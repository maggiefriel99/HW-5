"""FastAPI backend for the Campus Customs operations board.

Run from the backend folder:
    uvicorn main:app --reload --port 8000

Shop reads go through the MCP server (the same one the agents use). Paying is done only by the
approve route, after a person clicks approve.
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import agents
import approvals
import audit
from models import ApproveRequest

_run_lock = asyncio.Lock()  # one agent run at a time, so two runs never spend the same cash


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with agents.SHOP_TOOLS:  # keep one MCP server process up while the API runs
        yield


app = FastAPI(title="Campus Customs Multi-Agent Operations", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _mcp(tool: str, args: dict | None = None) -> dict:
    return await agents.SHOP_TOOLS.direct_call_tool(tool, args or {})


@app.get("/api/tickets")
async def list_tickets():
    """Every ticket on the board and its status."""
    board = await _mcp("list_tickets")
    return {
        "date_today": board["date_today"],
        "tickets": [
            {k: t[k] for k in ("id", "type", "requester", "subject", "status", "notes", "sku", "size", "qty")}
            for t in board["tickets"]
        ],
    }


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int):
    """Run the agent team on one ticket and queue whatever it wants a person to approve."""
    ticket = await _mcp("get_ticket", {"ticket_id": ticket_id})
    if "error" in ticket:
        raise HTTPException(404, ticket["error"])
    if _run_lock.locked():
        raise HTTPException(409, "The team is already working on a ticket; try again when it finishes")
    async with _run_lock:
        try:
            decision = await agents.run_ticket(ticket_id)
            detail = "Run stopped by a safety limit; see /api/events"
        except Exception as exc:  # e.g. the model API failed; the audit trail already has the details
            decision, detail = None, f"Run failed: {type(exc).__name__}: {exc}"
    if decision is None:
        await _mcp("update_ticket_status", {"ticket_id": ticket_id, "status": "open"})  # can be run again
        return {"ticket_id": ticket_id, "aborted": True, "detail": detail}
    await _mcp("update_ticket_status", {"ticket_id": ticket_id, "status": "resolved"})
    queued = approvals.queue_from_decision(decision)
    return {"ticket_id": ticket_id, "aborted": False, "decision": decision, "approvals_queued": queued}


@app.get("/api/events")
def recent_events(
    since: int = Query(0, ge=0, description="Number of audit events the board already has"),
    live_since: int = Query(0, ge=0, description="Number of live events the board already has"),
    ticket_id: int | None = None,
):
    """Agent events so the board can refresh.

    `live` is the step-by-step feed while a ticket runs (started, tool, delegated, blocked,
    finished, aborted). `events` are the finished audit-trail entries (tools, tokens, outcome).
    """
    entries = json.loads(audit.AUDIT_FILE.read_text()) if audit.AUDIT_FILE.exists() else []
    events = [{"index": i, **e} for i, e in enumerate(entries) if i >= since]
    live = agents.LIVE_EVENTS[live_since:]
    if ticket_id is not None:
        events = [e for e in events if e["ticket_id"] == ticket_id]
        live = [e for e in live if e["ticket_id"] == ticket_id]
    return {
        "total": len(entries),
        "events": events,
        "live_total": len(agents.LIVE_EVENTS),
        "live": live,
        "running": _run_lock.locked(),
    }


@app.get("/api/approvals")
def list_approvals():
    """Payments and purchase orders the agents prepared, pending or approved."""
    return {"approvals": approvals.list_approvals()}


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: int, body: ApproveRequest):
    """A person approved it: pay it, take the cash out of checking, and record the payment."""
    try:
        return approvals.approve(approval_id, body.approved_by)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except approvals.ApprovalRefused as exc:
        raise HTTPException(409, str(exc))


@app.get("/api/cash")
async def cash():
    """Current checking balance from cash_accounts."""
    accounts = (await _mcp("check_cash"))["accounts"]
    checking = next((a for a in accounts if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account")
    return checking


@app.post("/api/reset")
async def reset():
    """Copy the original database over the working copy for a fresh run. The audit trail is kept."""
    if _run_lock.locked():
        raise HTTPException(409, "Can't reset while the team is working on a ticket")
    approvals.reset_database()
    return {"reset": True, "database": "data/campus_customs_new.db restored from data/campus_customs.db"}
