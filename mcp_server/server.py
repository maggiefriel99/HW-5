"""Campus Customs MCP server.

Exposes shop tools backed by data/campus_customs_new.db (the working copy).
Every agent on the team gets its tools from this server; agents never open the
database themselves. No tool here moves money: payments are only proposed, and
a human approves them.
"""

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


TICKET_STATUSES = ("open", "in_progress", "waiting_on_approval", "resolved")


def _today(conn: sqlite3.Connection) -> str:
    """The shop's "today" comes from desk.date_today, not the system clock."""
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date, description FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Tickets ----------


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the board with its status, oldest first.

    Reads tickets and desk.
    """
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at").fetchall()
    return {"date_today": today, "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket on the board that is not resolved, oldest first.

    Reads tickets and desk.
    """
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at"
        ).fetchall()
    return {"date_today": today, "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with all of its fields. Reads tickets."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {"error": f"No ticket with id {ticket_id}"}
    return dict(row)


@mcp.tool
def update_ticket_status(ticket_id: int, status: str) -> dict:
    """Move a ticket to a new status on the board.

    Writes tickets.status. Allowed statuses: open, in_progress,
    waiting_on_approval, resolved.
    """
    if status not in TICKET_STATUSES:
        return {"error": f"status must be one of {', '.join(TICKET_STATUSES)}"}
    with _connect() as conn:
        row = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"error": f"No ticket with id {ticket_id}"}
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    return {"ticket_id": ticket_id, "old_status": row["status"], "new_status": status}


# ---------- Facilities ----------


@mcp.tool
def check_rent_due(lease_id: int) -> dict:
    """Look up how much rent is owed on a lease and when it is due.

    Reads leases, desk, and cash_accounts. Returns the rent amount, due date,
    days until due (based on desk.date_today), and whether checking has enough
    cash to cover it. This tool does not make a payment; paying requires
    human approval.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"error": f"No lease with id {lease_id}"}

        today = _today(conn)
        balance = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()["balance"]

    days_until_due = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
    return {
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "date_today": today,
        "days_until_due": days_until_due,
        "overdue": days_until_due < 0,
        "checking_balance": balance,
        "enough_cash": balance >= lease["monthly_rent"],
    }


# ---------- Inventory and vendors ----------


@mcp.tool
def check_inventory(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict:
    """Check units on hand for a SKU, optionally for one size.

    Reads inventory. If size and qty_needed are given, also reports whether
    stock covers the request and how many units are short.
    """
    with _connect() as conn:
        if size is None:
            rows = conn.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
                (sku,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
                (sku, size),
            ).fetchall()

    if not rows:
        return {"error": f"No inventory found for sku {sku}" + (f" size {size}" if size else "")}

    result = {"sku": sku, "items": [dict(r) for r in rows]}
    if size is not None and qty_needed is not None:
        on_hand = rows[0]["qty"]
        result["qty_needed"] = qty_needed
        result["can_fill"] = on_hand >= qty_needed
        result["shortfall"] = max(qty_needed - on_hand, 0)
    return result


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its lead time and whether it can ship right now.

    Reads vendors, invoices, and desk. A vendor with an open (unpaid) invoice
    will not ship new product, so can_ship is false until that invoice is paid.
    earliest_arrival is desk.date_today plus lead_days.
    """
    with _connect() as conn:
        today = _today(conn)
        vendors = conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()
        result = []
        for v in vendors:
            open_inv = _open_invoices(conn, v["id"])
            result.append({
                **dict(v),
                "open_invoices": open_inv,
                "can_ship": not open_inv,
                "earliest_arrival": (date.fromisoformat(today) + timedelta(days=v["lead_days"])).isoformat(),
            })
    return {"date_today": today, "vendors": result}


