import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") || "pending";
    const limit = parseInt(searchParams.get("limit") || "50");
    const fileId = searchParams.get("fileId");

    const where: {
      verificationStatus: string;
      processedFileId?: number;
    } = {
      verificationStatus: status,
    };

    if (fileId) {
      where.processedFileId = parseInt(fileId);
    }

    const verificationRecords = await prisma.verificationRecord.findMany({
      where,
      include: {
        counsellingData: {
          select: {
            rank: true,
            collegeName: true,
            course: true,
            quota: true,
            category: true,
            studentName: true,
          }
        },
        processedFile: {
          select: {
            filename: true,
            fileType: true,
          }
        }
      },
      orderBy: {
        createdAt: "desc"
      },
      take: limit,
    });

    return NextResponse.json({
      success: true,
      records: verificationRecords,
      count: verificationRecords.length
    });

  } catch (error) {
    console.error("Failed to fetch verification records:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch verification records" },
      { status: 500 }
    );
  }
}