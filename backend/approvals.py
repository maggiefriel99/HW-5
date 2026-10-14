"""Human approvals: the only code that moves money, and the database reset.

Agents can only prepare payments and purchase orders (see prepare_payment and
draft_purchase_order on the MCP server). When a run finishes, the Boss's proposals are queued
here as pending approvals. Cash only changes when a person approves one through the API.

This module is deliberately not an MCP tool, so no agent can ever reach it. Every amount is
read from the database at approval time; the agent's numbers are never trusted.
"""

import shutil
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from models import Approval, TicketDecision

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"


class ApprovalRefused(Exception):
    """The approval breaks a shop rule (not enough cash, vendor blocked, already paid)."""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            ref_id INTEGER NOT NULL,
            sku TEXT,
            size TEXT,
            qty INTEGER,
            payee TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            approved_by TEXT,
            approved_at TEXT
        )"""
    )
    return conn


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month).isoformat()


def _quote(conn, kind: str, ref_id: int, sku: str | None, qty: int | None) -> tuple[str, float]:
    """Payee and amount straight from the database."""
    if kind == "invoice":
        row = conn.execute(
            "SELECT v.name, i.amount FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (ref_id,),
        ).fetchone()
    elif kind == "rent":
        row = conn.execute("SELECT landlord, monthly_rent FROM leases WHERE id = ?", (ref_id,)).fetchone()
    else:
        vendor = conn.execute("SELECT name FROM vendors WHERE id = ?", (ref_id,)).fetchone()
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        row = (vendor[0], round(price[0] * qty, 2)) if vendor and price and qty else None
    if row is None:
        raise ApprovalRefused(f"Nothing in the database matches {kind} {ref_id}")
    return row[0], row[1]


def _row_to_approval(row) -> Approval:
    return Approval(**dict(row))


# ---------- Queue proposals from a run ----------


def queue_from_decision(decision: TicketDecision) -> list[Approval]:
    """Store the Boss's proposals as pending approvals, skipping ones already pending."""
    items = [(p.kind, p.ref_id, None, None, None, p.reason) for p in decision.payments_for_approval]
    items += [
        ("purchase_order", po.vendor_id, po.sku, po.size, po.qty, f"Restock {po.qty} x {po.sku} {po.size}")
        for po in decision.purchase_orders_for_approval
    ]
    queued = []
    with _connect() as conn:
        for kind, ref_id, sku, size, qty, reason in items:
            duplicate = conn.execute(
                "SELECT 1 FROM approvals WHERE status = 'pending' AND kind = ? AND ref_id = ? "
                "AND IFNULL(sku, '') = IFNULL(?, '') AND IFNULL(size, '') = IFNULL(?, '')",
                (kind, ref_id, sku, size),
            ).fetchone()
            if duplicate:
                continue
            try:
                payee, amount = _quote(conn, kind, ref_id, sku, qty)
            except ApprovalRefused:
                continue  # the agent proposed something that isn't in the database
            cur = conn.execute(
                "INSERT INTO approvals (ticket_id, kind, ref_id, sku, size, qty, payee, amount, reason, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
                (decision.ticket_id, kind, ref_id, sku, size, qty, payee, amount, reason,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            queued.append(cur.lastrowid)
        rows = conn.execute(
            f"SELECT * FROM approvals WHERE id IN ({','.join('?' * len(queued))})", queued
        ).fetchall() if queued else []
    return [_row_to_approval(r) for r in rows]


def list_approvals() -> list[Approval]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM approvals ORDER BY id").fetchall()
    return [_row_to_approval(r) for r in rows]


# ---------- Approve: the only place cash goes out ----------


def approve(approval_id: int, approved_by: str, account: str = "checking") -> dict:
    """Pay an approved item. All checks and writes happen in one transaction."""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        item = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if item is None:
            raise LookupError(f"No approval with id {approval_id}")
        if item["status"] != "pending":
            raise ApprovalRefused(f"Approval {approval_id} is already {item['status']}")

        kind, ref_id = item["kind"], item["ref_id"]
        today = _today(conn)
        payee, amount = _quote(conn, kind, ref_id, item["sku"], item["qty"])

        if kind == "invoice":
            status = conn.execute("SELECT status FROM invoices WHERE id = ?", (ref_id,)).fetchone()["status"]
            if status != "open":
                raise ApprovalRefused(f"Invoice {ref_id} is already {status}")
        if kind == "purchase_order":
            blocking = conn.execute(
                "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (ref_id,)
            ).fetchall()
            if blocking:
                ids = ", ".join(str(r["id"]) for r in blocking)
                raise ApprovalRefused(f"{payee} will not ship while invoice(s) {ids} are unpaid")

        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if cash is None:
            raise ApprovalRefused(f"No cash account named {account}")
        if cash["balance"] < amount:
            raise ApprovalRefused(
                f"Not enough cash: {account} has ${cash['balance']:,.2f}, payment is ${amount:,.2f}"
            )

        new_balance = round(cash["balance"] - amount, 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today, account)
        )
        payment = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, today, approved_by),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        elif kind == "rent":
            next_due = conn.execute("SELECT next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()["next_due"]
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_month(next_due), ref_id))
        conn.execute(
            "UPDATE approvals SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
            (approved_by, datetime.now(timezone.utc).isoformat(timespec="seconds"), approval_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "approval_id": approval_id,
        "payment_id": payment.lastrowid,
        "kind": kind,
        "payee": payee,
        "amount": amount,
        "account": account,
        "balance_before": cash["balance"],
        "balance_after": new_balance,
        "approved_by": approved_by,
        "paid_at": today,
    }


# ---------- Reset ----------


def reset_database() -> None:
    """Copy the untouched original over the working copy (clears approvals and drafts too)."""
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
