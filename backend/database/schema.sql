-- ============================================================================
-- Customer Success Digital FTE - PostgreSQL CRM Schema
-- Production-Grade Schema for Multi-Channel Customer Support
-- Hackathon 5 - Refined for Digital FTE Requirements
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgvector (optional - for AI embeddings)
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS "pgvector";
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'pgvector extension not available - vector search will be disabled';
    END;
END$$;

-- pg_trgm (optional - for text search)
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'pg_trgm extension not available - text search will be disabled';
    END;
END$$;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE channel_type AS ENUM ('web_form', 'gmail', 'whatsapp');

CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');

CREATE TYPE ticket_status AS ENUM (
    'new',
    'in_progress',
    'pending_customer',
    'pending_internal',
    'escalated',
    'resolved',
    'closed'
);

CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TYPE sentiment_type AS ENUM (
    'very_negative',
    'negative',
    'neutral',
    'positive',
    'very_positive'
);

CREATE TYPE escalation_reason AS ENUM (
    'customer_request',
    'negative_sentiment',
    'complex_issue',
    'vip_customer',
    'sla_breach_risk',
    'repeated_issue',
    'ai_confidence_low',
    'manual_review'
);

CREATE TYPE delivery_status AS ENUM ('pending', 'sent', 'delivered', 'failed', 'read');

-- ============================================================================
-- TABLE: customers
-- Unified customer identity across all channels
-- ============================================================================

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Core identity
    email VARCHAR(255),
    phone VARCHAR(50),
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    
    -- Customer segmentation
    customer_tier VARCHAR(50) DEFAULT 'standard',
    customer_since TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Aggregated metrics
    total_tickets INTEGER DEFAULT 0,
    resolved_tickets INTEGER DEFAULT 0,
    avg_satisfaction_score DECIMAL(3,2),
    
    -- Preferences
    preferred_channel channel_type DEFAULT 'web_form',
    preferred_language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_interaction_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_customers_email ON customers (email);
CREATE INDEX idx_customers_phone ON customers (phone);
CREATE INDEX idx_customers_tier ON customers (customer_tier);
CREATE INDEX idx_customers_active ON customers (is_active) WHERE is_active = TRUE;

-- ============================================================================
-- TABLE: customer_identifiers
-- Cross-channel identity mapping (unified customer view)
-- ============================================================================

CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    channel channel_type NOT NULL,
    channel_identifier VARCHAR(512) NOT NULL,
    channel_metadata JSONB DEFAULT '{}'::jsonb,
    
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_channel_identifier UNIQUE (channel, channel_identifier)
);

CREATE INDEX idx_customer_identifiers_customer ON customer_identifiers (customer_id);
CREATE INDEX idx_customer_identifiers_lookup ON customer_identifiers (channel, channel_identifier);

-- ============================================================================
-- TABLE: tickets
-- EVERY ticket is created BEFORE any response (core requirement)
-- ============================================================================

CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    subject VARCHAR(512) NOT NULL,
    description TEXT,
    channel channel_type NOT NULL,
    
    -- Lifecycle
    status ticket_status DEFAULT 'new',
    priority ticket_priority DEFAULT 'medium',
    
    -- Assignment
    assigned_to VARCHAR(255) DEFAULT 'ai_agent',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- SLA tracking
    sla_tier VARCHAR(50) DEFAULT 'standard',
    first_response_due_at TIMESTAMP WITH TIME ZONE,
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolution_due_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    sla_breached BOOLEAN DEFAULT FALSE,
    
    -- Escalation tracking (explicit)
    escalation_status VARCHAR(50) DEFAULT 'none',
    escalation_level INTEGER DEFAULT 0,
    escalation_reason escalation_reason,
    escalation_details TEXT,
    escalated_at TIMESTAMP WITH TIME ZONE,
    escalated_to VARCHAR(255),
    
    -- Resolution
    resolution_summary TEXT,
    resolution_category VARCHAR(100),
    satisfaction_score INTEGER CHECK (satisfaction_score IS NULL OR (satisfaction_score >= 1 AND satisfaction_score <= 5)),
    satisfaction_feedback TEXT,
    
    -- AI tracking
    ai_handled BOOLEAN DEFAULT TRUE,
    ai_model_used VARCHAR(100),
    total_ai_tokens INTEGER DEFAULT 0,
    total_ai_latency_ms INTEGER DEFAULT 0,
    handoff_to_human_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tickets_customer ON tickets (customer_id);
