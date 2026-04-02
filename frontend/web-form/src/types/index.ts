export interface SubmitTicketRequest {
  name?: string;
  customer_email: string;
  customer_phone?: string;
  subject: string;
  message: string;
  channel?: string;
  category?: 'general' | 'technical' | 'billing' | 'feedback' | 'bug_report';
  priority?: 'low' | 'medium' | 'high';
}

export interface SubmitTicketResponse {
  request_id: string;
  status: string;
}

export interface TicketStatusResponse {
  request_id: string;
  ticket_number: string;
  status: string;
  response?: string;
  messages?: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
  sentiment?: string;
  created_at: string | null;
  updated_at: string;
  customer_email?: string;
  customer_name?: string;
  customer_phone?: string;
  subject?: string;
  category?: string;
  priority?: string;
}

export type FormStatus = 'idle' | 'submitting' | 'success' | 'error';
