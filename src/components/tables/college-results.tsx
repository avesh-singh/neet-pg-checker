"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

interface CollegeResult {
  college: string;
  course: string;
  quota: string;
  cutoffRank: number;
  category: string;
  round: number;
  year: number;
  state?: string;
}

interface CollegeResultsProps {
  results: CollegeResult[];
  rank: number;
}

type FilterType = "all" | "clinical" | "non-clinical" | "surgical";

export function CollegeResults({ results, rank }: CollegeResultsProps) {
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const filterResults = (filter: FilterType) => {
    if (filter === "all") {
      return results;
    }

    if (filter === "clinical") {
      return results.filter(
        (r) =>
          r.course &&
          (r.course.toUpperCase().includes("MEDICINE") ||
            r.course.toUpperCase().includes("PAEDIATRICS") ||
            r.course.toUpperCase().includes("PSYCHIATRY"))
      );
    }

    if (filter === "non-clinical") {
      return results.filter(
        (r) =>
          r.course &&
          (r.course.toUpperCase().includes("PATHOLOGY") ||
            r.course.toUpperCase().includes("COMMUNITY") ||
            r.course.toUpperCase().includes("FORENSIC") ||
            r.course.toUpperCase().includes("PREVENTIVE") ||
            r.course.toUpperCase().includes("SOCIAL"))
      );
    }

    if (filter === "surgical") {
      return results.filter(
        (r) =>
          r.course &&
          (r.course.toUpperCase().includes("SURGERY") ||
            r.course.toUpperCase().includes("OPHTHALMOLOGY") ||
            r.course.toUpperCase().includes("GYNAE") ||
            r.course.toUpperCase().includes("ORTHO"))
      );
    }

    return results;
  };

  const filteredResults = filterResults(activeFilter);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Eligible Colleges</h2>
          <p className="text-gray-600">
            Based on your rank: <span className="font-semibold">{rank}</span>
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-green-100 text-green-800 font-semibold rounded-full text-sm">
            {results.length} Colleges Found
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveFilter("all")}
          className={`px-4 py-2 text-sm font-medium rounded-md ${
            activeFilter === "all"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          All
        </button>
        <button
          onClick={() => setActiveFilter("clinical")}
          className={`px-4 py-2 text-sm font-medium rounded-md ${
            activeFilter === "clinical"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Clinical
        </button>
        <button
          onClick={() => setActiveFilter("non-clinical")}
          className={`px-4 py-2 text-sm font-medium rounded-md ${
            activeFilter === "non-clinical"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Non-Clinical
        </button>
        <button
          onClick={() => setActiveFilter("surgical")}
          className={`px-4 py-2 text-sm font-medium rounded-md ${
            activeFilter === "surgical"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Surgical
        </button>
      </div>

      {filteredResults.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <h3 className="text-lg font-semibold text-gray-700 mb-2">
            No Eligible Colleges Found
          </h3>
          <p className="text-gray-600">
            Try adjusting your filters or check colleges with higher cutoff ranks
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredResults.map((result, index) => (
            <Card
              key={`${result.college}-${result.course}-${index}`}
              className={`transform transition-all duration-300 hover:shadow-lg ${
                result.quota === "State Quota"
                  ? "border-l-4 border-l-green-500"
                  : ""
              }`}
            >
              <CardContent className="p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-1">
                  {result.college}
                </h3>
                <p className="text-indigo-600 font-medium mb-3">
                  {result.course}
                </p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Cutoff Rank:</span>{" "}
                    <span className="font-medium">{result.cutoffRank}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Category:</span>{" "}
                    <span className="font-medium">{result.category}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Quota:</span>{" "}
                    <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-800 text-xs font-medium rounded">
                      {result.quota}
                    </span>
                  </div>
                  {result.state && (
                    <div>
                      <span className="text-gray-500">State:</span>{" "}
                      <span className="font-medium">{result.state}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
