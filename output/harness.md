# Campus Customs Multi-Agent Operations: Harness

**For:** shop managers and reviewers. This explains how the system works, what it can and can't do, and the rules that keep it safe.

---

## How it works in one minute

1. A ticket lands on the board: a customer order, rent notice, discount request, and so on.
2. A manager opens the **Dan Ops Board** (React dashboard), picks the ticket and clicks **Start the agent team**.
3. The **Boss** agent reads the ticket and hands pieces to specialists: **Inventory**, **Accounting**, **Facilities** and **Customer Service**. Any agent can ask any other for help.
4. Agents learn about the shop **only through the MCP server**, a fixed set of tools over the shop database. They never touch the database directly.
5. Agents can **prepare** payments and purchase orders, but **cannot pay anything**. Customer replies are saved as **drafts** and never sent.
6. When the run finishes, the ticket is marked **resolved**, and anything that costs money appears on the board's **approval panel**.
7. A **person** clicks Approve. Only then does cash leave checking. The approval is refused if there isn't enough cash or the vendor is blocked.
8. Every agent step is recorded in `output/audit_trail.json`.

```
 Manager ──► React board (:5173) ──► FastAPI backend (:8000) ──► Agent team (gpt-6-luna via Portkey)
                                         │                              │
                                         │ approve route (human only)   │ MCP tools only
                                         ▼                              ▼
                                   data/campus_customs_new.db ◄── MCP server (mcp_server/server.py)
```

---

## 1. Database tables

**Working copy:** `data/campus_customs_new.db`. The MCP server and backend read and write this file.
**Original:** `data/campus_customs.db`. Never edited. The board's **Fresh run** button (`POST /api/reset`) copies it over the working copy.
**Shop rules from the data:** "today" is `desk.date_today` (2026-08-31). Vendor lead times come from `vendors.lead_days`. A vendor with an open invoice won't ship. Cash only goes out; there is no revenue.

### `desk`
| Field | Why it matters |
|---|---|
| `date_today` | The shop's "today," used to decide what is overdue or coming due. |
| `notes` | Free-text notes for the shop. |

### `tickets`
| Field | Why it matters |
|---|---|
| `id` | Unique ticket number, used to track and update each request. |
| `type` | Kind of request (customer order, rent notice, price override), which tells the Boss which agent should handle it. |
| `requester` | Who asked, so Customer Service knows who a draft is for. |
| `subject` | Short title shown on the board. |
| `sku` | Product involved, which links the ticket to inventory and pricing. |
| `size` | Product size, needed to check stock for the exact item. |
| `qty` | Number of units requested, compared against stock to find shortfalls. |
| `lease_id` | Links rent tickets to the lease that Facilities handles. |
| `invoice_id` | Links the ticket to a vendor invoice that may block a restock. |
| `status` | `open`, `in_progress` or `resolved`, so agents and the board know what still needs work. |
| `notes` | The requester's details in plain language, which agents read to understand the request. |
| `created_at` | When the ticket arrived, used for ordering and urgency. |

### `inventory`
| Field | Why it matters |
|---|---|
| `sku` | Product ID, which joins to pricing and tickets. |
| `name` | Readable product name for drafts and the dashboard. |
| `size` | Stock is tracked per size, so checks must match SKU and size. |
| `qty` | Units on hand, used to decide whether an order can be filled or needs a restock. |
| `location` | Where the item sits in the shop, for picking orders. |

### `pricing`
| Field | Why it matters |
|---|---|
| `sku` | Links prices to inventory items. |
| `unit_cost` | What the shop pays per unit, used to compute margin and restock cost. Discounts can never go below it. |
| `list_price` | Normal selling price, the starting point for any discount. |

### `vendors`
| Field | Why it matters |
|---|---|
| `id` | Vendor ID, which joins to invoices. |
| `name` | Vendor name for purchase orders and drafts. |
| `specialty` | What the vendor supplies, so Inventory picks the right restock source. |
| `lead_days` | Days to deliver, used to promise realistic restock dates. |

### `leases`
| Field | Why it matters |
|---|---|
| `id` | Lease ID, which tickets reference. |
| `space_name` | Which shop space the lease covers. |
| `landlord` | Who gets paid rent. |
| `monthly_rent` | Amount owed each month, checked against available cash. |
| `next_due` | Next rent due date, compared to `desk.date_today` for urgency. It moves ahead one month when rent is paid. |
| `notes` | Extra lease details. |

