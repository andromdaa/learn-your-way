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

export type StoredDerivedAsset = {
  id: string;
  lesson_id: string;
  concept_id: string;
  kind: string;
  profile_id: string;
  file_path: string;
  created_at: string;
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
