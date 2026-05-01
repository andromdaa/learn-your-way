import { useEffect, useState } from "react";
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
