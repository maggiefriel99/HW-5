import type { AgentName, LiveEvent } from "../api";
import { DANS, DAN_ORDER, toolLine } from "../dans";
import { Dan, type DanMood } from "./Dan";
import { PIZZA_SLICES, Pizza } from "./Pizza";

interface DanState {
  mood: DanMood;
  slices: number;
  line: string;
}

/** Turn the live events of one run into what each Dan is doing right now. */
export function danStates(events: LiveEvent[]): Record<AgentName, DanState> {
  const states = Object.fromEntries(
    DAN_ORDER.map((a) => [a, { mood: "idle", slices: 0, line: DANS[a].catchphrase }]),
  ) as Record<AgentName, DanState>;
  const actions: Record<string, number> = {};
  const waitingOn: Partial<Record<AgentName, AgentName>> = {};

  for (const e of events) {
    const s = states[e.agent];
    actions[e.agent] = (actions[e.agent] ?? 0) + 1;
    const progress = Math.min(PIZZA_SLICES - 1, 1 + actions[e.agent]);
    switch (e.kind) {
      case "started":
        s.mood = "working";
        s.slices = Math.max(s.slices === PIZZA_SLICES ? PIZZA_SLICES - 1 : s.slices, progress);
        s.line = e.invoked_by === "runner"
          ? `${DANS[e.agent].startLine} (#${e.ticket_id})`
          : `${DANS[e.agent].startLine} ${DANS[e.invoked_by as AgentName]?.name ?? e.invoked_by} needs me.`;
        break;
      case "tool":
        s.mood = "working";
        s.slices = progress;
        s.line = toolLine(e.tool ?? "", e.args);
        break;
      case "delegated":
        s.mood = "waiting";
        s.slices = progress;
        s.line = `Asking ${DANS[e.to!].name}: "${e.text}"`;
        waitingOn[e.agent] = e.to;
        break;
      case "blocked":
        s.line = `Safety rule stopped a hand-off: ${e.text}`;
        break;
      case "finished":
        s.mood = "done";
        s.slices = PIZZA_SLICES;
        s.line = e.text || DANS[e.agent].doneLine;
        for (const caller of DAN_ORDER) {
          if (waitingOn[caller] === e.agent) {
            delete waitingOn[caller];
            states[caller].mood = "working";
            states[caller].line = `Reading ${DANS[e.agent].name}'s report…`;
          }
        }
        break;
      case "aborted":
        s.mood = "aborted";
        s.line = e.text;
        break;
    }
  }
  return states;
}

function eventIcon(kind: LiveEvent["kind"]) {
  return { started: "▶", tool: "🔧", delegated: "📣", blocked: "⛔", finished: "✅", aborted: "🛑" }[kind];
}

export function AgentColumn({ runEvents, feed, running }: { runEvents: LiveEvent[]; feed: LiveEvent[]; running: boolean }) {
  const states = danStates(runEvents);
  return (
    <aside className="column agents-column">
      <h2 className="column-title">
        The Dan Crew {running && <span className="live-dot">LIVE</span>}
      </h2>

      <div className="dan-grid">
        {DAN_ORDER.map((agent) => {
          const s = states[agent];
          const dan = DANS[agent];
          return (
            <div key={agent} className={`dan-card mood-${s.mood}`} style={{ ["--accent" as any]: dan.accent }}>
              <div className="dan-body">
                <div className="dan-figure">
                  <Pizza slices={s.slices} burnt={s.mood === "aborted"} size={46} />
                  <Dan agent={agent} mood={s.mood} size={76} />
                </div>
                <div className="dan-info">
                  <div className="dan-name">{dan.name}</div>
                  <div className="dan-role">{dan.role}</div>
                  <div key={s.line} className="speech">{s.line}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <h3 className="feed-title">Live activity</h3>
      <ol className="feed">
        {feed.length === 0 && <li className="feed-empty">Pick a ticket and start the team. Every move shows up here.</li>}
        {[...feed].reverse().map((e) => (
          <li key={e.index} className={`feed-item kind-${e.kind}`} style={{ ["--accent" as any]: DANS[e.agent].accent }}>
            <span className="feed-icon">{eventIcon(e.kind)}</span>
            <div>
              <div className="feed-head">
                <strong>{DANS[e.agent].name}</strong>
                {e.kind === "delegated" && e.to && <> → <strong>{DANS[e.to].name}</strong></>}
                <span className="feed-ticket">#{e.ticket_id}</span>
              </div>
              <div className="feed-text">
                {e.kind === "tool" ? (
                  <>
                    <code>{e.tool}</code> {toolLine(e.tool ?? "", e.args)}
                    <div className="feed-result">{e.text}</div>
                  </>
                ) : (
                  e.text
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
