PRAGMA foreign_keys = ON;

CREATE TABLE "REGION" (
    region_id VARCHAR(50) PRIMARY KEY NOT NULL,
    country VARCHAR(50) DEFAULT 'India',
    state VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    climate_zone VARCHAR(50),
    water_hardness_level VARCHAR(30),
    monsoon_zone VARCHAR(50),
    active CHAR(1) DEFAULT 'Y',
    CHECK (active IN ('Y', 'N'))
);

CREATE TABLE "USER" (
    user_email VARCHAR(100) PRIMARY KEY NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(30),
    address VARCHAR(255),
    region_id VARCHAR(50),
    preferred_language VARCHAR(20) DEFAULT 'en',
    FOREIGN KEY (region_id) REFERENCES "REGION"(region_id)
);

CREATE TABLE "PRODUCT" (
    product_code VARCHAR(50) PRIMARY KEY NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(50) NOT NULL,
    structure_type VARCHAR(50),
    image_path VARCHAR(255),
    manual_file_path VARCHAR(255),
    registration_supported CHAR(1) DEFAULT 'Y',
    source_type VARCHAR(50) DEFAULT 'demo_seed',
    source_url VARCHAR(500),
    CHECK (registration_supported IN ('Y', 'N'))
);

CREATE TABLE "PRODUCT_REGISTRATION_ATTEMPT" (
    attempt_id BIGINT PRIMARY KEY NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    input_product_code VARCHAR(50) NOT NULL,
    match_status VARCHAR(30) NOT NULL,
    matched_product_code VARCHAR(50),
    failure_reason VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email) REFERENCES "USER"(user_email),
    FOREIGN KEY (matched_product_code) REFERENCES "PRODUCT"(product_code),
    CHECK (match_status IN ('matched', 'not_found', 'blocked'))
);

CREATE TABLE "USER_PRODUCT" (
    user_email VARCHAR(100) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    registration_attempt_id BIGINT,
    display_name VARCHAR(100),
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_email, product_code),
    FOREIGN KEY (user_email) REFERENCES "USER"(user_email),
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    FOREIGN KEY (registration_attempt_id) REFERENCES "PRODUCT_REGISTRATION_ATTEMPT"(attempt_id)
);

CREATE TABLE "OFFICIAL_ASSET" (
    asset_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50),
    product_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100),
    procedure_type VARCHAR(100),
    source_type VARCHAR(50) NOT NULL,
    source_title VARCHAR(255) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    language_code VARCHAR(20) DEFAULT 'en',
    verified_yn CHAR(1) DEFAULT 'Y',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    CHECK (verified_yn IN ('Y', 'N'))
);

CREATE TABLE "OFFICIAL_DOCUMENT_CHUNK" (
    chunk_id BIGINT PRIMARY KEY NOT NULL,
    asset_id BIGINT NOT NULL,
    product_code VARCHAR(50),
    procedure_type VARCHAR(100),
    chunk_text TEXT NOT NULL,
    source_url VARCHAR(500),
    source_section VARCHAR(255),
    language_code VARCHAR(20) DEFAULT 'en',
    embedding_status VARCHAR(30) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES "OFFICIAL_ASSET"(asset_id),
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    CHECK (embedding_status IN ('pending', 'embedded', 'failed'))
);

CREATE TABLE "AR_TARGET" (
    ar_target_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    target_name VARCHAR(100) NOT NULL,
    reference_image_path VARCHAR(255) NOT NULL,
    mind_target_path VARCHAR(255) NOT NULL,
    target_width DECIMAL(10,2),
    target_height DECIMAL(10,2),
    active CHAR(1) DEFAULT 'Y',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    CHECK (active IN ('Y', 'N'))
);

