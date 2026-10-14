"""Append-only audit trail of every agent run.

Each agent run adds one entry to output/audit_trail.json (a JSON array). Earlier entries are
never removed or changed. If the file exists but can't be read as a JSON array, nothing is
written, so a bad file is never replaced by a fresh one.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart

from models import AuditEntry, BlockedCall, TokenUsage, ToolCallRecord

AUDIT_FILE = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
OUTPUT_TOOL_PREFIX = "final_result"  # Pydantic AI's structured-output tool, not a real tool call

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tool_calls(messages: list[ModelMessage]) -> list[ToolCallRecord]:
    calls = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and not part.tool_name.startswith(OUTPUT_TOOL_PREFIX):
                    calls.append(ToolCallRecord(tool=part.tool_name, args=part.args_as_dict()))
    return calls


def token_usage(messages: list[ModelMessage]) -> TokenUsage:
    """Tokens for this agent's own model calls only (teammates' runs are counted in their entries)."""
    usage = TokenUsage()
    for msg in messages:
        if isinstance(msg, ModelResponse):
            usage.input_tokens += msg.usage.input_tokens
            usage.output_tokens += msg.usage.output_tokens
            usage.model_requests += 1
    usage.total_tokens = usage.input_tokens + usage.output_tokens
    return usage


def build_entry(
    *,
    started: str,
    run_id: str,
    ticket_id: int,
    agent: str,
    model: str,
    invoked_by: str,
    messages: list[ModelMessage],
    blocked: list[BlockedCall],
    ticket_tokens_total: int | None = None,
    aborted: bool = False,
    abort_reason: str | None = None,
    outcome: str | None = None,
) -> AuditEntry:
    calls = tool_calls(messages)
    return AuditEntry(
        timestamp=started,
        run_id=run_id,
        ticket_id=ticket_id,
        agent=agent,
        model=model,
        invoked_by=invoked_by,
        delegated_to=[c.args["agent"] for c in calls if c.tool == "ask_agent" and "agent" in c.args],
        tools_called=calls,
        tokens=token_usage(messages),
        ticket_tokens_total=ticket_tokens_total,
        blocked_calls=blocked,
        aborted=aborted,
        abort_reason=abort_reason,
        outcome=outcome,
    )


def record(entry: AuditEntry) -> None:
    """Append one entry to the audit file without touching earlier entries."""
    with _lock:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if AUDIT_FILE.exists() and AUDIT_FILE.read_text().strip():
            entries = json.loads(AUDIT_FILE.read_text())
            if not isinstance(entries, list):
                raise RuntimeError(f"{AUDIT_FILE} is not a JSON array; refusing to overwrite it")
        entries.append(entry.model_dump(mode="json"))
        tmp = AUDIT_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2))
        os.replace(tmp, AUDIT_FILE)
