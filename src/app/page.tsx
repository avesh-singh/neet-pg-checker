"use client";

import { useState } from "react";
import { EligibilityForm } from "@/components/forms/eligibility-form";
import { CollegeResults } from "@/components/tables/college-results";
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

export default function Home() {
  const [results, setResults] = useState<CollegeResult[]>([]);
  const [rank, setRank] = useState<number | null>(null);
  // const [loading, setLoading] = useState<boolean>(false); // Will be used for loading states

  const handleResults = (collegeResults: CollegeResult[], userRank: number) => {
    setResults(collegeResults);
    setRank(userRank);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="py-12 md:py-20 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-3xl mb-12 text-white">
        <div className="max-w-3xl mx-auto text-center px-6">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">NEET PG College Eligibility Checker</h1>
          <p className="text-xl opacity-90 mb-8">
            Find eligible medical colleges based on your NEET PG rank
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="mb-12">
        <Card shadow="lg" className="overflow-hidden">
          <div className="bg-indigo-50 px-6 py-4 border-b border-indigo-100 flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-indigo-700">Check Your Eligibility</h2>
              <p className="text-sm text-indigo-600">Enter your rank to find eligible colleges</p>
            </div>
          </div>
          <CardContent className="p-6">
            <EligibilityForm onResults={handleResults} />
          </CardContent>
        </Card>
      </section>

      {/* Results Section */}
      {rank && (
        <section className="mb-12">
          <Card shadow="lg">
            <CardContent className="p-6">
              <CollegeResults results={results} rank={rank} />
            </CardContent>
          </Card>
        </section>
      )}

      {/* Data Information Section */}
      <section className="py-12">
        <div className="text-center">
          <p className="text-lg text-gray-600">Based on 2024 counselling data gathered from numerous sources</p>
        </div>
      </section>
    </div>
  );
}
