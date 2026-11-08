import taxonomy from "../../contracts/taxonomy.json";
import type { Score } from "./demo";
const names: Record<string, string> = {
  pig_butchering: "CRYPTO",
  bank_impersonation: "BANK",
  family_emergency: "FAMILY",
  job_task: "JOB",
  toll_delivery: "DELIVERY",
  carrier_support: "SUPPORT",
};
export function Compass({ score }: { score: Score }) {
  const directions = taxonomy.families.filter((f) => f.compass_deg !== null);
  let x = 0,
    y = 0;
  for (const f of directions) {
    const radians = (f.compass_deg! * Math.PI) / 180;
    const p = (score.family_probs as Record<string, number>)[f.id] ?? 0;
    x += p * Math.sin(radians);
    y -= p * Math.cos(radians);
  }
  const magnitude = Math.hypot(x, y);
  const angle = (Math.atan2(x, -y) * 180) / Math.PI;
  const length = score.risk * 60;
  const dx = magnitude > 1e-6 ? (x / magnitude) * length : 0;
  const dy = magnitude > 1e-6 ? (y / magnitude) * length : 0;
  return (
    <svg
      viewBox="0 0 240 220"
      role="img"
      aria-label={`Trajectory Compass: ${magnitude > 1e-6 ? `${Math.round(angle)} degrees, needle length ${Math.round(score.risk * 100)} percent of radius` : "no dominant direction"}. ${score.family.label}.`}
    >
      <defs>
        <radialGradient id="compass-glow">
          <stop stopColor="#3d8175" stopOpacity=".13" />
          <stop offset="1" stopColor="#3d8175" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle
        cx="120"
        cy="110"
        r="79"
        fill="url(#compass-glow)"
        stroke="#80947b"
        strokeOpacity=".35"
      />
      <circle
        cx="120"
        cy="110"
        r="60"
        fill="none"
        stroke="#80947b"
        strokeOpacity=".2"
        strokeDasharray="2 5"
      />
      <circle
        cx="120"
        cy="110"
        r="30"
        fill="none"
        stroke="#80947b"
        strokeOpacity=".16"
      />
      {directions.map((f) => {
        const r = (f.compass_deg! * Math.PI) / 180,
          sx = Math.sin(r),
          sy = -Math.cos(r);
        return (
          <g key={f.id}>
            <line
              x1={120 + sx * 68}
              y1={110 + sy * 68}
              x2={120 + sx * 79}
              y2={110 + sy * 79}
              stroke="#80947b"
            />
            <text
              x={120 + sx * 99}
              y={114 + sy * 96}
              textAnchor="middle"
              fill={score.family.id === f.id ? "#a4523e" : "#56684f"}
              fontSize="9"
              fontFamily="monospace"
            >
              {names[f.id]}
            </text>
          </g>
        );
      })}
      {magnitude > 1e-6 && (
        <g>
          <line
            x1="120"
            y1="110"
            x2={120 + dx}
            y2={110 + dy}
            stroke="#3d8175"
            strokeWidth="3"
          />
          <circle cx={120 + dx} cy={110 + dy} r="4" fill="#3d8175" />
        </g>
      )}
      <circle cx="120" cy="110" r="5" fill="#365642" />
    </svg>
  );
}
