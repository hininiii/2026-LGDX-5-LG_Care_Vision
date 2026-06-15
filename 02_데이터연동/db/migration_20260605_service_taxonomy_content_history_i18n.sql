-- migration_20260605_service_taxonomy_content_history_i18n.sql
-- SQLite development DB migration reference.
-- SQLite does not support ADD COLUMN IF NOT EXISTS in every local runtime,
-- so the live migration is applied by checking existing columns first.

CREATE TABLE IF NOT EXISTS user_addresses (
  address_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  address_type TEXT NOT NULL,
  country TEXT NOT NULL,
  region TEXT NOT NULL,
  city TEXT NOT NULL,
  district TEXT,
  postal_code TEXT,
  address_line1 TEXT NOT NULL,
  address_line2 TEXT,
  latitude REAL,
  longitude REAL,
  is_default INTEGER NOT NULL,
  verified_status TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supported_languages (
  language_code TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  native_name TEXT,
  region_scope TEXT,
  web_supported INTEGER NOT NULL,
  tts_supported INTEGER NOT NULL,
  fallback_language_code TEXT,
  created_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_language_preferences (
  language_pref_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  primary_language_code TEXT NOT NULL,
  fallback_language_code TEXT,
  web_language_code TEXT NOT NULL,
  tts_language_code TEXT,
  translation_consent_status TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translation_templates (
  template_id TEXT PRIMARY KEY,
  template_type TEXT NOT NULL,
  service_flow_type TEXT,
  source_language TEXT NOT NULL,
  source_text TEXT NOT NULL,
  safety_locked INTEGER NOT NULL,
  approval_status TEXT NOT NULL,
  created_at TEXT,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translation_jobs (
  translation_job_id TEXT PRIMARY KEY,
  template_id TEXT,
  content_id TEXT,
  target_language TEXT NOT NULL,
  status TEXT NOT NULL,
  provider TEXT,
  requested_at TEXT NOT NULL,
  completed_at TEXT,
  reviewed_by TEXT,
  reviewed_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_localizations (
  localization_id TEXT PRIMARY KEY,
  localization_group_id TEXT,
  content_id TEXT,
  template_id TEXT,
  language_code TEXT NOT NULL,
  title TEXT,
  body_text TEXT,
  subtitle_url TEXT,
  tts_script TEXT,
  approval_status TEXT NOT NULL,
  source_meaning_locked INTEGER NOT NULL,
  created_at TEXT,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_view_logs (
  content_view_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  content_id TEXT NOT NULL,
  service_flow_type TEXT NOT NULL,
  procedure_type TEXT,
  source_alert_id TEXT,
  source_chat_session_id TEXT,
  language_code TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  progress_percent REAL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS care_activity_logs (
  activity_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  service_flow_type TEXT NOT NULL,
  activity_channel TEXT NOT NULL,
  procedure_type TEXT,
  source_alert_id TEXT,
  source_chat_session_id TEXT,
  content_view_id TEXT,
  ar_session_id TEXT,
  status TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  progress_percent REAL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_care_summary (
  summary_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  self_care_count INTEGER NOT NULL,
  self_as_count INTEGER NOT NULL,
  total_care_count INTEGER NOT NULL,
  care_score REAL,
  last_self_care_at TEXT,
  last_self_as_at TEXT,
  updated_at TEXT NOT NULL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expert_as_requests (
  expert_as_request_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  address_id TEXT,
  route_log_id TEXT,
  request_status TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  symptom_summary TEXT,
  address_snapshot_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_addresses_user ON user_addresses(user_id, is_default);
CREATE INDEX IF NOT EXISTS idx_supported_languages_web ON supported_languages(web_supported, language_code);
CREATE INDEX IF NOT EXISTS idx_user_language_preferences_user ON user_language_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_content_localizations_content_language ON content_localizations(content_id, language_code, approval_status);
CREATE INDEX IF NOT EXISTS idx_content_view_logs_user_device ON content_view_logs(user_id, device_id, service_flow_type, status);
CREATE INDEX IF NOT EXISTS idx_care_activity_logs_user_device ON care_activity_logs(user_id, device_id, service_flow_type, status);
CREATE INDEX IF NOT EXISTS idx_device_care_summary_user_device ON device_care_summary(user_id, device_id);
CREATE INDEX IF NOT EXISTS idx_expert_as_requests_user_device ON expert_as_requests(user_id, device_id, request_status);
