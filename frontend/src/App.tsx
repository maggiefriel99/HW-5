import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Approval, type AuditEvent, type LiveEvent, type RunResult, type Ticket } from "./api";
import { AgentColumn } from "./components/AgentColumn";
import { MoneyColumn } from "./components/MoneyColumn";
import { TicketColumn } from "./components/TicketColumn";

const POLL_MS = 1000;

export default function App() {
  const [dateToday, setDateToday] = useState("");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [live, setLive] = useState<LiveEvent[]>([]);
  const [liveFloor, setLiveFloor] = useState(0); // live events before this index are from before the last reset
  const [runningId, setRunningId] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [runResults, setRunResults] = useState<Record<number, RunResult>>({});
  const [approver, setApprover] = useState(() => localStorage.getItem("approver") ?? "");
  const [approving, setApproving] = useState<number | null>(null);
  const [approvalErrors, setApprovalErrors] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const counts = useRef({ audit: 0, live: 0 });
  const polling = useRef(false); // never run two polls at once, or events would be added twice

  const refreshBoard = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setDateToday(t.date_today);
      setTickets(t.tickets);
      setBalance(c.balance);
      setApprovals(a.approvals);
      setError(null);
    } catch (e) {
      setError(`Can't reach the backend at http://localhost:8000 (${(e as Error).message}). Is uvicorn running?`);
    }
  }, []);

  const pollEvents = useCallback(async () => {
    if (polling.current) return;
    polling.current = true;
    try {
      const r = await api.events(counts.current.audit, counts.current.live);
      if (r.events.length) setAudit((prev) => [...prev, ...r.events]);
      if (r.live.length) setLive((prev) => [...prev, ...r.live]);
      const changed = r.events.length > 0 || r.live.length > 0;
      counts.current = { audit: r.total, live: r.live_total };
      if (changed) {
        const t = await api.tickets();
        setTickets(t.tickets);
      }
    } catch {
      /* the board banner already reports a missing backend */
    } finally {
      polling.current = false;
    }
  }, []);

  useEffect(() => {
    refreshBoard();
    pollEvents();
    const id = setInterval(pollEvents, POLL_MS);
    return () => clearInterval(id);
  }, [refreshBoard, pollEvents]);

  useEffect(() => {
    if (runningId == null) return;
    setElapsed(0);
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [runningId]);

  useEffect(() => localStorage.setItem("approver", approver), [approver]);

  async function runTicket(id: number) {
    setRunningId(id);
    setError(null);
    try {
      const result = await api.runTicket(id);
      setRunResults((prev) => ({ ...prev, [id]: result }));
    } catch (e) {
      setError(`Run failed: ${(e as Error).message}`);
    } finally {
      setRunningId(null);
      await pollEvents();
      await refreshBoard();
    }
  }

  async function approve(id: number) {
    setApproving(id);
    setApprovalErrors((prev) => ({ ...prev, [id]: "" }));
    try {
      await api.approve(id, approver.trim());
    } catch (e) {
      setApprovalErrors((prev) => ({ ...prev, [id]: (e as Error).message }));
    } finally {
      setApproving(null);
      await refreshBoard();
    }
  }

  async function reset() {
    if (!window.confirm("Reset the shop database to the original values? Payments, approvals, drafts and ticket statuses are cleared. The audit trail is kept.")) return;
    try {
      await api.reset();
      setRunResults({});
      setApprovalErrors({});
      setLiveFloor(counts.current.live);
      await refreshBoard();
    } catch (e) {
      setError(`Reset failed: ${(e as Error).message}`);
    }
  }

  // The Dans show the most recent run (since the last reset).
  const sinceReset = live.filter((e) => e.index >= liveFloor);
  const lastRunId = [...sinceReset].reverse().find((e) => e.kind === "started" && e.invoked_by === "runner")?.run_id;
  const runEvents = sinceReset.filter((e) => e.run_id === lastRunId);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">Y</span>
          <div>
            <h1>Campus Customs · Dan Ops Board</h1>
            <p>Five Handsome Dans run the shop. You hold the checkbook.</p>
          </div>
        </div>
        <button className="reset-button" onClick={reset} disabled={runningId != null}>↺ Fresh run (reset DB)</button>
      </header>

      <div className="columns">
        <AgentColumn runEvents={runEvents} feed={sinceReset} running={runningId != null} />
        <TicketColumn
          dateToday={dateToday}
          tickets={tickets}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onRun={runTicket}
          runningId={runningId}
          elapsed={elapsed}
          runResults={runResults}
          audit={audit}
          error={error}
        />
        <MoneyColumn
          balance={balance}
          approvals={approvals}
          approver={approver}
          onApproverChange={setApprover}
          onApprove={approve}
          approving={approving}
          approvalErrors={approvalErrors}
        />
      </div>
    </div>
  );
}
