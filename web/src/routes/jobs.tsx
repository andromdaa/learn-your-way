import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

export const Route = createFileRoute("/jobs")({
  component: JobsPage,
});

type JobEvent = {
  id: string;
  event: string;
  ts: number;
  data: Record<string, unknown>;
};

function JobsPage() {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/v1/jobs/events");
    esRef.current = es;

    function handler(e: MessageEvent) {
      try {
        const data = JSON.parse(e.data) as Record<string, unknown>;
        setEvents((prev) => {
          const next = [
            ...prev,
            { id: Math.random().toString(36).slice(2), event: e.type, ts: Date.now(), data },
          ];
          return next.slice(-100);
        });
      } catch {
        // ignore parse errors
      }
    }

    es.addEventListener("progress", handler);
    es.addEventListener("complete", handler);
    es.addEventListener("error", handler);

    return () => {
      es.close();
    };
  }, []);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Live Job Feed</h1>
      <p style={{ color: "#999" }}>Showing last 100 events from all workers.</p>
      {events.length === 0 && <p style={{ color: "#666" }}>Waiting for events…</p>}
      <div style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
        {[...events].reverse().map((ev) => (
          <div
            key={ev.id}
            style={{
              padding: "0.4rem 0.5rem",
              borderBottom: "1px solid #333",
              color:
                ev.event === "error"
                  ? "#f87171"
                  : ev.event === "complete"
                    ? "#4ade80"
                    : "#eee",
            }}
          >
            <span style={{ color: "#666" }}>{new Date(ev.ts).toISOString().slice(11, 23)} </span>
            <span style={{ color: "#a78bfa" }}>[{ev.event}] </span>
            {JSON.stringify(ev.data)}
          </div>
        ))}
      </div>
    </div>
  );
}
