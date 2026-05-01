import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type SourceDetail = {
  doc_id: string;
  path: string;
  sha256: string;
  created_at: string;
  lesson_id?: string;
};

export type ExcerptResponse = {
  text: string;
  doc_id: string;
  char_start: number;
  char_end: number;
  window_start: number;
};

export type UploadResponse = {
  id: string;
  title: string;
  status: "parsing" | "ready" | "failed";
  job_id?: string;
};

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => api.get<SourceDetail[]>("/sources"),
  });
}

export function useSource(docId: string | undefined) {
  return useQuery({
    queryKey: ["source", docId],
    queryFn: () => api.get<SourceDetail>(`/sources/${docId}`),
    enabled: !!docId,
  });
}

export function useSourceExcerpt(
  docId: string | undefined,
  charStart: number | undefined,
  charEnd: number | undefined,
  radius = 200,
) {
  return useQuery({
    queryKey: ["excerpt", docId, charStart, charEnd, radius],
    queryFn: () =>
      api.get<ExcerptResponse>(
        `/sources/${docId}/excerpt?char_start=${charStart}&char_end=${charEnd}&radius=${radius}`,
      ),
    enabled: !!docId && charStart !== undefined && charEnd !== undefined,
  });
}

export function useUploadSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/sources", { method: "POST", body: form });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json() as Promise<UploadResponse>;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}
