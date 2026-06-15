import { apiPost } from "./client";

export type CareRiskFactor = {
  factor: string;
  value: number | string | Record<string, number>;
  score_delta: number;
  reason: string;
};

export type CareRiskResponse = {
  care_risk_score: {
    score: number;
    risk_level: "low" | "medium" | "high";
    trigger_reason: string[];
  };
  care_risk_decision: {
    factor_scores: CareRiskFactor[];
  };
};

export type CareRiskLocation = {
  region: string;
  city: string;
  userEmail?: string;
};

export async function evaluateCareRisk(location?: CareRiskLocation): Promise<CareRiskResponse> {
  return apiPost<CareRiskResponse, { user_id: string; device_id: string; procedure_type: string; region?: string; city?: string }>(
    "/v1/care/risk/evaluate",
    {
      user_id: location?.userEmail ?? "u001@careshot.local",
      device_id: "D001",
      procedure_type: "filter_cleaning",
      region: location?.region,
      city: location?.city,
    },
  );
}
