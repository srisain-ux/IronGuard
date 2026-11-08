import { useEffect, useState } from "react";
import type { ChloroplastManifest } from "../contracts/chloroplast";
import { vitality } from "../runtime/chloroplast";
import { useMocks } from "../api/client";

export function LeafSheep({ manifests, status }: { manifests: ChloroplastManifest[]; status: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 60_000); return () => clearInterval(timer); }, []);
  return <section className="leaf-sheep" aria-label="Leaf sheep adapters">
    <div className="sheep"><svg viewBox="0 0 100 82" role="img" aria-label={`Leaf sheep with ${manifests.length} chloroplast cerata`}>
      <g fill="#5dff9b" stroke="#184f48" strokeWidth="1.5">{[24, 42, 60, 78].map((x, i) => <ellipse key={x} cx={x} cy={33 - (i % 2) * 8} rx="9" ry="24" transform={`rotate(${(i - 1.5) * 18} ${x} 33)`} />)}</g>
      <ellipse cx="50" cy="62" rx="36" ry="17" fill="#dfefd9" /><path d="M27 53 23 38M73 53 77 38" stroke="#dfefd9" strokeWidth="6" strokeLinecap="round" /><circle cx="38" cy="59" r="3" fill="#100a37" /><circle cx="62" cy="59" r="3" fill="#100a37" /><path d="M45 68q5 5 10 0" fill="none" stroke="#100a37" strokeWidth="2" />
    </svg><div><strong>Leaf Sheep</strong><p>{useMocks ? "Fixture chloroplasts" : `${manifests.length} downloaded adapters`}</p><small>{status || (useMocks ? "Display fixture; adapter weights are placeholders." : manifests.length ? "Vitality prompts a refresh; protection stays on." : "No chloroplast loaded")}</small></div></div>
    <div className="cerata-list">{manifests.map(manifest => { const value = vitality(manifest, now); return <div className="cerata" key={manifest.id}>
      <span className="cerata-glow" aria-hidden="true">❧</span><div><strong>{manifest.label}</strong><meter className="cerata-vitality" min={0} max={1} value={value} aria-label={`${manifest.label} display vitality ${(value * 100).toFixed(0)}%`} /><small>{(value * 100).toFixed(0)}% vitality · display only</small></div>
    </div>; })}</div>
  </section>;
}