CREATE TABLE "GUIDE" (
    guide_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    guide_category VARCHAR(100) NOT NULL,
    guide_type VARCHAR(20) NOT NULL,
    trigger_type VARCHAR(30) NOT NULL,
    guide_title VARCHAR(150) NOT NULL,
    guide_summary TEXT,
    guide_text TEXT NOT NULL,
    video_url VARCHAR(500),
    image_path VARCHAR(255),
    source_type VARCHAR(50) DEFAULT 'official_manual',
    source_asset_id BIGINT,
    source_chunk_ids TEXT,
    source_url VARCHAR(500),
    source_reference VARCHAR(255),
    language_code VARCHAR(20) DEFAULT 'ko',
    is_active CHAR(1) DEFAULT 'Y',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    FOREIGN KEY (source_asset_id) REFERENCES "OFFICIAL_ASSET"(asset_id),
    CHECK (guide_type IN ('manual', 'ar')),
    CHECK (trigger_type IN ('self_care', 'self_as')),
    CHECK (is_active IN ('Y', 'N'))
);

CREATE TABLE "AR_GUIDE" (
    ar_guide_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    guide_id BIGINT,
    ar_target_id BIGINT NOT NULL,
    procedure_type VARCHAR(100) NOT NULL,
    ar_scene_path VARCHAR(255),
    overlay_config_json TEXT NOT NULL,
    active CHAR(1) DEFAULT 'Y',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES "PRODUCT"(product_code),
    FOREIGN KEY (guide_id) REFERENCES "GUIDE"(guide_id),
    FOREIGN KEY (ar_target_id) REFERENCES "AR_TARGET"(ar_target_id),
    CHECK (active IN ('Y', 'N'))
);

CREATE TABLE "SELF_MANAGEMENT_HISTORY" (
    history_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    management_category VARCHAR(100) NOT NULL,
    management_type VARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email, product_code) REFERENCES "USER_PRODUCT"(user_email, product_code),
    CHECK (management_type IN ('self_care', 'self_as'))
);

CREATE TABLE "CHAT_SESSION" (
    session_id BIGINT PRIMARY KEY NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    session_status VARCHAR(30) DEFAULT 'active',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    FOREIGN KEY (user_email, product_code) REFERENCES "USER_PRODUCT"(user_email, product_code),
    CHECK (session_status IN ('active', 'closed', 'abandoned'))
);

CREATE TABLE "CHATBOT_INQUIRY" (
    inquiry_id BIGINT PRIMARY KEY NOT NULL,
    session_id BIGINT NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    inquiry_content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES "CHAT_SESSION"(session_id),
    FOREIGN KEY (user_email, product_code) REFERENCES "USER_PRODUCT"(user_email, product_code)
);

CREATE TABLE "AI_INQUIRY_ANALYSIS" (
    ai_response_id BIGINT PRIMARY KEY NOT NULL,
    inquiry_id BIGINT NOT NULL UNIQUE,
    symptom VARCHAR(100),
    intent_type VARCHAR(30) NOT NULL,
    risk_level VARCHAR(30),
    recommended_guide_id BIGINT,
    safety_reason TEXT,
    status_yn CHAR(1) DEFAULT 'N',
    FOREIGN KEY (inquiry_id) REFERENCES "CHATBOT_INQUIRY"(inquiry_id),
    FOREIGN KEY (recommended_guide_id) REFERENCES "GUIDE"(guide_id),
    CHECK (intent_type IN ('self_care', 'self_as', 'expert_as')),
    CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high')),
    CHECK (status_yn IN ('Y', 'N'))
);

CREATE TABLE "CHAT_MESSAGE" (
    message_id BIGINT PRIMARY KEY NOT NULL,
    session_id BIGINT NOT NULL,
    sender_type VARCHAR(20) NOT NULL,
    message_type VARCHAR(30) DEFAULT 'text',
    message_content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES "CHAT_SESSION"(session_id),
    CHECK (sender_type IN ('user', 'ai', 'system'))
);

CREATE TABLE "CONVERSATION_STATE" (
    state_id BIGINT PRIMARY KEY NOT NULL,
    session_id BIGINT NOT NULL UNIQUE,
    current_intent VARCHAR(30),
    missing_slots TEXT,
    collected_slots_json TEXT,
    next_question TEXT,
    state_status VARCHAR(30) DEFAULT 'collecting',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES "CHAT_SESSION"(session_id),
    CHECK (current_intent IS NULL OR current_intent IN ('self_care', 'self_as', 'expert_as')),
    CHECK (state_status IN ('collecting', 'ready', 'completed'))
);

