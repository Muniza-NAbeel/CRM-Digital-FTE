-- Message Queue Tracking Table
-- Stores messages before they are processed by worker

CREATE TABLE IF NOT EXISTS message_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(100) UNIQUE NOT NULL,
    trace_id VARCHAR(100) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    subject VARCHAR(512),
    message TEXT NOT NULL,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,
    ticket_id UUID,
    response TEXT,
    sentiment VARCHAR(50),
    is_escalated BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_message_queue_request_id ON message_queue (request_id);
CREATE INDEX IF NOT EXISTS idx_message_queue_status ON message_queue (status);
CREATE INDEX IF NOT EXISTS idx_message_queue_created ON message_queue (created_at);

-- Add customer_email to tickets metadata if not present
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
