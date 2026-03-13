import apiClient from "./api-client";
import {
  AdjudicationResult,
  ClaimsListResponse,
  DashboardStats,
  PaginationParams,
  ClaimRequest,
} from "@/types";

export async function fetchDocumentUrl(claimId: string): Promise<string> {
  const { data } = await apiClient.get<{ url: string }>(
    `/documents/view/${claimId}`,
  );
  return data.url;
}

export async function getPresignedUploadUrl(
  filename: string,
  contentType: string,
): Promise<{
  upload_url: string;
  document_key: string;
  document_name: string;
}> {
  const { data } = await apiClient.post("/documents/upload-url", {
    filename,
    content_type: contentType,
  });
  return data;
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const [allRes, passRes, flagRes, failRes] = await Promise.all([
    apiClient.get<ClaimsListResponse>("/claims?limit=1"),
    apiClient.get<ClaimsListResponse>("/claims?limit=1&decision=Pass"),
    apiClient.get<ClaimsListResponse>("/claims?limit=1&decision=Flag"),
    apiClient.get<ClaimsListResponse>("/claims?limit=1&decision=Fail"),
  ]);

  const total = allRes.data.total;
  const passed = passRes.data.total;
  const flagged = flagRes.data.total;
  const failed = failRes.data.total;

  // Fetch a sample of recent claims to compute avg risk score
  const sampleRes =
    await apiClient.get<ClaimsListResponse>("/claims?limit=100");
  const sample = sampleRes.data.results;

  const avgRisk = sample.length
    ? sample.reduce((sum, c) => sum + c.risk_score, 0) / sample.length
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
  params: PaginationParams = {},
): Promise<ClaimsListResponse> {
  const { skip = 0, limit = 10, decision } = params;
  const query = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
    ...(decision ? { decision } : {}),
  });
  const { data } = await apiClient.get<ClaimsListResponse>(`/claims?${query}`);
  return data;
}

export async function fetchClaim(claimId: string): Promise<AdjudicationResult> {
  const { data } = await apiClient.get<AdjudicationResult>(
    `/claims/${claimId}`,
  );
  return data;
}

export async function adjudicateClaim(
  claim: ClaimRequest,
): Promise<AdjudicationResult> {
  const { data } = await apiClient.post<AdjudicationResult>(
    "/adjudicate",
    claim,
  );
  return data;
}
