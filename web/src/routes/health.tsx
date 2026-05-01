import { createFileRoute } from "@tanstack/react-router";
import { useHealth } from "../api/hooks/useHealth";

export const Route = createFileRoute("/health")({
  component: HealthPage,
});

function HealthPage() {
  const { data, isLoading, refetch } = useHealth({ refetchInterval: 30_000 });

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <h1 style={{ margin: 0 }}>Service Health</h1>
        <button onClick={() => void refetch()}>Refresh</button>
      </div>
      {isLoading && <p>Checking…</p>}
      {data && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #444" }}>
              <th style={{ textAlign: "left", padding: "0.5rem" }}>Service</th>
              <th style={{ textAlign: "left", padding: "0.5rem" }}>Status</th>
              <th style={{ textAlign: "left", padding: "0.5rem" }}>Detail</th>
            </tr>
          </thead>
          <tbody>
            {(["redis", "qdrant", "db", "ollama"] as const).map((svc) => {
              const s = data[svc];
              return (
                <tr key={svc} style={{ borderBottom: "1px solid #333" }}>
                  <td style={{ padding: "0.5rem" }}>{svc}</td>
                  <td
                    style={{
                      padding: "0.5rem",
                      color: s.ok ? "#4ade80" : "#f87171",
                    }}
                  >
                    {s.ok ? "OK" : "DOWN"}
                  </td>
                  <td style={{ padding: "0.5rem", color: "#999" }}>{s.detail ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
