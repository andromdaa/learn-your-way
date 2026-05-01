import { useEffect, useState } from "react";

export type SseEvent = {
  event: string;
  data: unknown;
};

export type JobState = {
  phase: string;
  pct: number;
  status?: string;
  error?: string;
  traceback?: string;
  events: SseEvent[];
};

export function useJobEvents(jobId: string | undefined) {
  const [state, setState] = useState<JobState>({
    phase: "queued",
    pct: 0,
    events: [],
  });
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    setDone(false);
    setState({ phase: "queued", pct: 0, events: [] });

    const es = new EventSource(`/v1/jobs/${jobId}/events`);

    es.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data) as { phase: string; pct: number };
      setState((prev) => ({
        ...prev,
        phase: data.phase,
        pct: data.pct,
        events: [...prev.events, { event: "progress", data }],
      }));
    });

    es.addEventListener("complete", (e) => {
      const data = JSON.parse(e.data) as { event: string };
      setState((prev) => ({
        ...prev,
        status: "complete",
        phase: "complete",
        pct: 1,
        events: [...prev.events, { event: "complete", data }],
      }));
      setDone(true);
      es.close();
    });

    es.addEventListener("error", (e) => {
      const data = JSON.parse((e as MessageEvent).data ?? "{}") as {
        error?: string;
        traceback?: string;
      };
      setState((prev) => ({
        ...prev,
        status: "error",
        error: data.error,
        traceback: data.traceback,
        events: [...prev.events, { event: "error", data }],
      }));
      setDone(true);
      es.close();
    });

    return () => {
      es.close();
    };
  }, [jobId]);

  return { state, done };
}
