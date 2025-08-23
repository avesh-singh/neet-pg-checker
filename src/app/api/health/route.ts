import { NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function GET() {
  try {
    // Test database connection
    await prisma.$queryRaw`SELECT 1`;

    const response = {
      status: "healthy",
      message: "Application is running correctly",
      database: "connected",
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Health check failed:", error);

    const errorResponse = {
      status: "unhealthy",
      message: "Database connection failed",
      error: String(error),
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(errorResponse, { status: 503 });
  }
}
