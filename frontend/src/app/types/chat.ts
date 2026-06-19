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
  cardPolicy?: ChatCardPolicy | null;
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

export interface ChatDisplayStep {
  title?: string;
  text?: string;
  tts_enabled?: boolean;
  tts_text?: string;
  tts_language_code?: string;
  tts_provider?: "web_speech" | "google_cloud_tts" | string;
  audio_url?: string | null;
  source_type?: string;
  source_url?: string | null;
  source_title?: string | null;
  source_text?: string;
  evidence?: ChatEvidence[];
  generation_source?: string;
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
  display_title?: string;
  display_steps?: ChatDisplayStep[];
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
  card_policy?: ChatCardPolicy | null;
}

export interface ChatCardPolicy {
  card_type?: "clarification" | "service_route" | "safety_block" | "ar_start" | "manual_only" | "none";
  title?: string;
  description?: string;
  primary_action?: string | null;
  show_manual_button?: boolean;
  show_ar_button?: boolean;
  show_service_button?: boolean;
  reason?: string;
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

