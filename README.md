# Campus Customs Multi-Agent Operations (HW 5)

A team of five AI agents runs the Campus Customs shop's ticket board: **Boss, Inventory, Accounting, Facilities, and Customer Service**. Every agent uses `gpt-6-luna` through Portkey. The project has three pieces that talk to each other:

- **MCP server** (`mcp_server/`): the only way agents read or change the shop database.
- **FastAPI backend** (`backend/`): runs the agent team and holds the human-approval route, which is the only code that moves cash.
- **React dashboard** (`frontend/`): the "Dan Ops Board," where a person watches the agents work and approves payments.

How the system works, its tools and its safety rules are documented in [`output/harness.md`](output/harness.md).

```
hw5/
├── AI_prompts.md            prompts given to the vibe coder, per problem
├── requirements.txt         Python packages
├── .env.example             copy to .env and add your Portkey key
├── .gitignore
├── .mcp.json                MCP server config (used by Claude Code and the backend)
├── README.md
├── data/
│   ├── campus_customs.db       original shop database (never edited)
│   └── campus_customs_new.db   working copy the system reads and writes
├── mcp_server/
│   ├── server.py            FastMCP server with the shop tools
│   └── README.md
├── frontend/                React + Vite + TypeScript board
├── backend/
│   ├── main.py              FastAPI routes
│   ├── models.py            data types
│   ├── agents.py            the agent team, delegation and safety limits
│   ├── approvals.py         human approvals (pays) and database reset
│   ├── audit.py             append-only audit trail
│   └── prompts/             one prompt per agent
│       ├── boss.md
│       ├── inventory.md
│       ├── accounting.md
│       ├── facilities.md
│       └── customer_service.md
└── output/
    ├── harness.md            how the system works (for a manager)
    ├── mcp_smoke.json        MCP tool tests
    ├── desk_tickets.html     plan vs. actual for each ticket, cash, reflection
    ├── design.md             dashboard design choices
    ├── resolved_tickets.json results of the 3-ticket run
    ├── resolved_board.html   screenshots of the board per ticket
    ├── screenshots/          images used by resolved_board.html
    ├── audit_trail.json      every agent run (append-only)
    └── github_url.txt
```

---

## 1. Setup (once)

You need **Python 3.12+**, **Node.js 20+**, and a **Portkey API key** with access to `gpt-6-luna`.

```bash
git clone https://github.com/maggiefriel99/HW-5.git
cd HW-5

# Python environment (the .venv name matters: .mcp.json points at .venv/bin/python)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Your Portkey key (never commit .env)
cp .env.example .env
# then open .env and set PORTKEY_API_KEY=...

# Frontend packages
cd frontend && npm install && cd ..
```

## 2. Copy the original database to the working copy (clean run)

`data/campus_customs.db` is the original and is never edited. Everything runs against `data/campus_customs_new.db`. To start from the original values, copy the original over the working copy from the project root:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

The working copy in this repo holds the results of the graded 3-ticket run (checking ends at $152.00), so run this first if you want a fresh start.

## 3. Start the MCP server

You don't need a separate terminal. The backend starts the MCP server for you, as a child process launched from `.mcp.json`, and keeps it running while the API is up.

- **Claude Code:** open the project folder. It reads `.mcp.json` and offers to connect the `campus-customs` server. Approve it, and the tools appear as `mcp__campus-customs__<tool>`.
- **To run it by hand** (for example, to check it starts):
  ```bash
  .venv/bin/python mcp_server/server.py
  ```
  It speaks MCP over stdin/stdout and waits for a client. Press Ctrl+C to stop it.

## 4. Start the FastAPI backend

In a new terminal, from the project root:

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

The API is at `http://localhost:8000`. To check it's up, open `http://localhost:8000/api/cash`, which should show the checking balance. Interactive API docs are at `http://localhost:8000/docs`.

## 5. Start the React board

In another terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The board talks to the backend at `http://localhost:8000`, which allows this origin.

## 6. Full 3-ticket run

1. **Reset the database first.** Click **↺ Fresh run (reset DB)** on the board, or run either of these:
   ```bash
   curl -X POST http://localhost:8000/api/reset
   # or, from the project root:
   cp data/campus_customs.db data/campus_customs_new.db
   ```
   Checking should read **$3,400.00**. The reset doesn't touch the audit trail.
2. Click ticket **#101** and press **Start the agent team**. Watch the Dans work on the left. When the run finishes, the ticket shows **resolved** and a summary per agent appears in the center.
3. Do the same for **#102** and **#103**.
4. On the right, type your name under **Approving as** and approve what you want to pay. Cash only goes down when you approve, and the backend refuses anything that would make the balance negative or that a blocked vendor can't ship.

**Command-line alternative** (no board, no approvals), from the project root:
```bash
.venv/bin/python backend/agents.py --all      # or: backend/agents.py 101 102
```

Every agent run is appended to `output/audit_trail.json`.

---

## Rules this system follows

- Every agent uses only `gpt-6-luna` through Portkey.
- Shop facts come only from the database, through the MCP server.
- Agents can only *prepare* payments and purchase orders. A person approves each one, and only then does cash change.
- The pay step refuses if cash would go negative. Cash only goes out; there is no revenue.
- "Today" is `desk.date_today`. Vendor lead times come from `vendors`. A vendor with an open invoice won't ship.
- Nothing is emailed. Customer replies are saved as drafts on the board.