### `cash_accounts`
| Field | Why it matters |
|---|---|
| `name` | Which account money comes from (`checking`). |
| `balance` | Cash available. A payment must never push it below zero. |
| `date` | When the balance last changed. |

### `payments`
| Field | Why it matters |
|---|---|
| `id` | Unique payment record. |
| `kind` | What was paid: `invoice`, `rent` or `purchase_order`. |
| `ref_id` | ID of the invoice or lease paid, or the vendor for a purchase order. |
| `amount` | How much cash left the account. |
| `account` | Which cash account paid it. |
| `paid_at` | Shop date of the payment. |
| `approved_by` | The person who approved it. Every payment needs a human. |

### `invoices`
| Field | Why it matters |
|---|---|
| `id` | Invoice ID, which tickets and payments reference. |
| `vendor_id` | Which vendor is owed. An open invoice stops that vendor from shipping. |
| `amount` | Amount owed, checked against cash before paying. |
| `due_date` | Compared to `desk.date_today` to find overdue bills. |
| `status` | `open` or `paid`. Open invoices block new shipments from that vendor. |
| `description` | What the invoice was for. |

### Tables the system adds to the working copy
| Table | Created by | Holds |
|---|---|---|
| `drafts` | MCP tool `save_customer_draft` | Customer replies (recipient, subject, body, author). Never sent. |
| `approvals` | Backend, when a run finishes | Payments and purchase orders waiting for a person, with amount, payee, status and who approved them. |

---

## 2. The MCP rule

**Rule: every shop fact comes from `data/campus_customs_new.db` through the MCP server. There is no second tools layer.**
- The server is `mcp_server/server.py` (FastMCP, named `campus-customs`). It is launched from `.mcp.json` at the project root, which both Claude Code and the agent team use.
- Agents never open the database. Each agent only sees the MCP tools its role needs.
- The backend's read routes (tickets, cash) also go through MCP.
- **No MCP tool moves money.** Paying lives only in the backend's approve route (`backend/approvals.py`), which only a person can trigger. So no agent can reach it, even by mistake.

### MCP tool catalog
| Tool | Tables used | Reads / writes | Used by |
|---|---|---|---|
| `list_tickets()` | `tickets`, `desk` | read | Board (`GET /api/tickets`) |
| `list_open_tickets()` | `tickets`, `desk` | read | Boss |
| `get_ticket(ticket_id)` | `tickets` | read | all agents |
| `update_ticket_status(ticket_id, status)` | `tickets` | **writes** `status` | Boss, Board |
| `check_inventory(sku, size, qty_needed)` | `inventory` | read | Inventory, Customer Service |
| `list_vendors()` | `vendors`, `invoices`, `desk` | read | Inventory |
| `draft_purchase_order(vendor_id, sku, size, qty)` | `vendors`, `invoices`, `pricing`, `desk` | read (draft only, not placed) | Inventory, Accounting |
| `check_cash()` | `cash_accounts` | read | Boss, Accounting, Board |
| `check_invoices(status, vendor_id)` | `invoices`, `vendors`, `desk` | read | Accounting |
| `prepare_payment(kind, ref_id, account)` | `invoices` or `leases`, `cash_accounts`, `payments` | read (nothing is paid) | Accounting |
| `evaluate_bulk_discount(sku, qty, discount_percents)` | `pricing` | read | Accounting |
| `check_rent_due(lease_id)` | `leases`, `desk`, `cash_accounts` | read | Facilities |
| `save_customer_draft(ticket_id, subject, body, written_by)` | `tickets`, `drafts` | **writes** `drafts` | Customer Service |

### Why the first three tools fit their tickets (Problem 3)
- **`check_rent_due`, ticket 102:** gets the real amount and due date from `leases`, counts the days left from `desk.date_today`, and checks that `checking` can cover it. That way the landlord's notice is confirmed against the database before anyone is asked to pay.
- **`check_inventory`, tickets 101 and 103:** stock is tracked per SKU and size. This returns exact units on hand, whether the request can be filled, and the shortfall, which Inventory needs before deciding on a restock.
- **`evaluate_bulk_discount`, ticket 103:** uses `unit_cost` and `list_price` to show the price, total, profit and margin for each proposed discount, and flags anything below cost. The database has no discount policy, so the tool doesn't invent one.

