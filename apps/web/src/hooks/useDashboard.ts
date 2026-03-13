import { useQuery } from "@tanstack/react-query";
import { fetchDashboardStats, fetchRecentClaims } from "@/lib/queries";
import { PaginationParams } from "@/types";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn:  fetchDashboardStats,
    refetchInterval: 30_000, // refresh every 30s
  });
}

export function useRecentClaims(params: PaginationParams = {}) {
  return useQuery({
    queryKey: ["claims", "list", params],
    queryFn:  () => fetchRecentClaims(params),
    refetchInterval: 30_000,
  });
}