import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function GET() {
  try {
    const processedFiles = await prisma.processedFile.findMany({
      include: {
        _count: {
          select: {
            verificationRecords: true
          }
        }
      },
      orderBy: {
        processedDate: "desc"
      }
    });

    const filesWithStats = processedFiles.map(file => ({
      ...file,
      verificationRecordsCount: file._count.verificationRecords,
      verificationProgress: file.sampleSize 
        ? Math.round((file._count.verificationRecords / file.sampleSize) * 100) 
        : 0
    }));

    return NextResponse.json({
      success: true,
      files: filesWithStats
    });

  } catch (error) {
    console.error("Failed to fetch processed files:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch processed files" },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { fileId, status, verifiedBy } = await request.json();

    const updatedFile = await prisma.processedFile.update({
      where: { id: fileId },
      data: {
        verificationStatus: status,
        verifiedBy,
        verifiedAt: status === "verified" ? new Date() : null,
      }
    });

    return NextResponse.json({
      success: true,
      file: updatedFile
    });

  } catch (error) {
    console.error("Failed to update file verification status:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update file verification status" },
      { status: 500 }
    );
  }
}