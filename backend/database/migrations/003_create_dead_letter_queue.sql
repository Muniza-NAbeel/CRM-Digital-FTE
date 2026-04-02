-- Migration: Create Dead Letter Queue (DLQ) table
-- Run this to enable DLQ for failed messages after max retries

-- Create dead_letter_queue table
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Original message reference
    original_request_id VARCHAR(255) NOT NULL,
    original_trace_id VARCHAR(255),
    
    -- Message content (preserved from original)
    customer_email VARCHAR(255) NOT NULL,
    subject VARCHAR(512) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(50) NOT NULL,
    
    -- Failure information
    failure_reason TEXT NOT NULL,
    error_message TEXT,
    error_stack_trace TEXT,
    
    -- Retry history
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    first_attempt_at TIMESTAMP WITH TIME ZONE,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    last_error_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- DLQ processing status
    dlq_status VARCHAR(50) DEFAULT 'new',  -- new, reviewing, resolved, archived
    dlq_priority VARCHAR(50) DEFAULT 'medium',  -- low, medium, high, critical
    dlq_category VARCHAR(100),  -- auto_categorized failure type
    
    -- Manual review fields
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    resolution_action TEXT,
    
    -- Metadata
    original_metadata JSONB DEFAULT '{}'::jsonb,
    dlq_metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_dlq_request_id ON dead_letter_queue (original_request_id);
CREATE INDEX IF NOT EXISTS idx_dlq_email ON dead_letter_queue (customer_email);
CREATE INDEX IF NOT EXISTS idx_dlq_status ON dead_letter_queue (dlq_status);
CREATE INDEX IF NOT EXISTS idx_dlq_priority ON dead_letter_queue (dlq_priority);
CREATE INDEX IF NOT EXISTS idx_dlq_created_at ON dead_letter_queue (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dlq_category ON dead_letter_queue (dlq_category);

-- Add comments
COMMENT ON TABLE dead_letter_queue IS 'Dead Letter Queue for messages that failed after max retries';
COMMENT ON COLUMN dead_letter_queue.original_request_id IS 'Original request_id from message_queue';
COMMENT ON COLUMN dead_letter_queue.failure_reason IS 'Primary reason for failure';
COMMENT ON COLUMN dead_letter_queue.dlq_status IS 'DLQ processing status: new, reviewing, resolved, archived';
COMMENT ON COLUMN dead_letter_queue.dlq_priority IS 'Priority for manual review';
COMMENT ON COLUMN dead_letter_queue.dlq_category IS 'Auto-categorized failure type for analysis';

-- Create function to auto-categorize failures
CREATE OR REPLACE FUNCTION categorize_dlq_failure()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-categorize based on error message
    IF NEW.error_message ILIKE '%timeout%' OR NEW.error_message ILIKE '%timed out%' THEN
        NEW.dlq_category := 'timeout_error';
    ELSIF NEW.error_message ILIKE '%connection%' OR NEW.error_message ILIKE '%network%' THEN
        NEW.dlq_category := 'connection_error';
    ELSIF NEW.error_message ILIKE '%authentication%' OR NEW.error_message ILIKE '%unauthorized%' OR NEW.error_message ILIKE '%forbidden%' THEN
        NEW.dlq_category := 'authentication_error';
    ELSIF NEW.error_message ILIKE '%rate limit%' OR NEW.error_message ILIKE '%too many requests%' THEN
        NEW.dlq_category := 'rate_limit_error';
    ELSIF NEW.error_message ILIKE '%not found%' OR NEW.error_message ILIKE '%does not exist%' THEN
        NEW.dlq_category := 'not_found_error';
    ELSIF NEW.error_message ILIKE '%validation%' OR NEW.error_message ILIKE '%invalid%' THEN
        NEW.dlq_category := 'validation_error';
    ELSIF NEW.error_message ILIKE '%ai%' OR NEW.error_message ILIKE '%openai%' OR NEW.error_message ILIKE '%llm%' THEN
        NEW.dlq_category := 'ai_service_error';
    ELSIF NEW.error_message ILIKE '%database%' OR NEW.error_message ILIKE '%sql%' OR NEW.error_message ILIKE '%postgres%' THEN
        NEW.dlq_category := 'database_error';
    ELSIF NEW.error_message ILIKE '%kafka%' OR NEW.error_message ILIKE '%broker%' THEN
        NEW.dlq_category := 'messaging_error';
    ELSE
        NEW.dlq_category := 'unknown_error';
    END IF;
    
    -- Set priority based on category and retry count
    IF NEW.retry_count >= 3 THEN
        NEW.dlq_priority := 'high';
    ELSIF NEW.dlq_category IN ('authentication_error', 'database_error') THEN
        NEW.dlq_priority := 'high';
    ELSIF NEW.dlq_category IN ('timeout_error', 'connection_error') THEN
        NEW.dlq_priority := 'medium';
    ELSE
        NEW.dlq_priority := 'low';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-categorization
DROP TRIGGER IF EXISTS trigger_categorize_dlq ON dead_letter_queue;
CREATE TRIGGER trigger_categorize_dlq
    BEFORE INSERT ON dead_letter_queue
    FOR EACH ROW EXECUTE FUNCTION categorize_dlq_failure();

-- Update trigger for updated_at
CREATE TRIGGER update_dead_letter_queue_updated_at
    BEFORE UPDATE ON dead_letter_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for new DLQ items requiring review
CREATE OR REPLACE VIEW v_dlq_pending_review AS
SELECT
    id,
    original_request_id,
    customer_email,
    subject,
    failure_reason,
    error_message,
    dlq_category,
    dlq_priority,
    retry_count,
    created_at
FROM dead_letter_queue
WHERE dlq_status = 'new'
ORDER BY
    CASE dlq_priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    created_at ASC;

-- Create view for DLQ analytics
CREATE OR REPLACE VIEW v_dlq_analytics AS
SELECT
    DATE(created_at) as failure_date,
    dlq_category,
    COUNT(*) as failure_count,
    COUNT(*) FILTER (WHERE dlq_priority = 'critical') as critical_count,
    COUNT(*) FILTER (WHERE dlq_priority = 'high') as high_count,
    AVG(retry_count) as avg_retries,
    COUNT(*) FILTER (WHERE dlq_status = 'resolved') as resolved_count
FROM dead_letter_queue
GROUP BY DATE(created_at), dlq_category
ORDER BY failure_date DESC, failure_count DESC;
