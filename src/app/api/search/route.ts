import { NextRequest, NextResponse } from "next/server";
import { searchCollegesAndCourses } from "@/lib/api/counselling-data";
import { z } from "zod";

const searchSchema = z.object({
  q: z.string().min(1),
  type: z.enum(["all", "college", "course"]).default("all"),
});

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const searchParams = Object.fromEntries(url.searchParams.entries());
    
    const validationResult = searchSchema.safeParse(searchParams);
    
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid parameters", details: validationResult.error.flatten() },
        { status: 400 }
      );
    }

    const { q, type } = validationResult.data;

    const results = await searchCollegesAndCourses(q, type);

    return NextResponse.json({
      success: true,
      query: q,
      results,
    });
  } catch (error) {
    console.error("Error in search endpoint:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
