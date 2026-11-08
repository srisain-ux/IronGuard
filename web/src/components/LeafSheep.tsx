import { useEffect, useState } from "react";
import type { ChloroplastManifest } from "../contracts/chloroplast";
import { vitality } from "../runtime/chloroplast";
import { useMocks } from "../api/client";

export function LeafSheep({ manifests, status }: { manifests: ChloroplastManifest[]; status: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 60_000); return () => clearInterval(timer); }, []);
  return <section className="leaf-sheep" aria-label="Leaf sheep adapters">
    <div className="sheep"><img src="/botanical/leaf-sheep.webp" width="100" height="100" alt={`Leaf sheep with ${manifests.length} downloaded chloroplasts`} /><div><strong>Leaf Sheep</strong><p>{useMocks ? "Fixture chloroplasts" : `${manifests.length} downloaded adapters`}</p><small>{status || (useMocks ? "Display fixture; adapter weights are placeholders." : manifests.length ? "Vitality prompts a refresh; protection stays on." : "No chloroplast loaded")}</small></div></div>
    <div className="cerata-list">{manifests.map(manifest => { const value = vitality(manifest, now); return <div className="cerata" key={manifest.id}>
      <span className="cerata-glow" aria-hidden="true">❧</span><div><strong>{manifest.label}</strong><meter className="cerata-vitality" min={0} max={1} value={value} aria-label={`${manifest.label} display vitality ${(value * 100).toFixed(0)}%`} /><small>{(value * 100).toFixed(0)}% vitality · display only</small></div>
    </div>; })}</div>
  </section>;
}
