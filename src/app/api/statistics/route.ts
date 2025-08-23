import { NextResponse } from "next/server";
import { getDatabaseStatistics } from "@/lib/api/counselling-data";

export async function GET() {
  try {
    const statistics = await getDatabaseStatistics();

    if (!statistics) {
      return NextResponse.json(
        { error: "Failed to fetch statistics" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      statistics,
    });
  } catch (error) {
    console.error("Error fetching statistics:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