CREATE INDEX idx_tickets_status ON tickets (status);
CREATE INDEX idx_tickets_priority ON tickets (priority);
CREATE INDEX idx_tickets_escalation ON tickets (escalation_status);
CREATE INDEX idx_tickets_created ON tickets (created_at);
CREATE INDEX idx_tickets_sla_breach ON tickets (sla_breached) WHERE sla_breached = TRUE;

-- ============================================================================
-- TABLE: conversations
-- Cross-channel conversation threads - ALWAYS linked to a ticket
-- ============================================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Thread identification
    channel channel_type NOT NULL,
    external_thread_id VARCHAR(512),
    
    -- Cross-channel continuity
    is_cross_channel BOOLEAN DEFAULT FALSE,
    merged_from_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Sentiment tracking
    overall_sentiment sentiment_type DEFAULT 'neutral',
    sentiment_score DECIMAL(5,4),
    
    -- Message tracking
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    last_message_from VARCHAR(50),
    
    -- Response tracking
    first_response_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_channel_thread UNIQUE (channel, external_thread_id)
);

CREATE INDEX idx_conversations_ticket ON conversations (ticket_id);
CREATE INDEX idx_conversations_customer ON conversations (customer_id);
CREATE INDEX idx_conversations_channel ON conversations (channel);
CREATE INDEX idx_conversations_cross_channel ON conversations (is_cross_channel) WHERE is_cross_channel = TRUE;

-- ============================================================================
-- TABLE: messages
-- All interactions with metadata
-- ============================================================================

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text/plain',
    language VARCHAR(10) DEFAULT 'en',
    
    -- Direction
    direction message_direction NOT NULL,
    channel channel_type NOT NULL,
    
    -- External references
    external_message_id VARCHAR(512),
    
    -- AI processing
    sentiment sentiment_type DEFAULT 'neutral',
    sentiment_score DECIMAL(5,4),
    topics TEXT[] DEFAULT '{}',
    intent VARCHAR(100),
    summary TEXT,
    
    -- AI generation metadata
    ai_model_used VARCHAR(100),
    ai_prompt_tokens INTEGER,
    ai_completion_tokens INTEGER,
    ai_latency_ms INTEGER,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    
    -- Delivery tracking
    delivery_status delivery_status DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    delivery_error TEXT,
    
    -- Human intervention
    is_human_handled BOOLEAN DEFAULT FALSE,
    human_agent_id UUID,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_messages_ticket ON messages (ticket_id);
CREATE INDEX idx_messages_conversation ON messages (conversation_id);
CREATE INDEX idx_messages_customer ON messages (customer_id);
CREATE INDEX idx_messages_channel ON messages (channel);
CREATE INDEX idx_messages_sentiment ON messages (sentiment);
CREATE INDEX idx_messages_created ON messages (created_at);
CREATE INDEX idx_messages_topics ON messages USING gin (topics);

-- ============================================================================
-- TABLE: knowledge_base
-- Knowledge articles with vector embeddings
-- Learning loop: resolved tickets → knowledge_base
-- ============================================================================

CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    content_html TEXT,

    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags TEXT[] DEFAULT '{}',

    -- Vector embedding for semantic search (optional - requires pgvector)
    embedding TEXT,  -- Using TEXT instead of vector(1536) for compatibility

    -- Learning loop - link to source ticket
    learned_from_ticket_id UUID REFERENCES tickets(id) ON DELETE SET NULL,
    is_auto_learned BOOLEAN DEFAULT FALSE,
    learning_confidence DECIMAL(3,2),
    
    -- Usage tracking
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- Search
    keywords TEXT[] DEFAULT '{}',
    
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_knowledge_base_category ON knowledge_base (category);
CREATE INDEX idx_knowledge_base_status ON knowledge_base (status);
-- Vector index (only if pgvector is available)
DO $$
BEGIN
    BEGIN
        CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Skipping vector index - pgvector not available';
    END;
