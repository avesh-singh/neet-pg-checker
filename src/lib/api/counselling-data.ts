import { prisma } from "@/lib/db/prisma";
import { Prisma } from "@prisma/client";

export type EligibilityFilters = {
  rank: number;
  category?: string;
  quota?: string;
  round?: string;
  limit?: number;
};

export async function getEligibleColleges({
  rank,
  category,
  quota,
  round,
  limit = 100,
}: EligibilityFilters) {
  try {
    const where: Prisma.CounsellingDataWhereInput = {
      rank: { gte: rank },
    };

    if (category && category !== "all") {
      where.category = category;
    }

    if (quota && quota !== "all") {
      where.quota = quota;
    }

    if (round && round !== "all") {
      where.round = parseInt(round);
    }

    const results = await prisma.counsellingData.findMany({
      where,
      select: {
        collegeName: true,
        course: true,
        quota: true,
        rank: true,
        category: true,
        round: true,
        year: true,
        state: true,
      },
      orderBy: {
        rank: "asc",
      },
      take: limit,
      distinct: ["collegeName", "course", "quota", "category", "round", "year", "state"],
    });

    return results.map((result) => ({
      college: result.collegeName,
      course: result.course,
      quota: result.quota,
      cutoffRank: result.rank,
      category: result.category || "GENERAL",
      round: result.round,
      year: result.year,
      state: result.state,
    }));
  } catch (error) {
    console.error("Failed to fetch eligible colleges:", error);
    return [];
  }
}

export async function getAllColleges() {
  try {
    const colleges = await prisma.counsellingData.findMany({
      where: {
        collegeName: { not: null },
      },
      select: {
        collegeName: true,
        state: true,
        quota: true,
      },
      distinct: ["collegeName", "state", "quota"],
      orderBy: {
        collegeName: "asc",
      },
    });

    return colleges.map((college) => ({
      name: college.collegeName,
      state: college.state,
      quota: college.quota,
    }));
  } catch (error) {
    console.error("Failed to fetch colleges:", error);
    return [];
  }
}

export async function getAllCourses() {
  try {
    // Group by course and count colleges
    const courses = await prisma.counsellingData.groupBy({
      by: ["course"],
      where: {
        course: { not: null },
      },
      _count: {
        collegeName: true,
      },
      orderBy: {
        _count: {
          collegeName: "desc",
        },
      },
    });

    return courses.map((course) => ({
      name: course.course,
      collegeCount: course._count.collegeName,
    }));
  } catch (error) {
    console.error("Failed to fetch courses:", error);
    return [];
  }
}

export async function getCollegeCutoffs(collegeName: string) {
  try {
    const cutoffs = await prisma.counsellingData.groupBy({
      by: ["course", "category", "quota", "round", "year"],
      where: {
        collegeName: collegeName,
      },
      _min: {
        rank: true,
      },
      orderBy: {
        _min: {
          rank: "asc",
        },
      },
    });

    return cutoffs.map((cutoff) => ({
      course: cutoff.course,
      category: cutoff.category || "GENERAL",
      quota: cutoff.quota,
      cutoffRank: cutoff._min.rank,
      round: cutoff.round,
      year: cutoff.year,
    }));
  } catch (error) {
    console.error("Failed to fetch college cutoffs:", error);
    return [];
  }
}

export async function searchCollegesAndCourses(query: string, type: string = "all") {
  try {
    const results: { 
      colleges: Array<{ name: string | null; state: string | null; quota: string | null }>; 
      courses: (string | null)[] 
    } = {
      colleges: [],
      courses: [],
    };

    if (type === "all" || type === "college") {
      const colleges = await prisma.counsellingData.findMany({
        where: {
          collegeName: {
            contains: query,
            mode: "insensitive",
          },
        },
        select: {
          collegeName: true,
          state: true,
          quota: true,
        },
        distinct: ["collegeName", "state", "quota"],
        take: 20,
      });

      results.colleges = colleges.map((college) => ({
        name: college.collegeName,
        state: college.state,
        quota: college.quota,
      }));
    }

    if (type === "all" || type === "course") {
      const courses = await prisma.counsellingData.findMany({
        where: {
          course: {
            contains: query,
            mode: "insensitive",
          },
        },
        select: {
          course: true,
        },
        distinct: ["course"],
        take: 20,
      });

      results.courses = courses.map((course) => course.course);
    }

    return results;
  } catch (error) {
    console.error("Failed to search:", error);
    return { colleges: [], courses: [] };
  }
}

export async function getDatabaseStatistics() {
  try {
    const stats: Record<string, unknown> = {};

    // Total records
    const totalRecords = await prisma.counsellingData.count();
    stats.totalRecords = totalRecords;

    // Records by quota
    const quotaCounts = await prisma.counsellingData.groupBy({
      by: ["quota"],
      _count: {
        quota: true,
      },
    });
    stats.byQuota = Object.fromEntries(
      quotaCounts.map((q) => [q.quota || 'unknown', q._count.quota])
    );

    // Records by category
    const categoryCounts = await prisma.counsellingData.groupBy({
      by: ["category"],
      where: {
        category: { not: null },
      },
      _count: {
        category: true,
      },
    });
    stats.byCategory = Object.fromEntries(
      categoryCounts.map((c) => [c.category || 'unknown', c._count.category])
    );

    // Unique colleges
    const uniqueColleges = await prisma.counsellingData.findMany({
      select: {
        collegeName: true,
      },
      distinct: ["collegeName"],
    });
    stats.uniqueColleges = uniqueColleges.length;

    // Unique courses
    const uniqueCourses = await prisma.counsellingData.findMany({
      select: {
        course: true,
      },
      distinct: ["course"],
    });
    stats.uniqueCourses = uniqueCourses.length;

    // Rank ranges
    const rankRange = await prisma.counsellingData.aggregate({
      _min: {
        rank: true,
      },
      _max: {
        rank: true,
      },
    });
    stats.rankRange = {
      minimum: rankRange._min.rank,
      maximum: rankRange._max.rank,
    };

    return stats;
  } catch (error) {
    console.error("Failed to fetch statistics:", error);
    return null;
  }
}
