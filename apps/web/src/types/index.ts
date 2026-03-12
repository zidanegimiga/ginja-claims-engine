export type Decision = "Pass" | "Flag" | "Fail";

export type ProviderType =
  | "hospital"
  | "clinic"
  | "pharmacy"
  | "laboratory"
  | "specialist";

export type UserRole = "admin" | "claims_officer" | "viewer";

export interface ClaimRequest {
  claim_id?: string;
  member_id: string;
  provider_id: string;
  diagnosis_code: string;
  procedure_code: string;
  claimed_amount: number;
  approved_tariff: number;
  date_of_service: string;
  provider_type: ProviderType;
  location: string;
  member_age?: number;
  is_duplicate?: boolean;
}

export interface FeatureContributions {
  provider_is_high_risk: number;
  amount_deviation_pct: number;
  code_match: number;
  provider_claim_frequency: number;
  member_claim_frequency: number;
  member_age: number;
  amount_ratio: number;
  is_duplicate: number;
}

export interface AdjudicationResult {
  claim_id: string;
  member_id: string;
  provider_id: string;
  decision: Decision;
  risk_score: number;
  confidence: number;
  reasons: string[];
  explanation_of_benefits: string;
  feature_contributions: FeatureContributions;
  adjudication_stage: 1 | 2 | 3;
  processing_time_ms: number;
  adjudicated_at: string;
  extraction_metadata?: {
    provider: string;
    confidence: number;
    warnings: string[];
  };
}

export interface ClaimListItem {
  claim_id: string;
  member_id: string;
  provider_id: string;
  decision: Decision;
  risk_score: number;
  claimed_amount: number;
  adjudicated_at: string;
}

export interface ClaimsListResponse {
  total: number;
  skip: number;
  limit: number;
  results: ClaimListItem[];
}

export interface DashboardStats {
  total_claims: number;
  passed: number;
  flagged: number;
  failed: number;
  avg_risk_score: number;
  avg_processing_ms: number;
  fraud_rate: number;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  api_key: string;
}

export interface ApiKey {
  key_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  created_by: string;
  created_at: string;
  last_used: string | null;
  use_count: number;
}

export interface UploadedFile {
  key: string;
  url: string;
  filename: string;
  size: number;
  uploaded_at: string;
}

export interface PdfExtractionResult {
  extracted_data: Partial<ClaimRequest>;
  validation_errors: string[];
  is_valid: boolean;
  extraction_warnings: string[];
  confidence: number;
  provider_name: string;
}

export interface ApiError {
  error: string;
  detail?: string | object;
  hint?: string;
}

export interface PaginationParams {
  skip?: number;
  limit?: number;
  decision?: Decision;
}