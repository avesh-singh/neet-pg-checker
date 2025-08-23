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
            <div className="text-xs bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full">
              Database: Online
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

      {/* Features Section */}
      <section className="py-12">
        <h2 className="text-3xl font-bold text-center mb-10">Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-indigo-600">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Real-Time Eligibility</h3>
            <p className="text-gray-600">Instantly check eligible colleges based on your rank, category, and quota preferences.</p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-indigo-600">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Comprehensive Data</h3>
            <p className="text-gray-600">Access data from multiple rounds of counseling across all states and quotas.</p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-indigo-600">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Smart Filtering</h3>
            <p className="text-gray-600">Filter results by clinical, non-clinical, and surgical specialties to find your preferred course.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
