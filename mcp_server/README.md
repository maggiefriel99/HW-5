# Campus Customs MCP Server

## Purpose
This server gives the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service) all of its shop tools. Agents only see the shop through this server and never open the database themselves. It is built with FastMCP (`server.py`), and Claude Code and the agents connect to it through `.mcp.json` at the project root.

No tool moves money. Payments and purchase orders are only prepared for a human to approve, and customer replies are saved as drafts that are never sent.

## Database
- `data/campus_customs_new.db` is the working copy the server reads and updates.
- `data/campus_customs.db` is the original and is never touched. Copy it over the working copy to reset.

## Tools
| Tool | Tables | Does |
|---|---|---|
| `list_tickets()` | `tickets`, `desk` | Every ticket with its status (used by the board) |
| `list_open_tickets()` | `tickets`, `desk` | Every ticket that isn't resolved, plus today's date |
| `get_ticket(ticket_id)` | `tickets` | All fields of one ticket |
| `update_ticket_status(ticket_id, status)` | `tickets` (write) | Sets status to `open`, `in_progress`, `waiting_on_approval` or `resolved` |
| `check_inventory(sku, size, qty_needed)` | `inventory` | Units on hand and any shortfall |
| `list_vendors()` | `vendors`, `invoices`, `desk` | Lead times, open invoices, whether each vendor can ship, earliest arrival |
| `draft_purchase_order(vendor_id, sku, size, qty)` | `vendors`, `invoices`, `pricing`, `desk` | Restock cost, arrival date, and whether an unpaid invoice blocks it. Not placed |
| `check_cash()` | `cash_accounts` | Balance of each account |
| `check_invoices(status, vendor_id)` | `invoices`, `vendors`, `desk` | Invoices with days until due and an overdue flag |
| `prepare_payment(kind, ref_id, account)` | `invoices` or `leases`, `cash_accounts`, `payments` | Rent or invoice payment checked against cash. Not paid |
| `evaluate_bulk_discount(sku, qty, discount_percents)` | `pricing` | Price, total, profit and margin per discount, with below-cost options flagged |
| `check_rent_due(lease_id)` | `leases`, `desk`, `cash_accounts` | Rent amount, due date, days until due, whether cash covers it |
| `save_customer_draft(ticket_id, subject, body, written_by)` | `tickets`, `drafts` (write) | Saves a reply to the ticket's requester as a draft. Not sent |