---

## 3. Agents

**Model:** every agent uses **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`). No other model appears in the code or runs. Reasoning effort is set to `none`, because the deployment rejects tool calls otherwise, and that also keeps token use down.
**Code:** `backend/agents.py` (team, delegation, limits), `backend/prompts/<agent>.md` (one prompt per agent), `backend/models.py` (data types).
**Collaboration:** every agent has `ask_agent(agent, request)` and can hand work to any teammate (full connectivity). The Boss takes every ticket first. Specialists send escalations back to the Boss in their report (`needs_boss_decision`) instead of calling back up the chain.

| Agent (board name) | Responsibilities | MCP tools |
|---|---|---|
| **Boss** (Big Dan) | Reads each ticket, marks it in progress, assigns work, and makes the judgment calls: which bills come first when cash is short, and how much discount to give. Collects everything that needs approval. | `list_open_tickets`, `get_ticket`, `update_ticket_status`, `check_cash` |
| **Inventory** (Stockroom Dan) | Checks stock by SKU and size, finds shortfalls, picks a vendor by specialty, drafts restock orders, flags vendors blocked by unpaid invoices, and sends restock needs to the Boss. | `get_ticket`, `check_inventory`, `list_vendors`, `draft_purchase_order` |
| **Accounting** (Pennies Dan) | Checks cash and invoices, adds up obligations against cash, evaluates discounts and margins, and prepares payments and purchase orders for approval. | `get_ticket`, `check_cash`, `check_invoices`, `prepare_payment`, `evaluate_bulk_discount`, `draft_purchase_order` |
| **Facilities** (Handy Dan) | Checks the lease against the landlord's notice, tracks rent due dates, and asks Accounting to prepare rent. | `get_ticket`, `check_rent_due` |
| **Customer Service** (Sunny Dan) | Writes replies to requesters as drafts on the board. Never sends them, and never shares costs, cash or invoices. | `get_ticket`, `check_inventory`, `save_customer_draft` |

---

## 4. API routes

FastAPI app in `backend/main.py` at `http://localhost:8000`. Start it from `backend/` with `uvicorn main:app --reload --port 8000`. The board's origin (`http://localhost:5173`) is allowed through CORS.

- `GET /api/tickets`: returns every ticket and whether it is open, in progress or resolved.
- `POST /api/tickets/{ticket_id}/run`: runs the agent team on one ticket, marks it resolved when the run finishes (or back to open if stopped), and queues any payments or purchase orders for approval. Only one run at a time.
- `GET /api/events?since=N&live_since=M&ticket_id=ID`: returns the live step-by-step feed (started, tool called, delegated, finished) plus finished audit entries, so the board can show the agents working.
- `GET /api/approvals`: returns payments and purchase orders waiting for a person, plus ones already approved.
- `POST /api/approvals/{approval_id}/approve`: a person approves (their name is required). The backend re-reads the amount from the database, takes the cash out of checking, writes the payment, and marks the invoice paid or moves rent ahead a month. It refuses if cash is short, the vendor is blocked, or the item was already paid.
- `GET /api/cash`: returns the current checking balance from `cash_accounts`.
- `POST /api/reset`: copies the original database over the working copy for a fresh run. The audit trail is kept.

---

## 5. Dashboard

React + Vite + TypeScript in `frontend/`. Start it with `npm run dev` inside `frontend/`, then open `http://localhost:5173`. Crisp white on navy, three columns:

- **Left, the Dan Crew:** the five agents as Handsome Dans with their own personalities. A pizza above each head fills slice by slice (out of 8) as that agent works. Speech bubbles and a live feed show each tool call and hand-off as it happens.
- **Center, the Ticket Desk:** every ticket with its status, the selected ticket's details, and **Start the agent team**. After a run it shows the Boss's decision and a card per agent: what it said, the tools it used, who it handed off to, and its tokens.
- **Right, the money:** a large checking balance that counts down when a payment is approved. It also shows the total waiting for approval, the balance if everything were approved (red if negative), and the total paid out. Below that is the approval queue, with the approver's name field and an **Approve** button per item.
- **Header:** a **Fresh run** button that resets the database (with a confirmation).