END$$;
CREATE INDEX idx_knowledge_base_learned_from ON knowledge_base (learned_from_ticket_id) WHERE is_auto_learned = TRUE;

-- ============================================================================
-- TABLE: channel_configs
-- API configurations per channel
-- ============================================================================

CREATE TABLE channel_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel channel_type UNIQUE NOT NULL,
    
    api_endpoint VARCHAR(512),
    auth_type VARCHAR(50),
    credentials JSONB DEFAULT '{}'::jsonb,
    
    rate_limit_per_minute INTEGER DEFAULT 60,
    max_message_length INTEGER,
    
    webhook_url VARCHAR(512),
    webhook_secret VARCHAR(255),
    
    polling_enabled BOOLEAN DEFAULT FALSE,
    polling_interval_seconds INTEGER DEFAULT 60,
    last_poll_at TIMESTAMP WITH TIME ZONE,
    
    is_active BOOLEAN DEFAULT TRUE,
    last_health_check_at TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_channel_configs_channel ON channel_configs (channel);
CREATE INDEX idx_channel_configs_active ON channel_configs (is_active) WHERE is_active = TRUE;

-- ============================================================================
-- TABLE: agent_metrics
-- Hourly aggregated performance metrics
-- ============================================================================

CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    metric_date DATE NOT NULL,
    metric_hour INTEGER NOT NULL,
    channel channel_type NOT NULL,
    
    -- Volume
    total_messages_received INTEGER DEFAULT 0,
    total_messages_sent INTEGER DEFAULT 0,
    total_conversations_resolved INTEGER DEFAULT 0,
    
    -- Tickets
    tickets_created INTEGER DEFAULT 0,
    tickets_resolved INTEGER DEFAULT 0,
    tickets_escalated INTEGER DEFAULT 0,
    tickets_sla_breached INTEGER DEFAULT 0,
    
    -- AI performance
    total_ai_calls INTEGER DEFAULT 0,
    total_ai_tokens_input INTEGER DEFAULT 0,
    total_ai_tokens_output INTEGER DEFAULT 0,
    avg_ai_latency_ms INTEGER DEFAULT 0,
    ai_error_count INTEGER DEFAULT 0,
    
    -- Response times (seconds)
    avg_first_response_time INTEGER DEFAULT 0,
    avg_resolution_time INTEGER DEFAULT 0,
    
    -- Sentiment distribution
    sentiment_negative_count INTEGER DEFAULT 0,
    sentiment_neutral_count INTEGER DEFAULT 0,
    sentiment_positive_count INTEGER DEFAULT 0,
    
    -- Satisfaction
    avg_satisfaction_score DECIMAL(3,2),
    
    -- Escalations
    escalations_to_human INTEGER DEFAULT 0,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_metric_bucket UNIQUE (metric_date, metric_hour, channel)
);

CREATE INDEX idx_agent_metrics_date ON agent_metrics (metric_date);
CREATE INDEX idx_agent_metrics_channel ON agent_metrics (channel);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channel_configs_updated_at BEFORE UPDATE ON channel_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Ticket number generation
CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TRIGGER AS $$
DECLARE
    year_prefix TEXT;
    sequence_num TEXT;
BEGIN
    year_prefix := EXTRACT(YEAR FROM NEW.created_at)::TEXT;
    SELECT LPAD((COALESCE(
        (SELECT MAX(CAST(SUBSTRING(ticket_number FROM 'CS-[0-9]{4}-([0-9]+)$' AS INTEGER))
         FROM tickets WHERE ticket_number LIKE 'CS-' || year_prefix || '-%'), 0) + 1
    )::TEXT, '00001'), 5, '0') INTO sequence_num;
    NEW.ticket_number := 'CS-' || year_prefix || '-' || sequence_num;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_ticket_number
    BEFORE INSERT ON tickets
    FOR EACH ROW EXECUTE FUNCTION generate_ticket_number();

