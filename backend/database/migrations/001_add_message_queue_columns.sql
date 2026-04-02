-- Migration: Add response, sentiment, and escalation columns to message_queue
-- Run this on existing databases that already have message_queue table

-- Add new columns for storing processing results
ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS response TEXT;

ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50);

ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS is_escalated BOOLEAN DEFAULT FALSE;

ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR(100);

-- Create indexes for new columns (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_message_queue_sentiment ON message_queue (sentiment);
CREATE INDEX IF NOT EXISTS idx_message_queue_escalated ON message_queue (is_escalated) WHERE is_escalated = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN message_queue.response IS 'AI-generated response sent to customer';
COMMENT ON COLUMN message_queue.sentiment IS 'Detected sentiment: positive, negative, neutral';
COMMENT ON COLUMN message_queue.is_escalated IS 'Whether the ticket requires human escalation';
COMMENT ON COLUMN message_queue.escalation_reason IS 'Reason for escalation if applicable';
