import { NextRequest, NextResponse } from "next/server";
import { getCollegeCutoffs } from "@/lib/api/counselling-data";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ collegeName: string }> }
) {
  try {
    const { collegeName } = await params;
    
    if (!collegeName) {
      return NextResponse.json(
        { error: "College name is required" },
        { status: 400 }
      );
    }

    const cutoffs = await getCollegeCutoffs(decodeURIComponent(collegeName));

    if (cutoffs.length === 0) {
      return NextResponse.json(
        { error: "College not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      college: decodeURIComponent(collegeName),
      cutoffs,
    });
  } catch (error) {
    console.error("Error fetching college cutoffs:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
