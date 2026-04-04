import { SubmitTicketRequest, SubmitTicketResponse, TicketStatusResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-api-key-12345';

export async function submitTicket(data: SubmitTicketRequest): Promise<SubmitTicketResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/messages/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to submit ticket' }));
    throw new Error(error.detail || 'Failed to submit ticket');
  }

  return response.json();
}

export async function checkTicketStatus(requestId: string): Promise<TicketStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/messages/status/${requestId}`, {
    method: 'GET',
    headers: {
      'X-API-Key': API_KEY,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch ticket status' }));
    throw new Error(error.detail || 'Failed to fetch ticket status');
  }

  return response.json();
}
