import { createFileRoute } from "@tanstack/react-router";
import { useHealth } from "../api/hooks/useHealth";
import { useLessons } from "../api/hooks/useLessons";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

function Dashboard() {
  const health = useHealth({ refetchInterval: 30_000 });
  const lessons = useLessons();

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>

      <section>
        <h2>Service Health</h2>
        {health.isLoading && <p>Checking…</p>}
        {health.data && (
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            {(["redis", "qdrant", "db", "ollama"] as const).map((svc) => {
              const s = health.data[svc];
              return (
                <div
                  key={svc}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: 6,
                    background: s.ok ? "#1a3a1a" : "#3a1a1a",
                    color: s.ok ? "#4ade80" : "#f87171",
                    border: `1px solid ${s.ok ? "#4ade80" : "#f87171"}`,
                  }}
                >
                  <strong>{svc}</strong>: {s.ok ? "OK" : s.detail ?? "down"}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>Recent Lessons</h2>
        {lessons.isLoading && <p>Loading…</p>}
        {lessons.data?.slice(0, 5).map((l) => (
          <div key={l.id} style={{ marginBottom: "0.5rem" }}>
            <a href={`/lessons/${l.id}`} style={{ color: "#60a5fa" }}>
              {l.id}
            </a>{" "}
            — {l.concept_count} concepts
          </div>
        ))}
        {lessons.data?.length === 0 && <p>No lessons yet. Upload a PDF source to get started.</p>}
      </section>
    </div>
  );
}
