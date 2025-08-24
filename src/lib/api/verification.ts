import { prisma } from "@/lib/db/prisma";

export type VerificationStatus = "pending" | "verified" | "rejected";

export async function getVerificationSummary() {
  try {
    const summary = await prisma.verificationRecord.groupBy({
      by: ["verificationStatus"],
      _count: {
        id: true,
      },
    });

    const totalFiles = await prisma.processedFile.count();
    const verifiedFiles = await prisma.processedFile.count({
      where: { verificationStatus: "verified" }
    });

    return {
      recordSummary: summary.reduce((acc, item) => {
        acc[item.verificationStatus] = item._count.id;
        return acc;
      }, {} as Record<string, number>),
      fileSummary: {
        total: totalFiles,
        verified: verifiedFiles,
        pending: totalFiles - verifiedFiles,
      }
    };
  } catch (error) {
    console.error("Failed to get verification summary:", error);
    return null;
  }
}

export async function getVerificationRecordsForFile(fileId: number) {
  try {
    return await prisma.verificationRecord.findMany({
      where: { processedFileId: fileId },
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
        }
      },
      orderBy: { pageNumber: "asc" }
    });
  } catch (error) {
    console.error("Failed to fetch verification records:", error);
    return [];
  }
}

export async function createVerificationSample(
  fileId: number, 
  sampleRate: number = 0.1,
  strategy: "systematic" | "random" = "systematic"
) {
  try {
    // Get the processed file
    const processedFile = await prisma.processedFile.findUnique({
      where: { id: fileId }
    });

    if (!processedFile) {
      throw new Error("Processed file not found");
    }

    // For demonstration, we'll use a time-based approach to find records
    // In production, you'd want to track file-record relationships during import
    const whereClause: { createdAt?: { gte: Date } } = {};
    
    if (processedFile.processedDate) {
      whereClause.createdAt = {
        gte: processedFile.processedDate,
      };
    }
    
    const recordsFromFile = await prisma.counsellingData.findMany({
      where: whereClause,
      orderBy: { id: "asc" },
      take: processedFile.recordsCount || undefined,
    });

    if (recordsFromFile.length === 0) {
      throw new Error("No records found for this file");
    }

    // Calculate sample size
    const sampleSize = Math.max(1, Math.floor(recordsFromFile.length * sampleRate));
    let sampledRecords: typeof recordsFromFile = [];

    if (strategy === "systematic") {
      // Systematic sampling - take every nth record
      const step = Math.floor(recordsFromFile.length / sampleSize);
      for (let i = 0; i < recordsFromFile.length; i += step) {
        sampledRecords.push(recordsFromFile[i]);
        if (sampledRecords.length >= sampleSize) break;
      }
    } else {
      // Random sampling
      const shuffled = [...recordsFromFile].sort(() => 0.5 - Math.random());
      sampledRecords = shuffled.slice(0, sampleSize);
    }

    // Create verification records
    const verificationRecords = await Promise.all(
      sampledRecords.map(async (record, index) => {
        // Estimate page number based on position
        const estimatedPage = Math.floor((index / sampledRecords.length) * 100) + 1;
        
        return prisma.verificationRecord.create({
          data: {
            counsellingDataId: record.id,
            processedFileId: fileId,
            pageNumber: estimatedPage,
            verificationStatus: "pending",
          }
        });
      })
    );

    // Update processed file
    await prisma.processedFile.update({
      where: { id: fileId },
      data: {
        sampleSize: verificationRecords.length,
      }
    });

    return {
      sampleSize: verificationRecords.length,
      totalRecords: recordsFromFile.length,
      strategy,
      sampleRate,
    };

  } catch (error) {
    console.error("Failed to create verification sample:", error);
    throw error;
  }
}

export async function updateVerificationRecord(
  recordId: number,
  status: VerificationStatus,
  notes?: string,
  verifiedBy?: string
) {
  try {
    return await prisma.verificationRecord.update({
      where: { id: recordId },
      data: {
        verificationStatus: status,
        notes,
        verifiedBy,
        verifiedAt: status === "verified" ? new Date() : null,
      }
    });
  } catch (error) {
    console.error("Failed to update verification record:", error);
    throw error;
  }
}

export async function getVerificationStatistics() {
  try {
    const totalFiles = await prisma.processedFile.count();
    const filesWithSamples = await prisma.processedFile.count({
      where: { sampleSize: { gt: 0 } }
    });

    const verificationCounts = await prisma.verificationRecord.groupBy({
      by: ["verificationStatus"],
      _count: { id: true },
    });

    const recordStats = verificationCounts.reduce((acc, item) => {
      acc[item.verificationStatus] = item._count.id;
      return acc;
    }, {} as Record<string, number>);

    return {
      files: {
        total: totalFiles,
        withSamples: filesWithSamples,
        pendingSamples: totalFiles - filesWithSamples,
      },
      records: {
        pending: recordStats.pending || 0,
        verified: recordStats.verified || 0,
        rejected: recordStats.rejected || 0,
        total: Object.values(recordStats).reduce((sum, count) => sum + count, 0),
      }
    };
  } catch (error) {
    console.error("Failed to get verification statistics:", error);
    return null;
  }
}