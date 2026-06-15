ALTER TABLE devices ADD COLUMN product_code_id TEXT;
ALTER TABLE devices ADD COLUMN registered_product_code TEXT;
ALTER TABLE devices ADD COLUMN product_code_verification_status TEXT;

CREATE TABLE IF NOT EXISTS product_code_registry (
  product_code_id TEXT PRIMARY KEY,
  product_code TEXT NOT NULL,
  normalized_product_code TEXT NOT NULL UNIQUE,
  model_name TEXT NOT NULL,
  product_type TEXT NOT NULL,
  structure_type TEXT,
  brand TEXT NOT NULL,
  country TEXT NOT NULL,
  registration_supported INTEGER NOT NULL,
  verification_status TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  support_url TEXT,
  official_asset_ids_json TEXT,
  official_chunk_ids_json TEXT,
  product_model_id TEXT,
  registration_block_reason TEXT,
  demo_scope TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_code_registry_code ON product_code_registry(normalized_product_code);
CREATE INDEX IF NOT EXISTS idx_product_code_registry_model ON product_code_registry(model_name, product_type);
CREATE INDEX IF NOT EXISTS idx_product_code_registry_status ON product_code_registry(verification_status, registration_supported);

CREATE TABLE IF NOT EXISTS product_code_aliases (
  alias_id TEXT PRIMARY KEY,
  product_code_id TEXT NOT NULL,
  alias_code TEXT NOT NULL,
  normalized_alias_code TEXT NOT NULL,
  alias_type TEXT NOT NULL,
  source_url TEXT,
  verification_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_code_aliases_alias ON product_code_aliases(normalized_alias_code);
CREATE INDEX IF NOT EXISTS idx_product_code_aliases_registry ON product_code_aliases(product_code_id);

CREATE TABLE IF NOT EXISTS product_registration_attempts (
  attempt_id TEXT PRIMARY KEY,
  user_id TEXT,
  input_code TEXT NOT NULL,
  normalized_input_code TEXT NOT NULL,
  match_status TEXT NOT NULL,
  matched_product_code_id TEXT,
  created_device_id TEXT,
  failure_reason TEXT,
  created_at TEXT NOT NULL,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_registration_attempts_user ON product_registration_attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_product_registration_attempts_code ON product_registration_attempts(normalized_input_code, match_status);
