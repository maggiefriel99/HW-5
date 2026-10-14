import type { AgentName } from "../api";
import { DANS } from "../dans";

export type DanMood = "idle" | "working" | "waiting" | "done" | "aborted";

/** Handsome Dan, drawn in SVG, dressed for his job. */
export function Dan({ agent, mood, size = 110 }: { agent: AgentName; mood: DanMood; size?: number }) {
  const accent = DANS[agent].accent;
  const worried = agent === "accounting" || mood === "aborted";
  const stern = agent === "boss";
  return (
    <svg
      className={`dan dan-${mood}`}
      viewBox="0 0 120 132"
      width={size}
      height={size * 1.1}
      role="img"
      aria-label={`${DANS[agent].name}, ${mood}`}
    >
      {/* Sweater with the Y */}
      <path d="M22 132 Q22 100 60 98 Q98 100 98 132 Z" fill={accent} stroke="#0b1f3a" strokeWidth="2" />
      <path d="M50 108 L60 120 L70 108 M60 120 L60 131" stroke="#fff" strokeWidth="5" fill="none" strokeLinecap="round" />

      {/* Ears */}
      <path d="M22 44 Q14 26 34 28 Q34 40 28 48 Z" fill="#6b4a33" stroke="#0b1f3a" strokeWidth="2" />
      <path d="M98 44 Q106 26 86 28 Q86 40 92 48 Z" fill="#6b4a33" stroke="#0b1f3a" strokeWidth="2" />

      {/* Head and jowls */}
      <ellipse cx="60" cy="60" rx="40" ry="34" fill="#f6efe6" stroke="#0b1f3a" strokeWidth="2" />
      <ellipse cx="40" cy="80" rx="20" ry="15" fill="#f6efe6" stroke="#0b1f3a" strokeWidth="2" />
      <ellipse cx="80" cy="80" rx="20" ry="15" fill="#f6efe6" stroke="#0b1f3a" strokeWidth="2" />
      <ellipse cx="60" cy="74" rx="26" ry="18" fill="#f6efe6" />
      <ellipse cx="44" cy="55" rx="12" ry="11" fill="#d9b48f" opacity="0.8" />

      {/* Brows */}
      {stern ? (
        <path d="M38 47 L52 51 M82 47 L68 51" stroke="#0b1f3a" strokeWidth="2.5" strokeLinecap="round" />
      ) : worried ? (
        <path d="M38 51 L51 46 M82 51 L69 46" stroke="#0b1f3a" strokeWidth="2.5" strokeLinecap="round" />
      ) : (
        <path d="M39 48 Q45 45 51 48 M69 48 Q75 45 81 48" stroke="#0b1f3a" strokeWidth="2" fill="none" strokeLinecap="round" />
      )}

      {/* Eyes */}
      <g className="dan-eyes">
        <circle cx="46" cy="57" r="4.8" fill="#14161a" />
        <circle cx="74" cy="57" r="4.8" fill="#14161a" />
        <circle cx="47.5" cy="55.5" r="1.4" fill="#fff" />
        <circle cx="75.5" cy="55.5" r="1.4" fill="#fff" />
      </g>

      {/* Nose, mouth, underbite */}
      <ellipse cx="60" cy="68" rx="9.5" ry="6" fill="#1b1d22" />
      <ellipse cx="57" cy="66" rx="2.5" ry="1.4" fill="#5b6070" />
      <path d="M60 74 L60 79 M44 82 Q60 92 76 82" stroke="#0b1f3a" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M50 84 L52 78 L54 85 Z M66 85 L68 78 L70 84 Z" fill="#fff" stroke="#0b1f3a" strokeWidth="1" />
      {(agent === "customer_service" || mood === "done") && (
        <path d="M56 87 Q60 97 64 87 Z" fill="#ff7e9a" stroke="#0b1f3a" strokeWidth="1" />
      )}

      {/* Accessories */}
      {agent === "boss" && (
        <>
          <path d="M42 26 L46 12 L53 22 L60 8 L67 22 L74 12 L78 26 Z" fill="#f5c542" stroke="#0b1f3a" strokeWidth="2" />
          <circle cx="60" cy="10" r="2.5" fill="#ff5d5d" />
          <path d="M50 99 L60 104 L70 99 L70 109 L60 104 L50 109 Z" fill="#ff5d5d" stroke="#0b1f3a" strokeWidth="1.5" />
        </>
      )}
      {agent === "inventory" && (
        <>
          <path d="M30 32 Q60 8 90 32 Z" fill="#5ec2f2" stroke="#0b1f3a" strokeWidth="2" />
          <path d="M84 30 L104 32" stroke="#0b1f3a" strokeWidth="4" strokeLinecap="round" />
          <rect x="82" y="104" width="22" height="26" rx="2" fill="#c89b6d" stroke="#0b1f3a" strokeWidth="2" />
          <rect x="88" y="101" width="10" height="5" rx="1" fill="#9aa4b2" stroke="#0b1f3a" strokeWidth="1" />
          <path d="M86 112 H100 M86 118 H100 M86 124 H96" stroke="#fff" strokeWidth="1.5" />
        </>
      )}
      {agent === "accounting" && (
        <>
          <path d="M26 40 Q60 18 94 40 L90 44 Q60 28 30 44 Z" fill="#4fd18b" stroke="#0b1f3a" strokeWidth="2" opacity="0.95" />
          <circle cx="46" cy="57" r="9" fill="none" stroke="#0b1f3a" strokeWidth="2" />
          <circle cx="74" cy="57" r="9" fill="none" stroke="#0b1f3a" strokeWidth="2" />
          <path d="M55 57 H65" stroke="#0b1f3a" strokeWidth="2" />
        </>
      )}
      {agent === "facilities" && (
        <>
          <path d="M28 34 Q30 10 60 10 Q90 10 92 34 Z" fill="#ffcc33" stroke="#0b1f3a" strokeWidth="2" />
          <rect x="24" y="32" width="72" height="6" rx="3" fill="#ffcc33" stroke="#0b1f3a" strokeWidth="2" />
          <path d="M58 12 V32" stroke="#e0a800" strokeWidth="3" />
          <path d="M14 120 L30 104" stroke="#9aa4b2" strokeWidth="5" strokeLinecap="round" />
          <circle cx="32" cy="102" r="5" fill="none" stroke="#9aa4b2" strokeWidth="3" />
        </>
      )}
      {agent === "customer_service" && (
        <>
          <path d="M22 54 Q22 16 60 16 Q98 16 98 54" fill="none" stroke="#0b1f3a" strokeWidth="4" />
          <rect x="16" y="50" width="10" height="16" rx="4" fill="#ff7eb6" stroke="#0b1f3a" strokeWidth="2" />
          <rect x="94" y="50" width="10" height="16" rx="4" fill="#ff7eb6" stroke="#0b1f3a" strokeWidth="2" />
          <path d="M21 66 Q24 84 40 86" fill="none" stroke="#0b1f3a" strokeWidth="2.5" />
          <circle cx="41" cy="86" r="3" fill="#0b1f3a" />
        </>
      )}
    </svg>
  );
}