@mcp.tool
def draft_purchase_order(vendor_id: int, sku: str, size: str, qty: int) -> dict:
    """Draft (do not place) a restock order so Accounting and a human can review it.

    Reads vendors, invoices, pricing, and desk. Returns the cost at unit_cost,
    the earliest arrival date, and whether the vendor is blocked by an open
    invoice. Nothing is saved and nothing is sent to the vendor.
    """
    if qty <= 0:
        return {"error": "qty must be greater than 0"}
    with _connect() as conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"error": f"No vendor with id {vendor_id}"}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"error": f"No pricing found for sku {sku}"}
        today = _today(conn)
        open_inv = _open_invoices(conn, vendor_id)

    blocked = bool(open_inv)
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "vendor_specialty": vendor["specialty"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": price["unit_cost"],
        "total_cost": round(price["unit_cost"] * qty, 2),
        "lead_days": vendor["lead_days"],
        "earliest_arrival": (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat(),
        "blocked": blocked,
        "blocked_reason": (
            f"Vendor has open unpaid invoice(s) {[i['id'] for i in open_inv]}; it will not ship until they are paid."
            if blocked else None
        ),
        "status": "draft only, not placed",
    }


# ---------- Accounting ----------


@mcp.tool
def check_cash() -> dict:
    """Current balance of every cash account. Reads cash_accounts."""
    with _connect() as conn:
        rows = conn.execute("SELECT name, balance, date FROM cash_accounts").fetchall()
    return {"accounts": [dict(r) for r in rows]}


@mcp.tool
def check_invoices(status: str | None = None, vendor_id: int | None = None) -> dict:
    """List vendor invoices, optionally filtered by status or vendor.

    Reads invoices, vendors, and desk. Each invoice shows days until due
    (negative means overdue) based on desk.date_today.
    """
    query = (
        "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE 1=1"
    )
    params: list = []
    if status is not None:
        query += " AND i.status = ?"
        params.append(status)
    if vendor_id is not None:
        query += " AND i.vendor_id = ?"
        params.append(vendor_id)
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute(query + " ORDER BY i.due_date", params).fetchall()
    invoices = []
    for r in rows:
        days = _days_between(today, r["due_date"])
        invoices.append({**dict(r), "days_until_due": days, "overdue": r["status"] == "open" and days < 0})
    return {"date_today": today, "invoices": invoices}


@mcp.tool
def prepare_payment(kind: str, ref_id: int, account: str = "checking") -> dict:
    """Prepare (do not make) a payment so a human can approve it.

    kind is "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
    Reads invoices or leases, cash_accounts, and payments. The amount always
    comes from the database. Returns whether the account can cover it without
    going negative and whether it was already paid. No money moves and
    nothing is written.
    """
    with _connect() as conn:
        if kind == "invoice":
            row = conn.execute(
                "SELECT i.amount, i.status, i.due_date, v.name AS payee FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                return {"error": f"No invoice with id {ref_id}"}
            amount, payee, due = row["amount"], row["payee"], row["due_date"]
            already_paid = row["status"] != "open"
        elif kind == "rent":
            row = conn.execute(
                "SELECT monthly_rent, landlord, next_due FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if row is None:
                return {"error": f"No lease with id {ref_id}"}
            amount, payee, due = row["monthly_rent"], row["landlord"], row["next_due"]
            already_paid = conn.execute(
                "SELECT 1 FROM payments WHERE kind = 'rent' AND ref_id = ? AND paid_at >= ?",
                (ref_id, _today(conn)),
            ).fetchone() is not None
        else:
            return {"error": 'kind must be "invoice" or "rent"'}

        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if cash is None:
            return {"error": f"No cash account named {account}"}

    balance_after = round(cash["balance"] - amount, 2)
    return {
        "kind": kind,
        "ref_id": ref_id,
        "payee": payee,
        "amount": amount,
        "due_date": due,
        "account": account,
        "balance_before": cash["balance"],
        "balance_after": balance_after,
        "enough_cash": balance_after >= 0,
        "already_paid": already_paid,
        "status": "needs human approval, not paid",
    }


@mcp.tool
def evaluate_bulk_discount(sku: str, qty: int, discount_percents: list[float]) -> dict:
    """Compare discount options for a bulk order of one SKU.

    Reads pricing. For each discount percent given, returns the unit price,
    order total, profit per unit, total profit, and margin, and flags any
    option that would sell below unit_cost. The shop has no set discount
    policy in the database, so the caller chooses which percents to compare.
    """
    with _connect() as conn:
        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if price is None:
        return {"error": f"No pricing found for sku {sku}"}

    unit_cost = price["unit_cost"]
    list_price = price["list_price"]
    options = []
    for pct in discount_percents:
        unit_price = round(list_price * (1 - pct / 100), 2)
        profit_per_unit = round(unit_price - unit_cost, 2)
        options.append({
            "discount_percent": pct,
            "unit_price": unit_price,
            "order_total": round(unit_price * qty, 2),
            "profit_per_unit": profit_per_unit,
            "total_profit": round(profit_per_unit * qty, 2),
            "margin_percent": round(profit_per_unit / unit_price * 100, 1) if unit_price else None,
            "below_cost": unit_price < unit_cost,
        })

    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "options": options,
    }


# ---------- Customer service ----------


@mcp.tool
def save_customer_draft(ticket_id: int, subject: str, body: str, written_by: str) -> dict:
    """Save a reply to a customer as a draft on the board. It is never sent.

    Reads tickets (the recipient is always the ticket's requester) and writes
    drafts. The drafts table is created in the working copy on first use.
    """
    with _connect() as conn:
        ticket = conn.execute("SELECT requester FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"error": f"No ticket with id {ticket_id}"}
        conn.execute(
            """CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY,
                ticket_id INTEGER NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                written_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )"""
        )
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, written_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, ticket["requester"], subject, body, written_by,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    return {
        "draft_id": cur.lastrowid,
        "ticket_id": ticket_id,
        "recipient": ticket["requester"],
        "status": "draft saved on the board, not sent",
    }


if __name__ == "__main__":
    mcp.run()
