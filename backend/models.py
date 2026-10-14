"""Data types shared by the agent team and the audit trail."""

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "resolved"]


# ---------- What agents hand back ----------


class PaymentProposal(BaseModel):
    """A payment an agent wants a human to approve. Amounts come from prepare_payment."""

    kind: Literal["invoice", "rent"]
    ref_id: int = Field(description="invoices.id for an invoice, leases.id for rent")
    payee: str
    amount: float
    account: str = "checking"
    reason: str


class PurchaseOrderProposal(BaseModel):
    """A restock order an agent wants a human to approve. Values come from draft_purchase_order."""

    vendor_id: int
    sku: str
    size: str
    qty: int
    total_cost: float
    earliest_arrival: str
    blocked: bool = Field(description="True if the vendor has an open unpaid invoice and will not ship yet")


class AgentReport(BaseModel):
    """What a specialist (or a teammate asked for help) reports back."""

    summary: str
    facts: list[str] = Field(default_factory=list, description="Shop facts used, each taken from a tool result")
    recommendation: str
    payments_for_approval: list[PaymentProposal] = Field(default_factory=list)
    purchase_orders_for_approval: list[PurchaseOrderProposal] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list, description="IDs returned by save_customer_draft")
    needs_boss_decision: bool = False
    question_for_boss: str | None = None


class TicketDecision(BaseModel):
    """The Boss's final call on a ticket."""

    ticket_id: int
    decision: str
    status: TicketStatus
    summary: str
    agents_consulted: list[AgentName] = Field(default_factory=list)
    payments_for_approval: list[PaymentProposal] = Field(default_factory=list)
    purchase_orders_for_approval: list[PurchaseOrderProposal] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list)


# ---------- Audit trail ----------


class ToolCallRecord(BaseModel):
    tool: str
    args: dict


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_requests: int = 0


class BlockedCall(BaseModel):
    """A call a safety rule stopped before it ran."""

    call: str
    reason: str


class AuditEntry(BaseModel):
    """One agent run on one ticket. Delegated runs get their own entry with the same run_id."""

    timestamp: str
    run_id: str
    ticket_id: int
    agent: AgentName
    model: str
    invoked_by: str = Field(description='"runner" for the Boss, otherwise the agent that delegated')
    delegated_to: list[AgentName] = Field(default_factory=list)
    tools_called: list[ToolCallRecord] = Field(default_factory=list)
    tokens: TokenUsage
    ticket_tokens_total: int | None = Field(default=None, description="All agents combined; set on the Boss entry")
    blocked_calls: list[BlockedCall] = Field(default_factory=list)
    aborted: bool = False
    abort_reason: str | None = None
    outcome: str | None = None


# ---------- API ----------


ApprovalKind = Literal["invoice", "rent", "purchase_order"]


class Approval(BaseModel):
    """A payment or purchase order an agent prepared, waiting for a person to approve it."""

    id: int
    ticket_id: int
    kind: ApprovalKind
    ref_id: int = Field(description="invoices.id, leases.id, or vendors.id for a purchase order")
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    payee: str
    amount: float = Field(description="Taken from the database, not from the agent")
    reason: str
    status: Literal["pending", "approved"]
    created_at: str
    approved_by: str | None = None
    approved_at: str | None = None


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the person clicking approve")
