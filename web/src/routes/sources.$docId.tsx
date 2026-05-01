import { createFileRoute, useParams } from "@tanstack/react-router";
import { useSource } from "../api/hooks/useSources";
import { useJobEvents } from "../api/sse";
import { useState } from "react";

export const Route = createFileRoute("/sources/$docId")({
  component: SourceDetailPage,
});

function SourceDetailPage() {
  const { docId } = useParams({ from: "/sources/$docId" });
  const { data: source, isLoading, error } = useSource(docId);
  const [watchJobId, setWatchJobId] = useState<string | undefined>();
  const { state: jobState, done: jobDone } = useJobEvents(watchJobId);

  if (isLoading) return <p>Loading…</p>;
  if (error || !source) return <p style={{ color: "#f87171" }}>Source not found.</p>;

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Source Detail</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div>
          <h2>Metadata</h2>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <tbody>
              <Row label="Doc ID" value={<code style={{ fontSize: "0.8rem" }}>{source.doc_id}</code>} />
              <Row label="SHA-256" value={<code style={{ fontSize: "0.8rem" }}>{source.sha256.slice(0, 20)}…</code>} />
              <Row label="Created" value={source.created_at.slice(0, 19).replace("T", " ")} />
              <Row
                label="Lesson"
                value={
                  source.lesson_id ? (
                    <a href={`/lessons/${source.lesson_id}`} style={{ color: "#60a5fa" }}>
                      {source.lesson_id.slice(0, 16)}…
                    </a>
                  ) : (
                    <span style={{ color: "#666" }}>Not yet ingested</span>
                  )
                }
              />
            </tbody>
          </table>

          <div style={{ marginTop: "1rem" }}>
            <a
              href={`/sources/${source.doc_id}/file`}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "inline-block",
                padding: "0.4rem 1rem",
                background: "#2563eb",
                color: "#fff",
                borderRadius: 4,
                marginRight: "0.5rem",
              }}
            >
              View PDF
            </a>
          </div>
        </div>

        {watchJobId && (
          <div>
            <h2>Ingest Progress</h2>
            <ProgressBar pct={jobState.pct} />
            <p style={{ color: "#999", fontSize: "0.85rem" }}>
              Phase: {jobState.phase}
              {jobDone && (
                <span style={{ color: jobState.status === "error" ? "#f87171" : "#4ade80" }}>
                  {" "}— {jobState.status === "error" ? jobState.error : "complete"}
                </span>
              )}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr style={{ borderBottom: "1px solid #333" }}>
      <td style={{ padding: "0.4rem 0.5rem", color: "#999", width: 120 }}>{label}</td>
      <td style={{ padding: "0.4rem 0.5rem" }}>{value}</td>
    </tr>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div style={{ background: "#333", borderRadius: 4, height: 8, width: "100%" }}>
      <div
        style={{
          background: "#2563eb",
          width: `${Math.round(pct * 100)}%`,
          height: "100%",
          borderRadius: 4,
          transition: "width 0.3s",
        }}
      />
    </div>
  );
}
