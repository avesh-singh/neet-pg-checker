import { NextRequest, NextResponse } from "next/server";
import { getEligibleColleges } from "@/lib/api/counselling-data";
import { z } from "zod";

const eligibilitySchema = z.object({
  rank: z.coerce.number().int().positive(),
  category: z.string().optional(),
  quota: z.string().optional(),
  limit: z.coerce.number().int().positive().optional().default(100),
});

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const searchParams = Object.fromEntries(url.searchParams.entries());
    
    const validationResult = eligibilitySchema.safeParse(searchParams);
    
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid parameters", details: validationResult.error.flatten() },
        { status: 400 }
      );
    }

    const { rank, category, quota, limit } = validationResult.data;

    const eligibleColleges = await getEligibleColleges({
      rank,
      category,
      quota,
      limit,
    });

    return NextResponse.json({
      success: true,
      rank,
      totalEligible: eligibleColleges.length,
      colleges: eligibleColleges,
    });
  } catch (error) {
    console.error("Error in eligibility endpoint:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
