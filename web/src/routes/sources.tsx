import { createFileRoute } from "@tanstack/react-router";
import { useSources, useUploadSource } from "../api/hooks/useSources";
import type { ChangeEvent } from "react";

export const Route = createFileRoute("/sources")({
  component: SourcesPage,
});

function SourcesPage() {
  const { data: sources, isLoading } = useSources();
  const upload = useUploadSource();

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Sources</h1>

      <div style={{ marginBottom: "1.5rem" }}>
        <label
          style={{
            display: "inline-block",
            padding: "0.5rem 1rem",
            background: "#2563eb",
            color: "#fff",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          Upload PDF
          <input
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
            onChange={handleFile}
          />
        </label>
        {upload.isPending && <span style={{ marginLeft: "1rem" }}>Uploading…</span>}
        {upload.isError && (
          <span style={{ marginLeft: "1rem", color: "#f87171" }}>
            Upload failed: {upload.error.message}
          </span>
        )}
        {upload.isSuccess && (
          <span style={{ marginLeft: "1rem", color: "#4ade80" }}>
            Uploaded — job_id: {upload.data.job_id ?? "n/a"}
          </span>
        )}
      </div>

      {isLoading && <p>Loading…</p>}
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #444" }}>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Doc ID</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Created</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Lesson</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>File</th>
          </tr>
        </thead>
        <tbody>
          {sources?.map((s) => (
            <tr key={s.doc_id} style={{ borderBottom: "1px solid #333" }}>
              <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.85rem" }}>
                {s.doc_id.slice(0, 12)}…
              </td>
              <td style={{ padding: "0.5rem", color: "#999" }}>{s.created_at.slice(0, 10)}</td>
              <td style={{ padding: "0.5rem" }}>
                {s.lesson_id ? (
                  <a href={`/lessons/${s.lesson_id}`} style={{ color: "#60a5fa" }}>
                    {s.lesson_id.slice(0, 12)}…
                  </a>
                ) : (
                  <span style={{ color: "#666" }}>—</span>
                )}
              </td>
              <td style={{ padding: "0.5rem" }}>
                <a
                  href={`/sources/${s.doc_id}/file`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "#60a5fa" }}
                >
                  PDF
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
