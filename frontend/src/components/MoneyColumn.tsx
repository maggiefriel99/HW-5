import { useEffect, useRef, useState } from "react";
import type { Approval } from "../api";

const money = (n: number) =>
  `${n < 0 ? "-" : ""}$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const KIND_LABEL: Record<Approval["kind"], string> = {
  invoice: "Vendor invoice",
  rent: "Rent",
  purchase_order: "Purchase order",
};
const KIND_ICON: Record<Approval["kind"], string> = { invoice: "🧾", rent: "🏠", purchase_order: "📦" };

/** Counts smoothly from the old value to the new one. */
function useCountTo(target: number, ms = 1100) {
  const [shown, setShown] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const start = performance.now();
    const begin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(begin + (target - begin) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else from.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      from.current = target;
    };
  }, [target, ms]);
  return shown;
}

interface Props {
  balance: number | null;
  approvals: Approval[];
  approver: string;
  onApproverChange: (name: string) => void;
  onApprove: (id: number) => void;
  approving: number | null;
  approvalErrors: Record<number, string>;
}

export function MoneyColumn(p: Props) {
  const balance = p.balance ?? 0;
  const shown = useCountTo(balance);
  const pending = p.approvals.filter((a) => a.status === "pending");
  const approved = p.approvals.filter((a) => a.status === "approved");
  const pendingTotal = pending.reduce((n, a) => n + a.amount, 0);
  const paidTotal = approved.reduce((n, a) => n + a.amount, 0);
  const projected = balance - pendingTotal;
  const start = balance + paidTotal;
  const pct = (n: number) => `${start > 0 ? Math.max(0, Math.min(100, (n / start) * 100)) : 0}%`;

  // Flash the change whenever the balance moves.
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null);
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (p.balance == null) return;
    if (last.current != null && p.balance !== last.current) {
      setDelta({ amount: p.balance - last.current, key: Date.now() });
    }
    last.current = p.balance;
  }, [p.balance]);

  return (
    <aside className="column money-column">
      <section className="finance-hero">
        <div className="finance-label">Checking balance</div>
        <div className={`finance-balance ${balance < 500 ? "low" : ""}`}>
          {p.balance == null ? "—" : money(shown)}
          {delta && (
            <span key={delta.key} className={`finance-delta ${delta.amount < 0 ? "down" : "up"}`}>
              {delta.amount < 0 ? "−" : "+"}{money(Math.abs(delta.amount))}
            </span>
          )}
        </div>

        <div className="finance-bar" title="Paid out · waiting for approval · free cash">
          <span className="bar-paid" style={{ width: pct(paidTotal) }} />
          <span className="bar-pending" style={{ width: pct(Math.min(pendingTotal, balance)) }} />
        </div>

        <div className="finance-stats">
          <div>
            <span className="stat-label">Waiting for approval</span>
            <span className="stat-value pending">{money(pendingTotal)}</span>
            <span className="stat-sub">{pending.length} item(s)</span>
          </div>
          <div>
            <span className="stat-label">If all approved</span>
            <span className={`stat-value ${projected < 0 ? "negative" : ""}`}>{money(projected)}</span>
            <span className="stat-sub">{projected < 0 ? "Not enough cash for all" : "Still in the black"}</span>
          </div>
          <div>
            <span className="stat-label">Paid out</span>
            <span className="stat-value paid">{money(paidTotal)}</span>
            <span className="stat-sub">{approved.length} payment(s)</span>
          </div>
        </div>
        <p className="finance-note">Cash only goes out. Nothing is paid until a person clicks approve.</p>
      </section>

      <section className="approvals">
        <h2 className="column-title">Payment Approvals</h2>
        <label className="approver">
          Approving as
          <input value={p.approver} onChange={(e) => p.onApproverChange(e.target.value)} placeholder="Your name" />
        </label>

        {pending.length === 0 && <div className="empty-approvals">Nothing waiting. The Dans will send payments here.</div>}
        {pending.map((a) => (
          <div key={a.id} className={`approval-card kind-${a.kind}`}>
            <div className="approval-top">
              <span className="approval-kind">{KIND_ICON[a.kind]} {KIND_LABEL[a.kind]}</span>
              <span className="approval-ticket">ticket #{a.ticket_id}</span>
            </div>
            <div className="approval-amount">{money(a.amount)}</div>
            <div className="approval-payee">to {a.payee}</div>
            {a.kind === "purchase_order" && <div className="approval-detail">{a.qty} × {a.sku} {a.size}</div>}
            <div className="approval-reason">{a.reason}</div>
            <div className="approval-after">
              Balance after: <b className={balance - a.amount < 0 ? "negative" : ""}>{money(balance - a.amount)}</b>
            </div>
            {p.approvalErrors[a.id] && <div className="approval-error">{p.approvalErrors[a.id]}</div>}
            <button
              className="approve-button"
              disabled={!p.approver.trim() || p.approving != null}
              onClick={() => p.onApprove(a.id)}
            >
              {p.approving === a.id ? "Paying…" : p.approver.trim() ? `Approve ${money(a.amount)}` : "Enter your name to approve"}
            </button>
          </div>
        ))}

        {approved.length > 0 && (
          <>
            <h3 className="approved-title">Approved</h3>
            {approved.map((a) => (
              <div key={a.id} className="approved-row">
                <span>✅ {KIND_LABEL[a.kind]} · {a.payee}</span>
                <b>{money(a.amount)}</b>
                <span className="approved-by">by {a.approved_by}</span>
              </div>
            ))}
          </>
        )}
      </section>
    </aside>
  );
}
