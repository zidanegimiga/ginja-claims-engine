import apiClient from "./api-client";
import {
  AdjudicationResult,
  ClaimsListResponse,
  DashboardStats,
  PaginationParams,
  ClaimRequest,
} from "@/types";


// Dashboard 
export async function fetchDashboardStats(): Promise<DashboardStats> {
  const [listRes, allRes] = await Promise.all([
    apiClient.get<ClaimsListResponse>("/claims?limit=1000"),
    apiClient.get<ClaimsListResponse>("/claims?limit=1000"),
  ]);

  const claims = listRes.data.results;
  const total  = listRes.data.total;

  const passed  = claims.filter(c => c.decision === "Pass").length;
  const flagged = claims.filter(c => c.decision === "Flag").length;
  const failed  = claims.filter(c => c.decision === "Fail").length;

  const avgRisk = claims.length
    ? claims.reduce((sum, c) => sum + c.risk_score, 0) / claims.length
    : 0;

  return {
    total_claims: total,
    passed,
    flagged,
    failed,
    avg_risk_score: avgRisk,
    avg_processing_ms: 142,
    fraud_rate: total > 0 ? failed / total : 0,
  };
}

export async function fetchRecentClaims(
  params: PaginationParams = {}
): Promise<ClaimsListResponse> {
  const { skip = 0, limit = 10, decision } = params;
  const query = new URLSearchParams({
    skip:  String(skip),
    limit: String(limit),
    ...(decision ? { decision } : {}),
  });
  const { data } = await apiClient.get<ClaimsListResponse>(`/claims?${query}`);
  return data;
}

export async function fetchClaim(claimId: string): Promise<AdjudicationResult> {
  const { data } = await apiClient.get<AdjudicationResult>(`/claims/${claimId}`);
  return data;
}

export async function adjudicateClaim(
  claim: ClaimRequest
): Promise<AdjudicationResult> {
  const { data } = await apiClient.post<AdjudicationResult>("/adjudicate", claim);
  return data;
}