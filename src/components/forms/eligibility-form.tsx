"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

const eligibilitySchema = z.object({
  rank: z.coerce.number().int().positive("Rank must be a positive number"),
  category: z.string().optional(),
  quota: z.string().optional(),
  limit: z.coerce.number().int().positive().optional().default(100),
});

type EligibilityFormData = z.infer<typeof eligibilitySchema>;

interface EligibilityResult {
  college: string;
  course: string;
  quota: string;
  cutoffRank: number;
  category: string;
  round: number;
  year: number;
  state?: string;
}

interface EligibilityFormProps {
  onResults: (results: EligibilityResult[], rank: number) => void;
}

export function EligibilityForm({ onResults }: EligibilityFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(eligibilitySchema),
    defaultValues: {
      category: "all",
      quota: "all",
      limit: 100,
    },
  });

  const onSubmit = async (data: EligibilityFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        rank: data.rank.toString(),
        category: data.category || "all",
        quota: data.quota || "all",
        limit: (data.limit || 100).toString(),
      });

      const response = await fetch(`/api/eligibility?${params}`);
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Failed to check eligibility");
      }

      onResults(result.colleges || [], data.rank);
    } catch (err) {
      console.error("Error checking eligibility:", err);
      setError(
        err instanceof Error ? err.message : "Failed to check eligibility"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-md">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="space-y-1">
          <label
            htmlFor="rank"
            className="block text-sm font-medium text-gray-700"
          >
            Your NEET PG Rank
          </label>
          <Input
            id="rank"
            type="number"
            placeholder="e.g., 5000"
            error={!!errors.rank}
            {...register("rank")}
          />
          {errors.rank && (
            <p className="text-sm text-red-600">{errors.rank.message}</p>
          )}
        </div>

        <div className="space-y-1">
          <label
            htmlFor="category"
            className="block text-sm font-medium text-gray-700"
          >
            Category
          </label>
          <Select id="category" {...register("category")}>
            <option value="all">All Categories</option>
            <option value="GENERAL">General</option>
            <option value="OBC">OBC</option>
            <option value="SC">SC</option>
            <option value="ST">ST</option>
            <option value="EWS">EWS</option>
          </Select>
        </div>

        <div className="space-y-1">
          <label
            htmlFor="quota"
            className="block text-sm font-medium text-gray-700"
          >
            Quota
          </label>
          <Select id="quota" {...register("quota")}>
            <option value="all">All Quotas</option>
            <option value="AI">All India (AI)</option>
            <option value="DU">Delhi University (DU)</option>
            <option value="State Quota">State Quota</option>
          </Select>
        </div>

        <div className="flex items-end">
          <Button type="submit" isLoading={isLoading} className="w-full">
            Check Eligibility
          </Button>
        </div>
      </div>
    </form>
  );
}
