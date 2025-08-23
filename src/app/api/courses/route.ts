import { NextResponse } from "next/server";
import { getAllCourses } from "@/lib/api/counselling-data";

export async function GET() {
  try {
    const courses = await getAllCourses();

    return NextResponse.json({
      success: true,
      totalCourses: courses.length,
      courses,
    });
  } catch (error) {
    console.error("Error fetching courses:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
