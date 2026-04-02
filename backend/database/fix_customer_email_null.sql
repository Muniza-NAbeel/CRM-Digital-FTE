-- Fix message_queue table to allow NULL customer_email
-- This is needed for WhatsApp messages which use phone instead of email

ALTER TABLE message_queue 
ALTER COLUMN customer_email DROP NOT NULL;

-- Also update the unique constraint if it exists
-- (may need to be recreated)

COMMENT ON COLUMN message_queue.customer_email IS 'Customer email (NULL for WhatsApp/phone-only messages)';