Design reasoning is in `output/design.md`.

---

## 6. Audit trail

Every agent run appends one entry to `output/audit_trail.json`, including delegated, blocked and failed runs. Earlier entries are never removed, and a reset doesn't touch the file. Each entry records:
- `ticket_id` and `run_id` (all agents on one ticket run share a `run_id`)
- `agent`, `model`, and `invoked_by` (`runner` for the Boss, otherwise the agent that delegated)
- `delegated_to`: the teammates it called
- `tools_called`: each tool and its arguments
- `tokens`: its own input, output and total tokens and model calls. `ticket_tokens_total` on the Boss entry is the whole ticket.
- `blocked_calls`: hand-offs a safety rule stopped, and why
- `aborted` and `abort_reason`: set if the run was stopped by a limit or an error
- `outcome`: what the agent concluded

---

## 7. Safety rules

### Built into this system
- **Humans approve all money.** Agents only prepare payments and purchase orders. Cash changes only through the approve route, with a named approver.
- **No negative balances.** The approve route refuses any payment larger than the balance. All checks and writes happen in one database transaction.
- **Amounts come from the database, never the model.** At approval time the backend re-reads the invoice amount, the rent, or `unit_cost × qty`.
- **Vendor block.** A purchase order can't be approved while that vendor has an open invoice.
- **No double payments.** Already-paid invoices and already-approved items are refused, and duplicate proposals aren't queued twice.
- **Nothing is sent.** Customer replies are drafts, the recipient is always the ticket's requester, and there are no email or vendor tools.
- **Least-privilege tools.** Each agent sees only its role's MCP tools, and no MCP tool can pay.
- **Token budget per ticket.** 60,000 tokens and 30 model calls, shared by all agents on the ticket. Going over stops the ticket and logs the reason.
- **Delegation limits.** No delegating to yourself, no calling back to an agent already waiting on you, at most 3 agents deep, and at most 6 hand-offs per ticket. Blocked hand-offs are logged.
- **One run at a time,** so two runs can't plan around the same cash.
- **Only one model:** `gpt-6-luna` through Portkey.

### What a real business would add
- **Token and cost control:** monthly spend caps and alerts per agent and per ticket. Cache repeated lookups. Send simple tickets straight to one specialist. Shorten long histories, and stop a ticket after repeated failures.
- **Real money:** two-person approval above a dollar limit. Payments only to vendors and landlords already on file, never to new bank details from a ticket or email. Daily bank reconciliation. Reserve cash that agents can never spend. A tamper-proof, signed audit log.
- **Real customers:** a person reviews drafts before they're sent. Strip personal data from prompts and logs. Filter content and tone. Treat ticket text as untrusted, since customers could try to instruct the agents. Give customers a clear way to reach a human.
- **Operations:** logins with roles so only approvers can approve. Rate limits. Alerts on aborted runs. A sandbox database for testing, and backups.

---

## 8. Results from the test run (Problem 9)

The database was reset, then tickets 101, 102 and 103 were each run once on the agent team. All three finished **resolved**. Details are in `output/resolved_tickets.json` and `output/desk_tickets.html`.

| Ticket | Outcome | Tokens |
|---|---|---|
| 101: tee size S | Out of stock and the vendor was blocked by overdue invoice 501. Proposed paying the $840 invoice and a $8 restock. Draft reply saved. | 26,251 |
| 102: rent | Notice matches lease 1, $2,400 due 2026-09-02. Rent prepared for approval. | 12,486 |
| 103: 20 hoodies | 20% off ($46.40 each, $928). 8 in stock, and a 12-hoodie restock ($264) was proposed. Draft reply saved. | 35,488 |

**Cash:** $3,400.00 start, then −$840.00 (invoice 501), −$8.00 (tee restock) and −$2,400.00 (rent), for an **$152.00** end, matching `cash_accounts`. The $264 hoodie restock stays pending because only $152 is left. All payments were approved by Maggie Friel.

**Safety in action:** on ticket 101 the Boss tried to delegate to itself, and the rule blocked and logged it. The first attempt at ticket 101 failed on a model setting (reasoning effort) and is logged as aborted. After the fix, the database was reset again and all three tickets were run.
