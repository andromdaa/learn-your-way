import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AssessmentItem } from "./useLessons";
import type { AttemptRecord } from "./useProfiles";

export type JobEnqueuedResponse = {
  job_id: string;
  status: string;
};

export type GlowsGrowsResponse = {
  glows: string;
  grows: string;
};

export function useQuiz(
  lessonId: string | undefined,
  quizId: string | undefined,
) {
  return useQuery({
    queryKey: ["quiz", lessonId, quizId],
    queryFn: () =>
      api.get<AssessmentItem[]>(`/lessons/${lessonId}/quiz/${quizId}`),
    enabled: !!lessonId && !!quizId,
  });
}

export function useGenerateQuiz(lessonId: string) {
  return useMutation({
    mutationFn: (body: {
      profile_id: string;
      scope?: "concept" | "lesson";
      concept_ids?: string[];
    }) => api.post<JobEnqueuedResponse>(`/lessons/${lessonId}/quiz`, body),
  });
}

export function useGenerateMcq(lessonId: string, conceptId: string) {
  return useMutation({
    mutationFn: (body: { profile_id: string }) =>
      api.post<JobEnqueuedResponse>(
        `/lessons/${lessonId}/concepts/${conceptId}/mcq`,
        body,
      ),
  });
}

export function useGlowsGrows(quizId: string | undefined) {
  return useMutation({
    mutationFn: (body: { profile_id: string }) =>
      api.post<GlowsGrowsResponse>(`/quizzes/${quizId}/glows-grows`, body),
  });
}

export function useAttemptsByQuiz(
  quizId: string | undefined,
  profileId: string | undefined,
) {
  return useQuery({
    queryKey: ["attempts-by-quiz", quizId, profileId],
    queryFn: () =>
      api.get<AttemptRecord[]>(
        `/attempts/by-quiz?quiz_id=${quizId}&profile_id=${profileId}`,
      ),
    enabled: !!quizId && !!profileId,
  });
}

export function useBulkGenerate(lessonId: string) {
  return useMutation({
    mutationFn: (body: {
      profile_id: string;
      kinds: string[];
      skip_existing?: boolean;
    }) =>
      api.post<JobEnqueuedResponse>(`/lessons/${lessonId}/bulk-generate`, body),
  });
}
