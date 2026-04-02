-- ============================================================================
-- Migration: Allow NULL customer_email for WhatsApp support
-- ============================================================================
-- Run this migration to support WhatsApp messages that use phone instead of email
--
-- Usage:
--   psql <connection_string> -f database/migrations/001_allow_null_customer_email.sql
-- ============================================================================

BEGIN;

-- Step 1: Drop NOT NULL constraint on customer_email
ALTER TABLE message_queue 
ALTER COLUMN customer_email DROP NOT NULL;

-- Step 2: Add comment explaining the change
COMMENT ON COLUMN message_queue.customer_email IS 
'Customer email address. NULL for WhatsApp/phone-only messages.';

-- Step 3: Update any check constraints if they exist
-- (This is safe to run even if constraint doesn't exist)
DO $$
BEGIN
    -- Check if constraint exists and drop it
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'message_queue_customer_email_check'
        AND table_name = 'message_queue'
    ) THEN
        ALTER TABLE message_queue 
        DROP CONSTRAINT message_queue_customer_email_check;
    END IF;
END$$;

-- Step 4: Add a new check constraint that allows NULL or valid email
-- (Optional - uncomment if you want validation)
-- ALTER TABLE message_queue
-- ADD CONSTRAINT message_queue_customer_contact_check
-- CHECK (
--     customer_email IS NOT NULL OR 
--     (metadata->>'customer_phone') IS NOT NULL
-- );

COMMIT;

-- Verify the change
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'message_queue'
AND column_name IN ('customer_email', 'subject', 'message', 'channel');
