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

export function useClaimsSample() {
  return useQuery({
    queryKey: ["claims", "sample"],
    queryFn:  () => fetchRecentClaims({ limit: 100 }),
    refetchInterval: 60_000,
  });
}