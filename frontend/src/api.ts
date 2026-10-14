// Every call the board makes to the FastAPI backend (backend/main.py).

export const API_BASE = "http://localhost:8000";

export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  status: "open" | "in_progress" | "waiting_on_approval" | "resolved";
  notes: string | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
}

export interface LiveEvent {
  index: number;
  time: string;
  kind: "started" | "tool" | "delegated" | "blocked" | "finished" | "aborted";
  ticket_id: number;
  run_id: string;
  agent: AgentName;
  text: string;
  tool?: string;
  args?: Record<string, unknown>;
  to?: AgentName;
  invoked_by?: string;
}

export interface AuditEvent {
  index: number;
  timestamp: string;
  run_id: string;
  ticket_id: number;
  agent: AgentName;
  model: string;
  invoked_by: string;
  delegated_to: AgentName[];
  tools_called: { tool: string; args: Record<string, unknown> }[];
  tokens: { input_tokens: number; output_tokens: number; total_tokens: number; model_requests: number };
  ticket_tokens_total: number | null;
  blocked_calls: { call: string; reason: string }[];
  aborted: boolean;
  abort_reason: string | null;
  outcome: string | null;
}

export interface Approval {
  id: number;
  ticket_id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number;
  sku: string | null;
  size: string | null;
  qty: number | null;
  payee: string;
  amount: number;
  reason: string;
  status: "pending" | "approved";
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
}

export interface TicketDecision {
  ticket_id: number;
  decision: string;
  status: string;
  summary: string;
  agents_consulted: AgentName[];
}

export interface RunResult {
  ticket_id: number;
  aborted: boolean;
  detail?: string;
  decision?: TicketDecision;
  approvals_queued?: Approval[];
}

export interface EventsResponse {
  total: number;
  events: AuditEvent[];
  live_total: number;
  live: LiveEvent[];
  running: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export const api = {
  tickets: () => request<{ date_today: string; tickets: Ticket[] }>("/api/tickets"),
  runTicket: (id: number) => request<RunResult>(`/api/tickets/${id}/run`, { method: "POST" }),
  events: (since: number, liveSince: number) =>
    request<EventsResponse>(`/api/events?since=${since}&live_since=${liveSince}`),
  approvals: () => request<{ approvals: Approval[] }>("/api/approvals"),
  approve: (id: number, approvedBy: string) =>
    request<{ amount: number; balance_after: number; payee: string }>(`/api/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  cash: () => request<{ name: string; balance: number; date: string }>("/api/cash"),
  reset: () => request<{ reset: boolean }>("/api/reset", { method: "POST" }),
};
