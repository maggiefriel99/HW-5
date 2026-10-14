"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities, Customer Service.

Every agent runs on gpt-6-luna through Portkey and gets its shop tools from the MCP server
listed in .mcp.json; no agent reads the database directly. Any agent can hand work to any other
with `ask_agent` (full connectivity), within the safety limits below. Every agent run, including
delegated and aborted ones, appends an entry to output/audit_trail.json.

Run tickets from the HW 5 folder:
    .venv/bin/python backend/agents.py 101 102
    .venv/bin/python backend/agents.py --all
"""

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, capture_run_messages
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage, UsageLimits

import audit
from models import AgentName, AgentReport, BlockedCall, TicketDecision

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MCP_CONFIG = ROOT / ".mcp.json"

load_dotenv(ROOT / ".env")  # PORTKEY_API_KEY (see .env.example); real environment variables win

MODEL_NAME = "gpt-6-luna"  # the only model allowed in this assignment; every agent uses it
# The gpt-6-luna deployment behind Portkey rejects tool calls on chat completions when reasoning
# effort is set, so reasoning is turned off. This also keeps token use down.
MODEL_SETTINGS = {"openai_reasoning_effort": "none"}

# ---------- Safety limits (per ticket, shared by every agent working on it) ----------
TICKET_TOKEN_BUDGET = 60_000  # input + output tokens across all agents
TICKET_REQUEST_LIMIT = 30  # model calls across all agents
MAX_CHAIN_LENGTH = 3  # e.g. boss -> accounting -> inventory, and no further
MAX_DELEGATIONS = 6  # ask_agent calls per ticket
LIMITS = UsageLimits(total_tokens_limit=TICKET_TOKEN_BUDGET, request_limit=TICKET_REQUEST_LIMIT)

# Which MCP tools each agent may call. Everything else on the server is hidden from that agent.
AGENT_TOOLS: dict[AgentName, set[str]] = {
    "boss": {"list_open_tickets", "get_ticket", "update_ticket_status", "check_cash"},
    "inventory": {"get_ticket", "check_inventory", "list_vendors", "draft_purchase_order"},
    "accounting": {
        "get_ticket", "check_cash", "check_invoices", "prepare_payment",
        "evaluate_bulk_discount", "draft_purchase_order",
    },
    "facilities": {"get_ticket", "check_rent_due"},
    "customer_service": {"get_ticket", "check_inventory", "save_customer_draft"},
}


# ---------- Model and MCP connection ----------


def build_model() -> OpenAIChatModel:
    """gpt-6-luna, reached through the Portkey gateway with PORTKEY_API_KEY."""
    portkey_key = os.getenv("PORTKEY_API_KEY")
    if not portkey_key:
        raise RuntimeError("PORTKEY_API_KEY is not set")
    client = AsyncOpenAI(
        api_key=portkey_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": portkey_key},
    )
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


# ---------- Live events (what the board shows while a ticket runs) ----------

LIVE_EVENTS: list[dict] = []  # in memory; the audit trail is the permanent record
LIVE_TEXT_LIMIT = 220


def emit(kind: str, ticket_id: int, run_id: str, agent: str, text: str, **extra) -> None:
    """kind: started, tool, delegated, blocked, finished, aborted."""
    text = " ".join(str(text).split())
    LIVE_EVENTS.append({
        "index": len(LIVE_EVENTS), "time": audit.now(), "kind": kind, "ticket_id": ticket_id,
        "run_id": run_id, "agent": agent,
        "text": text if len(text) <= LIVE_TEXT_LIMIT else text[: LIVE_TEXT_LIMIT - 1] + "…",
        **extra,
    })


async def _live_tool_call(ctx: RunContext, call_tool, name: str, args: dict):
    """Report each MCP tool call to the live feed, then run it."""
    result = await call_tool(name, args)
    deps = ctx.deps
    if isinstance(deps, TeamDeps):
        emit("tool", deps.ticket_id, deps.run_id, deps.agent,
             json.dumps(result, default=str) if not isinstance(result, str) else result,
             tool=name, args=args)
    return result


def _mcp_config() -> dict:
    """.mcp.json uses paths relative to the project root (that's how Claude Code launches it).
    The backend runs from backend/, so resolve the paths here and start the server with this
    same Python, which already has the requirements installed."""
    config = json.loads(MCP_CONFIG.read_text())
    for server in config["mcpServers"].values():
        server["command"] = sys.executable
        server["args"] = [a if Path(a).is_absolute() else str(ROOT / a) for a in server.get("args", [])]
    return config


# One connection to the MCP server (launched from .mcp.json), shared by the whole team.
SHOP_TOOLS = MCPToolset(Client(_mcp_config()), process_tool_call=_live_tool_call)


def tools_for(name: AgentName):
    allowed = AGENT_TOOLS[name]
    return SHOP_TOOLS.filtered(lambda ctx, tool_def: tool_def.name in allowed)


# ---------- Run state ----------


@dataclass
class TicketBudget:
    """Shared by every agent run on one ticket."""

    delegations: int = 0


@dataclass
class TeamDeps:
    ticket_id: int
    run_id: str
    agent: AgentName
    chain: tuple[AgentName, ...]  # who is working on this ticket right now, Boss first
    budget: TicketBudget
    blocked: list[BlockedCall] = field(default_factory=list)


# ---------- Delegation ----------


def _delegation_blocked(deps: TeamDeps, target: AgentName) -> str | None:
    """Why a hand-off is not allowed, or None if it is."""
    if target == deps.agent:
        return "an agent cannot delegate to itself"
    if target in deps.chain:
        return (
            f"{target} is already waiting on this answer ({' -> '.join(deps.chain)}); "
            "put the question or escalation in your report instead of calling back"
        )
    if len(deps.chain) >= MAX_CHAIN_LENGTH:
        return f"delegation chain is already {len(deps.chain)} agents deep (limit {MAX_CHAIN_LENGTH})"
    if deps.budget.delegations >= MAX_DELEGATIONS:
        return f"ticket already used {MAX_DELEGATIONS} delegations (limit reached)"
    return None


async def ask_agent(ctx: RunContext[TeamDeps], agent: AgentName, request: str) -> str:
    """Hand part of this ticket to a teammate and get their report back.

    agent: boss, inventory, accounting, facilities, or customer_service.
    request: exactly what you need from them, including the ticket facts they need.
    """
    reason = _delegation_blocked(ctx.deps, agent)
    if reason:
        ctx.deps.blocked.append(BlockedCall(call=f"ask_agent(agent={agent!r})", reason=reason))
        emit("blocked", ctx.deps.ticket_id, ctx.deps.run_id, ctx.deps.agent, reason, to=agent)
        return f"BLOCKED by safety rule: {reason}"
    ctx.deps.budget.delegations += 1
    emit("delegated", ctx.deps.ticket_id, ctx.deps.run_id, ctx.deps.agent, request, to=agent)
    report = await run_agent(
        agent,
        f"[Ticket #{ctx.deps.ticket_id}] Request from {ctx.deps.agent}: {request}",
        ticket_id=ctx.deps.ticket_id,
        run_id=ctx.deps.run_id,
        chain=ctx.deps.chain + (agent,),
        budget=ctx.deps.budget,
        usage=ctx.usage,
        invoked_by=ctx.deps.agent,
    )
    return report.model_dump_json()


# ---------- The team ----------


def _make_agent(name: AgentName, output_type) -> Agent[TeamDeps, AgentReport | TicketDecision]:
    return Agent(
        build_model(),
        name=name,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(),
        model_settings=MODEL_SETTINGS,
        toolsets=[tools_for(name)],
        tools=[ask_agent],
        retries=2,
    )


AGENTS: dict[AgentName, Agent] = {
    "boss": _make_agent("boss", TicketDecision),
    "inventory": _make_agent("inventory", AgentReport),
    "accounting": _make_agent("accounting", AgentReport),
    "facilities": _make_agent("facilities", AgentReport),
    "customer_service": _make_agent("customer_service", AgentReport),
}


async def run_agent(
    name: AgentName,
    prompt: str,
    *,
    ticket_id: int,
    run_id: str,
    chain: tuple[AgentName, ...],
    budget: TicketBudget,
    usage: RunUsage,
    invoked_by: str,
) -> AgentReport | TicketDecision:
    """Run one agent and append its audit entry, whether it finishes or is aborted."""
    deps = TeamDeps(ticket_id=ticket_id, run_id=run_id, agent=name, chain=chain, budget=budget)
    started = audit.now()
    entry_args = dict(
        started=started, run_id=run_id, ticket_id=ticket_id, agent=name,
        model=MODEL_NAME, invoked_by=invoked_by, blocked=deps.blocked,
    )
    top_level = invoked_by == "runner"
    emit("started", ticket_id, run_id, name, prompt, invoked_by=invoked_by)
    with capture_run_messages() as messages:
        try:
            result = await AGENTS[name].run(prompt, deps=deps, usage=usage, usage_limits=LIMITS)
        except UsageLimitExceeded as exc:
            emit("aborted", ticket_id, run_id, name, f"Safety limit hit: {exc}")
            audit.record(audit.build_entry(
                **entry_args, messages=messages, aborted=True,
                abort_reason=f"Safety limit hit: {exc}",
                ticket_tokens_total=usage.total_tokens if top_level else None,
            ))
            raise
        except Exception as exc:
            emit("aborted", ticket_id, run_id, name, f"{type(exc).__name__}: {exc}")
            audit.record(audit.build_entry(
                **entry_args, messages=messages, aborted=True,
                abort_reason=f"{type(exc).__name__}: {exc}",
                ticket_tokens_total=usage.total_tokens if top_level else None,
            ))
            raise

    output = result.output
    outcome = output.decision if isinstance(output, TicketDecision) else output.summary
    emit("finished", ticket_id, run_id, name, outcome)
    audit.record(audit.build_entry(
        **entry_args, messages=result.new_messages(), outcome=outcome,
        ticket_tokens_total=usage.total_tokens if top_level else None,
    ))
    return output


async def run_ticket(ticket_id: int) -> TicketDecision | None:
    """The Boss takes the ticket and pulls in whoever it needs. Returns None if aborted."""
    try:
        return await run_agent(
            "boss",
            f"Work ticket #{ticket_id}.",
            ticket_id=ticket_id,
            run_id=uuid.uuid4().hex[:12],
            chain=("boss",),
            budget=TicketBudget(),
            usage=RunUsage(),
            invoked_by="runner",
        )
    except UsageLimitExceeded as exc:
        print(f"Ticket #{ticket_id} aborted by safety limit: {exc}", file=sys.stderr)
        return None


async def main(args: list[str]) -> None:
    async with SHOP_TOOLS:  # keep one MCP server process up for the whole run
        if args == ["--all"]:
            board = await SHOP_TOOLS.direct_call_tool("list_open_tickets", {})
            ticket_ids = [t["id"] for t in board["tickets"]]
        else:
            ticket_ids = [int(a) for a in args]
        for ticket_id in ticket_ids:
            decision = await run_ticket(ticket_id)
            if decision:
                print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1:]))
