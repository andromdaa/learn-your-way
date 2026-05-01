import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  useProfiles,
  useCreateProfile,
  useDeleteProfile,
  type CreateProfileRequest,
} from "../api/hooks/useProfiles";

export const Route = createFileRoute("/profiles")({
  component: ProfilesPage,
});

function ProfilesPage() {
  const { data: profiles, isLoading } = useProfiles();
  const create = useCreateProfile();
  const del = useDeleteProfile();
  const [form, setForm] = useState<CreateProfileRequest>({
    grade_level: "",
    interests: [],
    goals: [],
  });
  const [interestInput, setInterestInput] = useState("");
  const [goalInput, setGoalInput] = useState("");

  function handleCreate() {
    create.mutate(form, {
      onSuccess: () => setForm({ grade_level: "", interests: [], goals: [] }),
    });
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Profiles</h1>

      <div
        style={{
          background: "#1a1a2e",
          padding: "1rem",
          borderRadius: 8,
          marginBottom: "1.5rem",
          maxWidth: 400,
        }}
      >
        <h3 style={{ margin: "0 0 0.75rem" }}>New Profile</h3>
        <input
          placeholder="Grade level"
          value={form.grade_level}
          onChange={(e) => setForm({ ...form, grade_level: e.target.value })}
          style={{ display: "block", width: "100%", marginBottom: "0.5rem", padding: "0.4rem", boxSizing: "border-box" }}
        />
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <input
            placeholder="Add interest"
            value={interestInput}
            onChange={(e) => setInterestInput(e.target.value)}
            style={{ flex: 1, padding: "0.4rem" }}
          />
          <button
            onClick={() => {
              if (interestInput.trim()) {
                setForm({ ...form, interests: [...form.interests, interestInput.trim()] });
                setInterestInput("");
              }
            }}
          >
            +
          </button>
        </div>
        {form.interests.length > 0 && (
          <div style={{ marginBottom: "0.5rem", color: "#999" }}>
            Interests: {form.interests.join(", ")}
          </div>
        )}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <input
            placeholder="Add goal"
            value={goalInput}
            onChange={(e) => setGoalInput(e.target.value)}
            style={{ flex: 1, padding: "0.4rem" }}
          />
          <button
            onClick={() => {
              if (goalInput.trim()) {
                setForm({ ...form, goals: [...form.goals, goalInput.trim()] });
                setGoalInput("");
              }
            }}
          >
            +
          </button>
        </div>
        {form.goals.length > 0 && (
          <div style={{ marginBottom: "0.75rem", color: "#999" }}>
            Goals: {form.goals.join(", ")}
          </div>
        )}
        <button
          onClick={handleCreate}
          disabled={!form.grade_level || create.isPending}
          style={{ padding: "0.4rem 1rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          {create.isPending ? "Creating…" : "Create"}
        </button>
      </div>

      {isLoading && <p>Loading…</p>}
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #444" }}>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>ID</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Grade</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Interests</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>Created</th>
            <th style={{ textAlign: "left", padding: "0.5rem" }}></th>
          </tr>
        </thead>
        <tbody>
          {profiles?.map((p) => (
            <tr key={p.id} style={{ borderBottom: "1px solid #333" }}>
              <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.85rem" }}>
                {p.id.slice(0, 12)}…
              </td>
              <td style={{ padding: "0.5rem" }}>{p.grade_level}</td>
              <td style={{ padding: "0.5rem", color: "#999" }}>{p.interests.join(", ") || "—"}</td>
              <td style={{ padding: "0.5rem", color: "#999" }}>{p.created_at.slice(0, 10)}</td>
              <td style={{ padding: "0.5rem" }}>
                <button
                  onClick={() => del.mutate(p.id)}
                  style={{ color: "#f87171", background: "none", border: "none", cursor: "pointer" }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
