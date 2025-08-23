import { NextResponse } from "next/server";
import { getAllColleges } from "@/lib/api/counselling-data";

export async function GET() {
  try {
    const colleges = await getAllColleges();

    return NextResponse.json({
      success: true,
      totalColleges: colleges.length,
      colleges,
    });
  } catch (error) {
    console.error("Error fetching colleges:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