CREATE TABLE "SMART_DIAGNOSIS_RESULT" (
    diagnosis_id BIGINT PRIMARY KEY NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    diagnosis_code VARCHAR(100),
    diagnosis_message TEXT,
    severity_level VARCHAR(30),
    raw_result_json TEXT,
    diagnosed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email, product_code) REFERENCES "USER_PRODUCT"(user_email, product_code),
    CHECK (severity_level IS NULL OR severity_level IN ('low', 'medium', 'high'))
);

CREATE TABLE "OFFICIAL_DOCUMENT_EMBEDDING" (
    embedding_id BIGINT PRIMARY KEY NOT NULL,
    chunk_id BIGINT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_vector TEXT NOT NULL,
    embedding_status VARCHAR(30) DEFAULT 'embedded',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES "OFFICIAL_DOCUMENT_CHUNK"(chunk_id),
    UNIQUE (chunk_id, embedding_model),
    CHECK (embedding_status IN ('pending', 'embedded', 'failed'))
);

CREATE TABLE "RAG_SEARCH_LOG" (
    rag_log_id BIGINT PRIMARY KEY NOT NULL,
    inquiry_id BIGINT,
    ai_response_id BIGINT,
    query_text TEXT NOT NULL,
    top_chunk_ids TEXT,
    selected_asset_ids TEXT,
    search_status VARCHAR(30) DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES "CHATBOT_INQUIRY"(inquiry_id),
    FOREIGN KEY (ai_response_id) REFERENCES "AI_INQUIRY_ANALYSIS"(ai_response_id),
    CHECK (search_status IN ('success', 'no_match', 'blocked'))
);

CREATE TABLE "APPLIANCE_USAGE_LOG" (
    usage_log_id BIGINT PRIMARY KEY NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    usage_period_days INT DEFAULT 7,
    recent_used_hours DECIMAL(8,2) DEFAULT 0,
    last_used_at DATETIME,
    setting_temperature DECIMAL(4,1),
    operation_mode VARCHAR(30),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email, product_code) REFERENCES "USER_PRODUCT"(user_email, product_code)
);

CREATE TABLE "ENVIRONMENT_OBSERVATION" (
    observation_id BIGINT PRIMARY KEY NOT NULL,
    region_id VARCHAR(50) NOT NULL,
    observed_at DATETIME NOT NULL,
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    aqi INT,
    pm25 DECIMAL(8,2),
    pm10 DECIMAL(8,2),
    rain_intensity DECIMAL(8,2),
    monsoon_intensity DECIMAL(8,2),
    provider VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES "REGION"(region_id)
);

CREATE INDEX idx_user_region ON "USER"(region_id);
CREATE INDEX idx_product_model ON "PRODUCT"(model_name, product_type);
CREATE INDEX idx_user_product_user ON "USER_PRODUCT"(user_email);
CREATE INDEX idx_asset_product_procedure ON "OFFICIAL_ASSET"(product_code, product_type, procedure_type);
CREATE INDEX idx_chunk_asset ON "OFFICIAL_DOCUMENT_CHUNK"(asset_id);
CREATE INDEX idx_chunk_product_procedure ON "OFFICIAL_DOCUMENT_CHUNK"(product_code, procedure_type);
CREATE INDEX idx_embedding_chunk ON "OFFICIAL_DOCUMENT_EMBEDDING"(chunk_id);
CREATE INDEX idx_chat_session_user_product ON "CHAT_SESSION"(user_email, product_code, started_at);
CREATE INDEX idx_chat_message_session ON "CHAT_MESSAGE"(session_id, created_at);
CREATE INDEX idx_usage_user_product ON "APPLIANCE_USAGE_LOG"(user_email, product_code, created_at);
CREATE INDEX idx_environment_region_observed ON "ENVIRONMENT_OBSERVATION"(region_id, observed_at);
