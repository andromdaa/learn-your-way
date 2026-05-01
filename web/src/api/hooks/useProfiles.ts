import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type LearnerProfile = {
  id: string;
  grade_level: string;
  interests: string[];
  goals: string[];
  created_at: string;
};

export type CreateProfileRequest = {
  grade_level: string;
  interests: string[];
  goals: string[];
};

export type AttemptRecord = {
  id: string;
  profile_id: string;
  item_id: string;
  response: string;
  correct: boolean;
  attempted_at: string;
};

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.get<LearnerProfile[]>("/profiles"),
  });
}

export function useProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: ["profile", profileId],
    queryFn: () => api.get<LearnerProfile>(`/profiles/${profileId}`),
    enabled: !!profileId,
  });
}

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProfileRequest) =>
      api.post<LearnerProfile>("/profiles", body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useUpdateProfile(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProfileRequest) =>
      api.put<LearnerProfile>(`/profiles/${profileId}`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["profiles"] });
      void qc.invalidateQueries({ queryKey: ["profile", profileId] });
    },
  });
}

export function useDeleteProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => api.delete(`/profiles/${profileId}`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useProfileAttempts(profileId: string | undefined) {
  return useQuery({
    queryKey: ["profile", profileId, "attempts"],
    queryFn: () => api.get<AttemptRecord[]>(`/profiles/${profileId}/attempts`),
    enabled: !!profileId,
  });
}
