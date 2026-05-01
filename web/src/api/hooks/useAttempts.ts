import { useMutation } from "@tanstack/react-query";
import { api } from "../client";

export type AttemptRequest = {
  profile_id: string;
  item_id: string;
  response: string;
  defer_glows_grows?: boolean;
};

export type AttemptFeedback = {
  correct: boolean;
  rationale: string;
  source_spans: unknown[];
  suggested_next_concept_id?: string;
  glows?: string;
  grows?: string;
};

export type RecommendationResponse = {
  next_concept_id?: string;
  reason: string;
};

export function useRecordAttempt() {
  return useMutation({
    mutationFn: (body: AttemptRequest) =>
      api.post<AttemptFeedback>("/attempts", body),
  });
}

export function useNextRecommendation() {
  return useMutation({
    mutationFn: (body: { profile_id: string; lesson_id: string }) =>
      api.post<RecommendationResponse>("/recommendations/next", body),
  });
}
