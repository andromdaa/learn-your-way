import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type JobResultResponse = {
  status: "complete" | "failed" | "in_progress" | "not_found";
  result?: Record<string, unknown>;
  error?: string;
  traceback?: string;
};

export function useJobResult(jobId: string | undefined) {
  return useQuery({
    queryKey: ["job-result", jobId],
    queryFn: () => api.get<JobResultResponse>(`/v1/jobs/${jobId}/result`),
    enabled: !!jobId,
  });
}
