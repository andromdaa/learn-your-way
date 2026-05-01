import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type LessonSummary = {
  id: string;
  source_id: string;
  concept_count: number;
  created_at: string;
};

export type ConceptNode = {
  id: string;
  title: string;
  summary: string;
  learning_objective: string;
  source_spans: SourceSpan[];
  prerequisites: string[];
  bloom_level?: string;
  temporal_position?: string;
};

export type SourceSpan = {
  doc_id: string;
  page_start: number;
  page_end: number;
  char_start: number;
  char_end: number;
};

export type LessonGraph = {
  id: string;
  source_id: string;
  concepts: ConceptNode[];
};

export type AssessmentItem = {
  id: string;
  kind: string;
  prompt: string;
  options?: string[];
  correct_answer?: string;
  rationale: string;
  difficulty: string;
  bloom_level?: string;
  concept_id: string;
  source_spans: SourceSpan[];
  quiz_id?: string;
};

export type StoredDerivedAsset = {
  id: string;
  lesson_id: string;
  concept_id: string;
  kind: string;
  profile_id: string;
  file_path: string;
  created_at: string;
};

export type QuizSummary = {
  quiz_id: string;
  item_count: number;
};

export function useLessons() {
  return useQuery({
    queryKey: ["lessons"],
    queryFn: () => api.get<LessonSummary[]>("/lessons"),
  });
}

export function useLesson(lessonId: string | undefined) {
  return useQuery({
    queryKey: ["lesson", lessonId],
    queryFn: () => api.get<LessonGraph>(`/lessons/${lessonId}`),
    enabled: !!lessonId,
  });
}

export function useConceptNode(lessonId: string | undefined, conceptId: string | undefined) {
  return useQuery({
    queryKey: ["lesson", lessonId, "concept", conceptId],
    queryFn: () => api.get<ConceptNode>(`/lessons/${lessonId}/concepts/${conceptId}`),
    enabled: !!lessonId && !!conceptId,
  });
}

export function useLessonItems(
  lessonId: string | undefined,
  opts?: { conceptId?: string; quizId?: string },
) {
  const params = new URLSearchParams();
  if (opts?.conceptId) params.set("concept_id", opts.conceptId);
  if (opts?.quizId) params.set("quiz_id", opts.quizId);
  const qs = params.toString();
  return useQuery({
    queryKey: ["lesson", lessonId, "items", opts],
    queryFn: () =>
      api.get<AssessmentItem[]>(`/lessons/${lessonId}/items${qs ? `?${qs}` : ""}`),
    enabled: !!lessonId,
  });
}

export function useLessonAssets(
  lessonId: string | undefined,
  opts?: { conceptId?: string; kind?: string; profileId?: string },
) {
  const params = new URLSearchParams();
  if (opts?.conceptId) params.set("concept_id", opts.conceptId);
  if (opts?.kind) params.set("kind", opts.kind);
  if (opts?.profileId) params.set("profile_id", opts.profileId);
  const qs = params.toString();
  return useQuery({
    queryKey: ["lesson", lessonId, "assets", opts],
    queryFn: () =>
      api.get<StoredDerivedAsset[]>(`/lessons/${lessonId}/assets${qs ? `?${qs}` : ""}`),
    enabled: !!lessonId,
  });
}

export function useLessonQuizzes(lessonId: string | undefined) {
  return useQuery({
    queryKey: ["lesson", lessonId, "quizzes"],
    queryFn: () => api.get<QuizSummary[]>(`/lessons/${lessonId}/quizzes`),
    enabled: !!lessonId,
  });
}
