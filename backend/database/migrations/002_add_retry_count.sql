-- Migration: Add retry_count column to message_queue
-- Run this on existing databases

-- Add retry_count column for tracking retry attempts
ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- Add last_retry_at for tracking when last retry was attempted
ALTER TABLE message_queue 
ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP WITH TIME ZONE;

-- Create index for retry queries
CREATE INDEX IF NOT EXISTS idx_message_queue_retry ON message_queue (status, retry_count, created_at);

-- Add comment for documentation
COMMENT ON COLUMN message_queue.retry_count IS 'Number of retry attempts (max 3)';
COMMENT ON COLUMN message_queue.last_retry_at IS 'Timestamp of last retry attempt';
