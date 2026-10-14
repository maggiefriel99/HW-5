// The Handsome Dan crew: one bulldog per agent, each with its own personality.
import type { AgentName } from "./api";

export interface DanProfile {
  agent: AgentName;
  name: string;
  role: string;
  personality: string;
  accent: string;
  catchphrase: string; // shown while idle
  startLine: string; // said when the Boss hands them a ticket
  doneLine: string; // said when they finish
}

export const DANS: Record<AgentName, DanProfile> = {
  boss: {
    agent: "boss",
    name: "Big Dan",
    role: "Boss",
    personality: "Calm, decisive, a little regal. Hears everyone out, then makes the call.",
    accent: "#f5c542",
    catchphrase: "The buck stops at these paws.",
    startLine: "Alright team, new ticket on the desk.",
    doneLine: "Decision made. Next!",
  },
  inventory: {
    agent: "inventory",
    name: "Stockroom Dan",
    role: "Inventory",
    personality: "Meticulous counter. Trusts nothing he hasn't sniffed twice.",
    accent: "#5ec2f2",
    catchphrase: "Counted twice, sniffed thrice.",
    startLine: "Grabbing my clipboard…",
    doneLine: "Shelves accounted for.",
  },
  accounting: {
    agent: "accounting",
    name: "Pennies Dan",
    role: "Accounting",
    personality: "Frugal worrier. Guards every dollar like a chew toy.",
    accent: "#4fd18b",
    catchphrase: "Every bone is budgeted.",
    startLine: "Sharpening my pencil. Let's see the numbers.",
    doneLine: "Books balance. For now.",
  },
  facilities: {
    agent: "facilities",
    name: "Handy Dan",
    role: "Facilities",
    personality: "Laid-back fixer. Knows every lease, leak, and landlord.",
    accent: "#ff9f43",
    catchphrase: "If it's got walls, it's mine.",
    startLine: "Pulling up the lease, no sweat.",
    doneLine: "Roof's still over our heads.",
  },
  customer_service: {
    agent: "customer_service",
    name: "Sunny Dan",
    role: "Customer Service",
    personality: "Endlessly cheerful. Writes every reply with a wagging tail.",
    accent: "#ff7eb6",
    catchphrase: "Woof! How can I help?",
    startLine: "Ooh, a customer! Drafting something friendly.",
    doneLine: "Draft's on the board. Not sent!",
  },
};

export const DAN_ORDER: AgentName[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

const money = (n: unknown) =>
  typeof n === "number" ? `$${n.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : String(n);

/** A short, readable line for a tool call, built from its arguments. */
export function toolLine(tool: string, args: Record<string, unknown> = {}): string {
  const a = args as Record<string, any>;
  switch (tool) {
    case "list_open_tickets": return "Scanning the board for open tickets";
    case "get_ticket": return `Reading ticket #${a.ticket_id}`;
    case "update_ticket_status": return `Marking ticket #${a.ticket_id} ${String(a.status).replace(/_/g, " ")}`;
    case "check_inventory": return `Checking stock: ${a.sku}${a.size ? ` size ${a.size}` : ""}${a.qty_needed ? ` × ${a.qty_needed}` : ""}`;
    case "list_vendors": return "Looking up vendors and lead times";
    case "draft_purchase_order": return `Drafting a PO: ${a.qty} × ${a.sku} ${a.size ?? ""} from vendor ${a.vendor_id}`;
    case "check_cash": return "Checking the cash accounts";
    case "check_invoices": return `Reviewing ${a.status ?? "all"} invoices`;
    case "prepare_payment": return `Preparing ${a.kind} payment #${a.ref_id} for approval`;
    case "evaluate_bulk_discount": return `Pricing ${a.qty} × ${a.sku} at ${(a.discount_percents ?? []).join("/")}% off`;
    case "check_rent_due": return `Checking rent on lease #${a.lease_id}`;
    case "save_customer_draft": return `Saving a draft reply: "${a.subject}"`;
    default: return `${tool}(${Object.values(a).map(money).join(", ")})`;
  }
}
