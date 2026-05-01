import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../client";

type GenerateKind = "relevel" | "replace";

export type GenerateRequest = {
  concept_id: string;
  profile_id: string;
  kind: GenerateKind;
};

export type GenerateResponse = {
  job_id: string;
  status: string;
};

export type GenerateResult = {
  job_id: string;
  status: string;
  result?: Record<string, unknown>;
};

export function useGenerateLesson(lessonId: string) {
  return useMutation({
    mutationFn: (body: GenerateRequest) =>
      api.post<GenerateResponse>(`/lessons/${lessonId}/generate`, body),
  });
}

export function useGenerateResult(
  lessonId: string | undefined,
  jobId: string | undefined,
) {
  return useQuery({
    queryKey: ["generate-result", lessonId, jobId],
    queryFn: () =>
      api.get<GenerateResult>(`/lessons/${lessonId}/generate/${jobId}`),
    enabled: !!lessonId && !!jobId,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "complete" || status === "not_found" ? false : 2000;
    },
  });
}