-- Update customer metrics on ticket resolution
CREATE OR REPLACE FUNCTION update_customer_ticket_metrics()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('resolved', 'closed') AND OLD.status NOT IN ('resolved', 'closed') THEN
        UPDATE customers
        SET resolved_tickets = resolved_tickets + 1,
            last_interaction_at = CURRENT_TIMESTAMP
        WHERE id = NEW.customer_id;
    END IF;
    IF NEW.status = 'new' AND OLD.status IS DISTINCT FROM 'new' THEN
        UPDATE customers
        SET total_tickets = total_tickets + 1,
            last_interaction_at = CURRENT_TIMESTAMP
        WHERE id = NEW.customer_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_ticket_metrics
    AFTER UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_customer_ticket_metrics();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active tickets with customer info
CREATE VIEW v_active_tickets AS
SELECT 
    t.id,
    t.ticket_number,
    t.subject,
    t.status,
    t.priority,
    t.escalation_status,
    t.escalation_reason,
    t.first_response_due_at,
    t.resolution_due_at,
    t.sla_breached,
    t.created_at,
    c.id AS customer_id,
    c.full_name AS customer_name,
    c.email AS customer_email,
    c.customer_tier
FROM tickets t
JOIN customers c ON t.customer_id = c.id
WHERE t.status NOT IN ('resolved', 'closed');

-- Cross-channel customer conversations
CREATE VIEW v_customer_cross_channel_summary AS
SELECT 
    c.id AS customer_id,
    c.full_name,
    c.email,
    COUNT(DISTINCT t.id) AS total_tickets,
    COUNT(DISTINCT conv.id) AS total_conversations,
    COUNT(DISTINCT conv.channel) AS channels_used,
    array_agg(DISTINCT conv.channel) AS channels,
    MAX(conv.last_message_at) AS last_interaction_at
FROM customers c
LEFT JOIN tickets t ON c.id = t.customer_id
LEFT JOIN conversations conv ON t.id = conv.ticket_id
WHERE c.is_active = TRUE
GROUP BY c.id, c.full_name, c.email;

-- Tickets ready for knowledge base learning
CREATE VIEW v_tickets_ready_for_learning AS
SELECT 
    t.id,
    t.ticket_number,
    t.subject,
    t.resolution_summary,
    t.resolution_category,
    t.satisfaction_score,
    t.resolved_at,
    c.full_name AS customer_name
FROM tickets t
JOIN customers c ON t.customer_id = c.id
WHERE t.status = 'resolved'
    AND t.resolution_summary IS NOT NULL
    AND t.satisfaction_score >= 4
    AND NOT EXISTS (
        SELECT 1 FROM knowledge_base kb 
        WHERE kb.learned_from_ticket_id = t.id
    );

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

INSERT INTO channel_configs (channel, auth_type, rate_limit_per_minute, max_message_length, is_active)
VALUES 
    ('web_form', 'none', 100, 10000, TRUE),
    ('gmail', 'oauth2', 30, 50000, FALSE),
    ('whatsapp', 'api_key', 60, 4096, FALSE)
ON CONFLICT (channel) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE customers IS 'Unified customer identity across all support channels';
COMMENT ON TABLE customer_identifiers IS 'Cross-channel identity mapping for unified customer view';
COMMENT ON TABLE tickets IS 'Core ticket system - created BEFORE any response';
COMMENT ON TABLE conversations IS 'Cross-channel conversation threads linked to tickets';
COMMENT ON TABLE messages IS 'All customer interactions with AI metadata';
COMMENT ON TABLE knowledge_base IS 'Knowledge articles with embeddings; learns from resolved tickets';
COMMENT ON TABLE channel_configs IS 'API configurations per channel';
COMMENT ON TABLE agent_metrics IS 'Hourly aggregated performance metrics';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
