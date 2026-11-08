/**
 * Strongly typed interfaces for Humark API communications.
 */

export interface GameSessionResponse {
  id: string;
  current_round: number;
  status: string;
  created_at: string;
  updated_at: string;
  total_attempts: number;
  correct_attempts: number;
  round_attempts: number;
  accuracy: number;
}

export interface NextChallengeResponse {
  id: string | null;
  title: string | null;
  category: string | null;
  thumbnail_a_url: string | null;
  thumbnail_b_url: string | null;
  round_completed: boolean;
  round_number: number;
  attempt_index: number;
  total_round_items: number;
}

export interface ModelComparisonResult {
  model_name: string;
  model_version: string;
  predicted_variant: string;
  confidence: number;
  reasoning: string;
  prompt_version: string;
  token_count: number;
  latency_ms: number;
  cost_usd: number;
  is_model_correct: boolean;
}

export interface AttemptReceipt {
  attempt_id: string;
  session_id: string;
  challenge_id: string;
  round_number: number;
  attempt_index: number;
  round_items: number;
  selected_variant: string;
  is_correct: boolean;
  time_taken_ms: number;
  title: string;
  category: string;
  thumbnail_a_url: string;
  thumbnail_b_url: string;
  impressions_a: number;
  clicks_a: number;
  ctr_a: floatNumber;
  impressions_b: number;
  clicks_b: number;
  ctr_b: floatNumber;
  winning_variant: string;
  z_score: number;
  p_value: number;
  provenance_source: string;
  model_predictions: ModelComparisonResult[];
}

// Helper alias for clarity
export type floatNumber = number;

export interface RoundAdvanceResponse {
  session_id: string;
  current_round: number;
  status: string;
  message: string;
}

export interface WilsonInterval {
  p: number;
  ci_lower: number;
  ci_upper: number;
  margin_of_error: number;
  sample_size: number;
  is_sample_size_valid: boolean;
  warning: string | null;
}

export interface ModelComparisonItem {
  model_name: string;
  model_accuracy: number;
  user_beat_model: number;
  model_beat_user: number;
  ties: number;
  accuracy_delta: number;
  verdict: 'ahead' | 'behind' | 'tied';
}

export interface CategoryBreakdownItem {
  category: string;
  total_attempts: number;
  correct_attempts: number;
  accuracy: number;
}

export interface VerificationAuditSummary {
  verification_hash: string;
  completed_at: string;
  cumulative_accuracy: number;
  round_1_correct: number;
  round_2_correct: number;
  round_3_correct: number;
}

export interface ScorecardResponse {
  session_id: string;
  total_attempts: number;
  correct_attempts: number;
  accuracy: number;
  wilson_interval: WilsonInterval;
  average_time_taken_ms: number;
  current_round: number;
  rounds_completed: number;
  status: string;
  is_verified: boolean;
  model_comparisons: ModelComparisonItem[];
  category_breakdown: CategoryBreakdownItem[];
  verification_audit: VerificationAuditSummary | null;
  verification_hash: string | null;
}

export interface VerificationResult {
  session_id: string;
  completed_at: string;
  total_attempts: number;
  correct_attempts: number;
  cumulative_accuracy: number;
  is_verified: boolean;
  round_1_correct: number;
  round_2_correct: number;
  round_3_correct: number;
  verification_hash: string;
}

export interface VerificationStatusResponse {
  session_id: string;
  current_round: number;
  status: string;
  round_attempts: number;
  total_attempts: number;
  is_completed: boolean;
  is_verified: boolean | null;
  cumulative_accuracy: number | null;
  round_scores: Record<string, number>;
  verification_hash: string | null;
  audit_log: VerificationResult | null;
}
