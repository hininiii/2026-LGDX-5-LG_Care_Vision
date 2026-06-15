import type { ChatDeviceOption } from "./device";

export interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  time: string;
  status?: ChatMessageStatus;
  options?: string[];
  problemOptions?: string[];
  showVideo?: boolean;
  videoUrl?: string;
  guideButtons?: ("manual" | "ar" | "service")[];
  guideOptions?: ChatGuideOptions;
  showDoneAsk?: boolean;
  showSchedule?: boolean;
  showServiceSummary?: ServiceInfo;
  showServiceComplete?: boolean;
  modelOptions?: ChatDeviceOption[];
}

export type ChatMessageStatus =
  | "sent"
  | "analyzing"
  | "needs_clarification"
  | "evidence_found"
  | "blocked"
  | "ar_ready";

export interface ChatEvidence {
  title?: string;
  source_url?: string;
  source_type?: string;
  section_title?: string;
  procedure_type?: string;
  risk_policy?: string;
}

export interface ChatManualGuide {
  title?: string;
  summary?: string;
  guide_text?: string;
  source_url?: string;
  video_url?: string | null;
  evidence?: ChatEvidence[];
  safety_scope?: string;
}

export interface ChatYoutubeRecommendation {
  title?: string;
  source_url?: string;
  video_id?: string;
  source_type?: string;
  channel_name?: string;
  procedure_type?: string;
  risk_policy?: string;
}

export interface ChatGuideOptions {
  service_flow_type?: string;
  procedure_type?: string;
  manual_guides?: ChatManualGuide[];
  youtube_recommendations?: ChatYoutubeRecommendation[];
  ar_guides?: unknown[];
  matching_policy?: Record<string, unknown>;
}

export interface AiChatResponse {
  message: string;
  message_type?: string;
  session_id?: string;
  service_flow_type?: string;
  risk_level?: string;
  procedure_type?: string;
  recommended_action?: string;
  needs_clarification?: boolean;
  missing_slots?: string[];
  guide_options?: ChatGuideOptions | null;
}

export interface ServiceInfo {
  product: string;
  name: string;
  phone: string;
  address: string;
  model: string;
  issue: string;
}

export type ServiceStep = "idle" | "model" | "issue";
export type FlowType = "trouble" | "care" | "service" | null;
export type RecommendedAction = "manual" | "ar" | "video" | "service" | "llm";

export interface ChatContext {
  intent?: Exclude<FlowType, null>;
  productCategory?: string;
  productType?: string;
  deviceId?: string;
  session_id?: string;
  productName?: string;
  model?: string;
  symptom?: string;
  issue?: string;
  recommendedActions?: RecommendedAction[];
}

export interface ScheduleDateOption {
  label: string;
  value: string;
}

