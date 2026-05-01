import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type ServiceHealth = { ok: boolean; detail?: string };
export type HealthResponse = {
  redis: ServiceHealth;
  qdrant: ServiceHealth;
  db: ServiceHealth;
  ollama: ServiceHealth;
};

export function useHealth(opts?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<HealthResponse>("/healthz"),
    refetchInterval: opts?.refetchInterval,
  });
}
