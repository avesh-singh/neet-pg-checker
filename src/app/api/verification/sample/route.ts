import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function POST(request: NextRequest) {
  try {
    const { fileId, sampleRate = 0.1 } = await request.json();

    const processedFile = await prisma.processedFile.findUnique({
      where: { id: fileId }
    });

    if (!processedFile) {
      return NextResponse.json(
        { success: false, error: "Processed file not found" },
        { status: 404 }
      );
    }

    // Get all counselling data records from this file
    // Note: This is a simplified approach - in production you'd want to 
    // track the relationship between records and files during import
    const whereClause: { createdAt?: { gte: Date } } = {};
    
    if (processedFile.processedDate) {
      whereClause.createdAt = {
        gte: processedFile.processedDate,
      };
    }
    
    const allRecords = await prisma.counsellingData.findMany({
      where: whereClause,
      orderBy: { id: "asc" },
      take: processedFile.recordsCount || undefined,
    });

    if (allRecords.length === 0) {
      return NextResponse.json(
        { success: false, error: "No records found for this file" },
        { status: 404 }
      );
    }

    // Create sample using systematic sampling
    const sampleSize = Math.max(1, Math.floor(allRecords.length * sampleRate));
    const step = Math.floor(allRecords.length / sampleSize);
    const sampledRecords = [];

    for (let i = 0; i < allRecords.length; i += step) {
      sampledRecords.push(allRecords[i]);
      if (sampledRecords.length >= sampleSize) break;
    }

    // Create verification records
    const verificationRecords = await Promise.all(
      sampledRecords.map(async (record, index) => {
        // Estimate page number based on position (rough approximation)
        const estimatedPage = Math.floor((index / sampledRecords.length) * 100) + 1;
        
        return prisma.verificationRecord.create({
          data: {
            counsellingDataId: record.id,
            processedFileId: fileId,
            pageNumber: estimatedPage, // This would ideally come from the import process
            verificationStatus: "pending",
          }
        });
      })
    );

    // Update processed file with sample size
    await prisma.processedFile.update({
      where: { id: fileId },
      data: {
        sampleSize: verificationRecords.length,
      }
    });

    return NextResponse.json({
      success: true,
      message: `Created ${verificationRecords.length} verification records`,
      sampleSize: verificationRecords.length,
      totalRecords: allRecords.length,
      sampleRate: sampleRate
    });

  } catch (error) {
    console.error("Failed to create verification sample:", error);
    return NextResponse.json(
      { success: false, error: "Failed to create verification sample" },
      { status: 500 }
    );
  }
}