import type { AgentName, AuditEvent, RunResult, Ticket } from "../api";
import { DANS, DAN_ORDER } from "../dans";
import { Dan } from "./Dan";

const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

interface Props {
  dateToday: string;
  tickets: Ticket[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onRun: (id: number) => void;
  runningId: number | null;
  elapsed: number;
  runResults: Record<number, RunResult>;
  audit: AuditEvent[];
  error: string | null;
}

function StatusBadge({ status }: { status: Ticket["status"] }) {
  return <span className={`badge badge-${status}`}>{status.replace(/_/g, " ")}</span>;
}

/** What each agent did on the ticket's most recent run, from the audit trail. */
function AgentSummaries({ entries }: { entries: AuditEvent[] }) {
  const byAgent = new Map<AgentName, AuditEvent[]>();
  for (const e of entries) byAgent.set(e.agent, [...(byAgent.get(e.agent) ?? []), e]);
  const total = entries.find((e) => e.invoked_by === "runner")?.ticket_tokens_total;

  return (
    <div className="summaries">
      <div className="summaries-head">
        <h3>What each Dan did</h3>
        {total != null && <span className="token-pill">{total.toLocaleString()} tokens total</span>}
      </div>
      {DAN_ORDER.filter((a) => byAgent.has(a)).map((agent) => {
        const runs = byAgent.get(agent)!;
        const tools = runs.flatMap((r) => r.tools_called.map((t) => t.tool)).filter((t) => t !== "ask_agent");
        const delegated = [...new Set(runs.flatMap((r) => r.delegated_to))];
        const tokens = runs.reduce((n, r) => n + r.tokens.total_tokens, 0);
        const aborted = runs.find((r) => r.aborted);
        const blocked = runs.flatMap((r) => r.blocked_calls);
        return (
          <div key={agent} className="summary-card" style={{ ["--accent" as any]: DANS[agent].accent }}>
            <Dan agent={agent} mood={aborted ? "aborted" : "done"} size={46} />
            <div className="summary-body">
              <div className="summary-name">
                {DANS[agent].name} <span className="summary-role">{DANS[agent].role}</span>
                <span className="summary-tokens">{tokens.toLocaleString()} tok</span>
              </div>
              {runs.map((r) => r.outcome && <p key={r.index} className="summary-outcome">{r.outcome}</p>)}
              {aborted && <p className="summary-aborted">Stopped: {aborted.abort_reason}</p>}
              <div className="chips">
                {[...new Set(tools)].map((t) => <code key={t} className="chip">{t}</code>)}
                {delegated.map((d) => <span key={d} className="chip chip-delegate">→ {DANS[d].name}</span>)}
              </div>
              {blocked.map((b, i) => <p key={i} className="summary-blocked">⛔ {b.call}: {b.reason}</p>)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function TicketColumn(p: Props) {
  const selected = p.tickets.find((t) => t.id === p.selectedId) ?? null;
  const ticketAudit = selected ? p.audit.filter((e) => e.ticket_id === selected.id) : [];
  const lastRunId = ticketAudit.at(-1)?.run_id;
  const lastRun = ticketAudit.filter((e) => e.run_id === lastRunId);
  const result = selected ? p.runResults[selected.id] : undefined;
  const bossEntry = lastRun.find((e) => e.invoked_by === "runner");
  const isRunning = selected != null && p.runningId === selected.id;

  return (
    <main className="column tickets-column">
      <h2 className="column-title">Ticket Desk <span className="desk-date">Shop date {p.dateToday}</span></h2>

      <div className="ticket-list">
        {p.tickets.map((t) => (
          <button
            key={t.id}
            className={`ticket-card ${t.id === p.selectedId ? "selected" : ""} ${p.runningId === t.id ? "running" : ""}`}
            onClick={() => p.onSelect(t.id)}
          >
            <div className="ticket-top">
              <span className="ticket-id">#{t.id}</span>
              <StatusBadge status={t.status} />
            </div>
            <div className="ticket-subject">{t.subject}</div>
            <div className="ticket-meta">{TYPE_LABEL[t.type] ?? t.type} · {t.requester}</div>
          </button>
        ))}
      </div>

      {p.error && <div className="error-banner">{p.error}</div>}

      {!selected ? (
        <div className="empty-panel">Pick a ticket to put the Dans to work.</div>
      ) : (
        <section className="ticket-detail">
          <div className="detail-head">
            <div>
              <div className="detail-kicker">{TYPE_LABEL[selected.type] ?? selected.type} · from {selected.requester}</div>
              <h3 className="detail-title">#{selected.id} · {selected.subject}</h3>
            </div>
            <StatusBadge status={selected.status} />
          </div>
          <p className="detail-notes">"{selected.notes}"</p>
          <div className="detail-facts">
            {selected.sku && <span><b>SKU</b> {selected.sku}</span>}
            {selected.size && <span><b>Size</b> {selected.size}</span>}
            {selected.qty != null && <span><b>Qty</b> {selected.qty}</span>}
          </div>

          <button
            className="run-button"
            disabled={p.runningId != null}
            onClick={() => p.onRun(selected.id)}
          >
            {isRunning
              ? `The Dans are on it… ${p.elapsed}s`
              : p.runningId != null
                ? `Busy with ticket #${p.runningId}`
                : selected.status === "resolved" ? "Run the team again" : "Start the agent team"}
          </button>

          {isRunning && <div className="progress-strip"><span /></div>}

          {result?.aborted && <div className="error-banner">Run stopped by a safety limit. Check the live feed for why.</div>}

          {(result?.decision || bossEntry?.outcome) && (
            <div className="decision">
              <div className="decision-label">Big Dan's call</div>
              <p className="decision-text">{result?.decision?.decision ?? bossEntry?.outcome}</p>
              {result?.decision?.summary && <p className="decision-summary">{result.decision.summary}</p>}
              {result?.approvals_queued && result.approvals_queued.length > 0 && (
                <p className="decision-approvals">
                  {result.approvals_queued.length} item(s) sent to the approval panel →
                </p>
              )}
            </div>
          )}

          {lastRun.length > 0 && <AgentSummaries entries={lastRun} />}
        </section>
      )}
    </main>
  );
}
