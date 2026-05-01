import { createFileRoute, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useQuiz, useGlowsGrows } from "../api/hooks/useQuizzes";
import { useRecordAttempt, useNextRecommendation } from "../api/hooks/useAttempts";
import { useProfiles } from "../api/hooks/useProfiles";
import type { AssessmentItem } from "../api/hooks/useLessons";
import type { AttemptFeedback } from "../api/hooks/useAttempts";

export const Route = createFileRoute("/quizzes/$quizId")({
  component: QuizPlayerPage,
});

type QuizPhase = "playing" | "submitting" | "reviewing";

function QuizPlayerPage() {
  const { quizId } = useParams({ from: "/quizzes/$quizId" });
  const { data: items, isLoading } = useQuiz(undefined, quizId);
  const { data: profiles } = useProfiles();
  const [profileId] = useState<string>(() => profiles?.[0]?.id ?? "");

  const recordAttempt = useRecordAttempt();
  const glowsGrows = useGlowsGrows(quizId);
  const nextRec = useNextRecommendation();

  const [responses, setResponses] = useState<Record<string, string>>({});
  const [phase, setPhase] = useState<QuizPhase>("playing");
  const [feedbacks, setFeedbacks] = useState<Record<string, AttemptFeedback>>({});
  const [gg, setGg] = useState<{ glows: string; grows: string } | null>(null);
  const [nextConceptId, setNextConceptId] = useState<string | null>(null);

  async function handleSubmit() {
    if (!items) return;
    setPhase("submitting");

    const activeProfile = profileId || profiles?.[0]?.id || "";

    const results = await Promise.all(
      items.map((item) =>
        recordAttempt.mutateAsync({
          profile_id: activeProfile,
          item_id: item.id,
          response: responses[item.id] ?? "",
          defer_glows_grows: true,
        }),
      ),
    );

    const fbMap: Record<string, AttemptFeedback> = {};
    items.forEach((item, i) => {
      fbMap[item.id] = results[i]!;
    });
    setFeedbacks(fbMap);

    const firstItem = items[0];
    if (firstItem?.quiz_id) {
      glowsGrows.mutate(
        { profile_id: activeProfile },
        {
          onSuccess: (data) => {
            setGg(data);
          },
        },
      );
    }

    if (firstItem?.concept_id) {
      const lessonId = `lesson_${firstItem.concept_id.split("_")[0] ?? ""}`;
      nextRec.mutate(
        { profile_id: activeProfile, lesson_id: lessonId },
        {
          onSuccess: (data) => {
            setNextConceptId(data.next_concept_id ?? null);
          },
        },
      );
    }

    setPhase("reviewing");
  }

  if (isLoading) return <p>Loading quiz…</p>;
  if (!items?.length) return <p>Quiz not found or has no items.</p>;

  const activeProfile = profileId || profiles?.[0]?.id || "";
  const score = phase === "reviewing"
    ? items.filter((item) => feedbacks[item.id]?.correct).length
    : 0;

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ marginTop: 0 }}>Quiz</h1>
      <p style={{ color: "#999" }}>
        {items.length} items · Profile: {activeProfile.slice(0, 12)}…
      </p>

      {phase === "playing" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSubmit();
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", marginBottom: "1.5rem" }}>
            {items.map((item, idx) => (
              <QuizItem
                key={item.id}
                item={item}
                index={idx}
                response={responses[item.id] ?? ""}
                onResponse={(v) => setResponses((r) => ({ ...r, [item.id]: v }))}
              />
            ))}
          </div>
          <button
            type="submit"
            style={{
              padding: "0.6rem 1.5rem",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            Submit Quiz
          </button>
        </form>
      )}

      {phase === "submitting" && <p>Scoring your answers…</p>}

      {phase === "reviewing" && (
        <div>
          <div
            style={{
              padding: "1rem",
              background: "#1e1e2e",
              borderRadius: 8,
              marginBottom: "1.5rem",
              display: "flex",
              gap: "2rem",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "2rem", fontWeight: "bold" }}>
                {score}/{items.length}
              </div>
              <div style={{ color: "#999" }}>Correct</div>
            </div>
            <div>
              <div style={{ fontSize: "1.25rem", color: score / items.length >= 0.7 ? "#4ade80" : "#f87171" }}>
                {Math.round((score / items.length) * 100)}%
              </div>
            </div>
          </div>

          {gg && (
            <div
              style={{
                background: "#1e1e2e",
                border: "1px solid #333",
                borderRadius: 8,
                padding: "1rem",
                marginBottom: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 0.75rem" }}>Glows &amp; Grows</h3>
              <div style={{ marginBottom: "0.5rem" }}>
                <strong style={{ color: "#4ade80" }}>Glows</strong>
                <p style={{ margin: "0.25rem 0 0", color: "#ccc" }}>{gg.glows}</p>
              </div>
              <div>
                <strong style={{ color: "#fbbf24" }}>Grows</strong>
                <p style={{ margin: "0.25rem 0 0", color: "#ccc" }}>{gg.grows}</p>
              </div>
            </div>
          )}

          {nextConceptId && (
            <div
              style={{
                background: "#1e1e2e",
                border: "1px solid #2563eb",
                borderRadius: 8,
                padding: "1rem",
                marginBottom: "1.5rem",
              }}
            >
              <strong>Recommended next:</strong>{" "}
              <a href={`/lessons?c=${nextConceptId}`} style={{ color: "#60a5fa" }}>
                {nextConceptId}
              </a>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {items.map((item, idx) => (
              <ReviewItem
                key={item.id}
                item={item}
                index={idx}
                response={responses[item.id] ?? ""}
                feedback={feedbacks[item.id]}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function QuizItem({
  item,
  index,
  response,
  onResponse,
}: {
  item: AssessmentItem;
  index: number;
  response: string;
  onResponse: (v: string) => void;
}) {
  return (
    <div style={{ background: "#1e1e2e", padding: "1rem", borderRadius: 8 }}>
      <p style={{ margin: "0 0 0.75rem", fontWeight: "bold" }}>
        {index + 1}. {item.prompt}
      </p>
      {item.options ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          {item.options.map((opt) => (
            <label key={opt} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <input
                type="radio"
                name={item.id}
                value={opt}
                checked={response === opt}
                onChange={() => onResponse(opt)}
              />
              {opt}
            </label>
          ))}
        </div>
      ) : (
        <textarea
          value={response}
          onChange={(e) => onResponse(e.target.value)}
          rows={3}
          style={{
            width: "100%",
            padding: "0.4rem",
            background: "#0f0f14",
            border: "1px solid #444",
            color: "#eee",
            borderRadius: 4,
            resize: "vertical",
          }}
        />
      )}
    </div>
  );
}

function ReviewItem({
  item,
  index,
  response,
  feedback,
}: {
  item: AssessmentItem;
  index: number;
  response: string;
  feedback?: AttemptFeedback;
}) {
  const correct = feedback?.correct;
  return (
    <div
      style={{
        background: "#1e1e2e",
        padding: "1rem",
        borderRadius: 8,
        borderLeft: `4px solid ${correct ? "#4ade80" : "#f87171"}`,
      }}
    >
      <p style={{ margin: "0 0 0.5rem", fontWeight: "bold" }}>
        {index + 1}. {item.prompt}
      </p>
      <p style={{ margin: "0 0 0.4rem", fontSize: "0.9rem" }}>
        Your answer: <strong>{response || "—"}</strong>
        {item.correct_answer && (
          <span style={{ marginLeft: "0.75rem", color: "#4ade80" }}>
            Correct: {item.correct_answer}
          </span>
        )}
      </p>
      {feedback?.rationale && (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "#999" }}>{feedback.rationale}</p>
      )}
    </div>
  );
}
