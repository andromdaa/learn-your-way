import { useEffect, useState } from "react";
import MermaidAsset from "./MermaidAsset";
import type { StoredDerivedAsset } from "../api/hooks/useLessons";

type Props = {
  asset: StoredDerivedAsset;
};

export default function AssetViewer({ asset }: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/v1/assets/${asset.id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        setContent(text);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(String(err));
        setLoading(false);
      });
  }, [asset.id]);

  if (loading) return <p style={{ color: "#999" }}>Loading asset…</p>;
  if (error) return <p style={{ color: "#f87171" }}>Error: {error}</p>;
  if (!content) return null;

  const kind = asset.kind;

  if (kind === "mind_map" || kind === "timeline") {
    return <MermaidAsset source={content} id={asset.id} />;
  }

  if (kind === "slides") {
    return <SlidesViewer raw={content} />;
  }

  return (
    <pre
      style={{
        background: "#1e1e2e",
        padding: "1rem",
        borderRadius: 6,
        fontSize: "0.85rem",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        margin: 0,
        overflow: "auto",
        maxHeight: 400,
      }}
    >
      {content}
    </pre>
  );
}

function SlidesViewer({ raw }: { raw: string }) {
  let deck: { title: string; body: string; speaker_notes?: string }[] = [];
  try {
    const parsed = JSON.parse(raw) as {
      slides?: { title: string; body: string; speaker_notes?: string }[];
    };
    deck = parsed.slides ?? [];
  } catch {
    return <pre style={{ background: "#1e1e2e", padding: "1rem" }}>{raw}</pre>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {deck.map((slide, i) => (
        <article
          key={i}
          style={{
            background: "#1e1e2e",
            border: "1px solid #333",
            borderRadius: 6,
            padding: "0.75rem",
          }}
        >
          <strong style={{ display: "block", marginBottom: "0.4rem" }}>{slide.title}</strong>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "#ccc" }}>{slide.body}</p>
          {slide.speaker_notes && (
            <details style={{ marginTop: "0.5rem" }}>
              <summary style={{ color: "#666", fontSize: "0.8rem", cursor: "pointer" }}>
                Speaker notes
              </summary>
              <p style={{ margin: "0.4rem 0 0", fontSize: "0.8rem", color: "#999" }}>
                {slide.speaker_notes}
              </p>
            </details>
          )}
        </article>
      ))}
    </div>
  );
}
