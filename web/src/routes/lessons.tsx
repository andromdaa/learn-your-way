import { createFileRoute, Link } from "@tanstack/react-router";
import { useLessons } from "../api/hooks/useLessons";

export const Route = createFileRoute("/lessons")({
  component: LessonsPage,
});

function LessonsPage() {
  const { data: lessons, isLoading } = useLessons();

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Lessons</h1>
      {isLoading && <p>Loading…</p>}
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #444" }}>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>ID</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Source</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Concepts</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {lessons?.map((l) => (
            <tr key={l.id} style={{ borderBottom: "1px solid #333" }}>
              <td style={{ padding: "0.5rem" }}>
                <Link to="/lessons/$lessonId" params={{ lessonId: l.id }} style={{ color: "#60a5fa" }}>
                  {l.id.slice(0, 16)}…
                </Link>
              </td>
              <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.85rem", color: "#999" }}>
                {l.source_id.slice(0, 12)}…
              </td>
              <td style={{ padding: "0.5rem" }}>{l.concept_count}</td>
              <td style={{ padding: "0.5rem", color: "#999" }}>{l.created_at.slice(0, 10)}</td>
            </tr>
          ))}
          {lessons?.length === 0 && (
            <tr>
              <td colSpan={4} style={{ padding: "1rem", color: "#666" }}>
                No lessons yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
