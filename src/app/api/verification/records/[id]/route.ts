import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: idParam } = await params;
    const id = parseInt(idParam);

    const verificationRecord = await prisma.verificationRecord.findUnique({
      where: { id },
      include: {
        counsellingData: true,
        processedFile: true,
      }
    });

    if (!verificationRecord) {
      return NextResponse.json(
        { success: false, error: "Verification record not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      record: verificationRecord
    });

  } catch (error) {
    console.error("Failed to fetch verification record:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch verification record" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: idParam } = await params;
    const id = parseInt(idParam);
    const body = await request.json();
    const { status, notes, verifiedBy } = body;

    const updatedRecord = await prisma.verificationRecord.update({
      where: { id },
      data: {
        verificationStatus: status,
        notes,
        verifiedBy,
        verifiedAt: status === "verified" ? new Date() : null,
      },
      include: {
        counsellingData: true,
        processedFile: true,
      }
    });

    return NextResponse.json({
      success: true,
      record: updatedRecord
    });

  } catch (error) {
    console.error("Failed to update verification record:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update verification record" },
      { status: 500 }
    );
  }
}