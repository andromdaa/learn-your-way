import { useEffect, useRef, useState } from "react";

let mermaidReady = false;
let mermaidInit: Promise<void> | null = null;

function ensureMermaid() {
  if (mermaidReady) return Promise.resolve();
  if (mermaidInit) return mermaidInit;
  mermaidInit = import("mermaid").then((mod) => {
    const m = mod.default;
    m.initialize({ startOnLoad: false, theme: "dark" });
    mermaidReady = true;
  });
  return mermaidInit;
}

type Props = { source: string; id: string };

export default function MermaidAsset({ source, id }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    ensureMermaid()
      .then(() => import("mermaid"))
      .then(async ({ default: mermaid }) => {
        if (cancelled || !ref.current) return;
        try {
          const { svg } = await mermaid.render(`mermaid-${id}`, source);
          if (!cancelled && ref.current) {
            ref.current.innerHTML = svg;
          }
        } catch (err) {
          if (!cancelled) setError(String(err));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [source, id]);

  if (error) {
    return (
      <div>
        <p style={{ color: "#f87171" }}>Failed to render diagram: {error}</p>
        <pre style={{ background: "#1e1e2e", padding: "0.5rem", fontSize: "0.8rem", overflow: "auto" }}>
          {source}
        </pre>
      </div>
    );
  }

  return <div ref={ref} style={{ background: "#1e1e2e", padding: "0.5rem", borderRadius: 6 }} />;
}
