import { createFileRoute, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { lazy, Suspense, useState } from "react";
import {
  useLesson,
  useLessonItems,
  useLessonAssets,
  useLessonQuizzes,
} from "../api/hooks/useLessons";
import { useGenerateLesson } from "../api/hooks/useGenerate";
import { useGenerateQuiz, useBulkGenerate } from "../api/hooks/useQuizzes";
import { useProfiles } from "../api/hooks/useProfiles";
import { useJobEvents } from "../api/sse";
import AssetViewer from "../components/AssetViewer";
import type { ConceptNode, StoredDerivedAsset } from "../api/hooks/useLessons";
import { useSourceExcerpt } from "../api/hooks/useSources";

const ConceptGraph = lazy(() => import("../components/ConceptGraph"));

type SearchParams = { c?: string };

export const Route = createFileRoute("/lessons/$lessonId")({
  component: LessonWorkspace,
  validateSearch: (s: Record<string, unknown>): SearchParams => ({
    c: typeof s["c"] === "string" ? s["c"] : undefined,
  }),
});

const KINDS = ["relevel", "replace", "mnemonic"] as const;
type Kind = (typeof KINDS)[number];

function LessonWorkspace() {
  const { lessonId } = useParams({ from: "/lessons/$lessonId" });
  const search = useSearch({ from: "/lessons/$lessonId" });
  const navigate = useNavigate();
  const selectedId = search.c;

  const { data: graph, isLoading } = useLesson(lessonId);
  const { data: profiles } = useProfiles();
  const [profileId, setProfileId] = useState<string>("");
  const [kind, setKind] = useState<Kind>("relevel");
  const [jobId, setJobId] = useState<string | undefined>();
  const { state: jobState, done: jobDone } = useJobEvents(jobId);

  const generateLesson = useGenerateLesson(lessonId);
  const generateQuiz = useGenerateQuiz(lessonId);
  const bulkGenerate = useBulkGenerate(lessonId);

  const selectedConcept = graph?.concepts.find((c) => c.id === selectedId) ?? graph?.concepts[0];

  function handleSelectConcept(id: string) {
    void navigate({ search: { c: id } });
  }

  function handleGenerate() {
    if (!profileId || !selectedConcept) return;
    generateLesson.mutate(
      { concept_id: selectedConcept.id, profile_id: profileId, kind },
      { onSuccess: (r) => setJobId(r.job_id) },
    );
  }

  function handleGenerateQuiz() {
    if (!profileId) return;
    generateQuiz.mutate(
      { profile_id: profileId, scope: "lesson" },
      { onSuccess: (r) => setJobId(r.job_id) },
    );
  }

  function handleBulkGenerate() {
    if (!profileId) return;
    bulkGenerate.mutate(
      { profile_id: profileId, kinds: [...KINDS], skip_existing: true },
      { onSuccess: (r) => setJobId(r.job_id) },
    );
  }

  if (isLoading) return <p>Loading lesson…</p>;
  if (!graph) return <p>Lesson not found.</p>;

  const activeProfile = profileId || profiles?.[0]?.id || "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 3rem)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 220px", flex: 1, gap: 0, overflow: "hidden" }}>
        {/* Left: concept graph */}
        <div style={{ borderRight: "1px solid #333", overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "0.75rem", borderBottom: "1px solid #333" }}>
            <strong>{lessonId.slice(0, 16)}…</strong>
            <div style={{ color: "#999", fontSize: "0.8rem" }}>{graph.concepts.length} concepts</div>
          </div>
          <div style={{ flex: 1, position: "relative" }}>
            <Suspense fallback={<p style={{ padding: "1rem", color: "#666" }}>Loading graph…</p>}>
              <ConceptGraph
                concepts={graph.concepts}
                selectedId={selectedConcept?.id}
                onSelect={handleSelectConcept}
              />
            </Suspense>
          </div>
        </div>

        {/* Middle: concept detail */}
        <div style={{ overflow: "auto", padding: "1rem" }}>
          {selectedConcept ? (
            <ConceptDetail
              concept={selectedConcept}
              lessonId={lessonId}
              profileId={activeProfile}
              allConcepts={graph.concepts}
              onSelectConcept={handleSelectConcept}
            />
          ) : (
            <p style={{ color: "#666" }}>Select a concept.</p>
          )}
        </div>

        {/* Right: actions */}
        <div
          style={{
            borderLeft: "1px solid #333",
            padding: "0.75rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            overflow: "auto",
          }}
        >
          <strong>Actions</strong>

          <label style={{ fontSize: "0.8rem", color: "#999" }}>Profile</label>
          <select
            value={activeProfile}
            onChange={(e) => setProfileId(e.target.value)}
            style={{ padding: "0.3rem", background: "#1e1e2e", border: "1px solid #444", color: "#eee", borderRadius: 4 }}
          >
            {profiles?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.grade_level} ({p.id.slice(0, 8)}…)
              </option>
            ))}
          </select>

          <label style={{ fontSize: "0.8rem", color: "#999", marginTop: "0.25rem" }}>Modality</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as Kind)}
            style={{ padding: "0.3rem", background: "#1e1e2e", border: "1px solid #444", color: "#eee", borderRadius: 4 }}
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>

          <button
            onClick={handleGenerate}
            disabled={!activeProfile || generateLesson.isPending}
            style={{ padding: "0.4rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}
          >
            Generate
          </button>

          <button
            onClick={handleGenerateQuiz}
            disabled={!activeProfile || generateQuiz.isPending}
            style={{ padding: "0.4rem", background: "#059669", color: "#fff", border: "none", borderRadius: 4 }}
          >
            Generate Quiz
          </button>

          <button
            onClick={handleBulkGenerate}
            disabled={!activeProfile || bulkGenerate.isPending}
            style={{ padding: "0.4rem", background: "#7c3aed", color: "#fff", border: "none", borderRadius: 4 }}
          >
            Bulk Generate All
          </button>

          {jobId && (
            <div style={{ marginTop: "0.5rem" }}>
              <div style={{ background: "#333", borderRadius: 4, height: 6 }}>
                <div
                  style={{
                    background: "#2563eb",
                    width: `${Math.round(jobState.pct * 100)}%`,
                    height: "100%",
                    borderRadius: 4,
                    transition: "width 0.3s",
                  }}
                />
              </div>
              <p style={{ fontSize: "0.75rem", color: "#999", margin: "0.25rem 0 0" }}>
                {jobState.phase}
                {jobDone && (
                  <span style={{ color: jobState.status === "error" ? "#f87171" : "#4ade80" }}>
                    {" — "}
                    {jobState.status === "error" ? jobState.error : "done"}
                  </span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConceptDetail — tabbed panel
// ---------------------------------------------------------------------------

type ConceptDetailProps = {
  concept: ConceptNode;
  lessonId: string;
  profileId: string;
  allConcepts: ConceptNode[];
  onSelectConcept: (id: string) => void;
};

type Tab = "overview" | "spans" | "assets" | "items" | "quiz";

function ConceptDetail({ concept, lessonId, profileId, allConcepts, onSelectConcept }: ConceptDetailProps) {
  const [tab, setTab] = useState<Tab>("overview");
  const tabs: Tab[] = ["overview", "spans", "assets", "items", "quiz"];

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{concept.title}</h2>

      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid #333", marginBottom: "1rem" }}>
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "0.3rem 0.75rem",
              background: "none",
              border: "none",
              borderBottom: t === tab ? "2px solid #2563eb" : "2px solid transparent",
              color: t === tab ? "#fff" : "#999",
              cursor: "pointer",
              fontSize: "0.9rem",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <OverviewTab concept={concept} allConcepts={allConcepts} onSelectConcept={onSelectConcept} />
      )}
      {tab === "spans" && <SpansTab concept={concept} />}
      {tab === "assets" && <AssetsTab lessonId={lessonId} conceptId={concept.id} profileId={profileId} />}
      {tab === "items" && <ItemsTab lessonId={lessonId} conceptId={concept.id} />}
      {tab === "quiz" && <QuizTab lessonId={lessonId} />}
    </div>
  );
}

function OverviewTab({
  concept,
  allConcepts,
  onSelectConcept,
}: {
  concept: ConceptNode;
  allConcepts: ConceptNode[];
  onSelectConcept: (id: string) => void;
}) {
  const prereqConcepts = allConcepts.filter((c) => concept.prerequisites?.includes(c.id));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <Section label="Learning Objective">{concept.learning_objective}</Section>
      <Section label="Summary">{concept.summary}</Section>
      {concept.bloom_level && <Section label="Bloom Level">{concept.bloom_level}</Section>}
      {concept.temporal_position && (
        <Section label="Temporal Position">{concept.temporal_position}</Section>
      )}
      {prereqConcepts.length > 0 && (
        <Section label="Prerequisites">
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {prereqConcepts.map((p) => (
              <button
                key={p.id}
                onClick={() => onSelectConcept(p.id)}
                style={{
                  padding: "0.2rem 0.6rem",
                  background: "#1e1e2e",
                  border: "1px solid #555",
                  borderRadius: 4,
                  color: "#60a5fa",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
              >
                {p.title}
              </button>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function SpansTab({ concept }: { concept: ConceptNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {concept.source_spans.length === 0 && <p style={{ color: "#666" }}>No source spans.</p>}
      {concept.source_spans.map((span, i) => (
        <SpanExcerpt key={i} span={span} />
      ))}
    </div>
  );
}

type SourceSpan = {
  doc_id: string;
  char_start: number;
  char_end: number;
  page_start: number;
  page_end: number;
};

function SpanExcerpt({ span }: { span: SourceSpan }) {
  const { data: excerpt, isLoading } = useSourceExcerpt(span.doc_id, span.char_start, span.char_end);

  if (isLoading)
    return <div style={{ background: "#1e1e2e", padding: "0.5rem", borderRadius: 6, color: "#666" }}>Loading…</div>;

  const text = excerpt?.text ?? "";
  const relStart = span.char_start - (excerpt?.window_start ?? span.char_start);
  const relEnd = span.char_end - (excerpt?.window_start ?? span.char_start);

  return (
    <div style={{ background: "#1e1e2e", padding: "0.75rem", borderRadius: 6 }}>
      <div style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.4rem" }}>
        p.{span.page_start}–{span.page_end} ·{" "}
        <a
          href={`/sources/${span.doc_id}`}
          style={{ color: "#60a5fa" }}
        >
          {span.doc_id.slice(0, 12)}…
        </a>
      </div>
      <p style={{ margin: 0, fontSize: "0.85rem", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
        {text.slice(0, relStart)}
        <mark style={{ background: "#fbbf24", color: "#000" }}>
          {text.slice(relStart, relEnd)}
        </mark>
        {text.slice(relEnd)}
      </p>
    </div>
  );
}

function AssetsTab({
  lessonId,
  conceptId,
  profileId,
}: {
  lessonId: string;
  conceptId: string;
  profileId: string;
}) {
  const { data: assets, isLoading } = useLessonAssets(lessonId, { conceptId, profileId });
  const [expanded, setExpanded] = useState<string | null>(null);

  if (isLoading) return <p style={{ color: "#999" }}>Loading…</p>;
  if (!assets?.length) return <p style={{ color: "#666" }}>No assets yet. Generate one using the Actions panel.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {assets.map((asset: StoredDerivedAsset) => (
        <div key={asset.id} style={{ border: "1px solid #333", borderRadius: 6, overflow: "hidden" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "0.5rem 0.75rem",
              background: "#1e1e2e",
              cursor: "pointer",
            }}
            onClick={() => setExpanded(expanded === asset.id ? null : asset.id)}
          >
            <span>
              <strong>{asset.kind}</strong>{" "}
              <span style={{ color: "#999", fontSize: "0.8rem" }}>{asset.created_at.slice(0, 10)}</span>
            </span>
            <span style={{ color: "#666" }}>{expanded === asset.id ? "▲" : "▼"}</span>
          </div>
          {expanded === asset.id && (
            <div style={{ padding: "0.75rem" }}>
              <AssetViewer asset={asset} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ItemsTab({ lessonId, conceptId }: { lessonId: string; conceptId: string }) {
  const { data: items, isLoading } = useLessonItems(lessonId, { conceptId });

  if (isLoading) return <p style={{ color: "#999" }}>Loading…</p>;
  if (!items?.length) return <p style={{ color: "#666" }}>No assessment items yet.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {items.map((item) => (
        <div key={item.id} style={{ background: "#1e1e2e", padding: "0.75rem", borderRadius: 6 }}>
          <p style={{ margin: "0 0 0.5rem", fontWeight: "bold" }}>{item.prompt}</p>
          {item.options && (
            <ul style={{ margin: "0 0 0.5rem", paddingLeft: "1.25rem" }}>
              {item.options.map((opt, i) => (
                <li key={i} style={{ color: opt === item.correct_answer ? "#4ade80" : "#ccc" }}>
                  {opt}
                </li>
              ))}
            </ul>
          )}
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#999" }}>
            {item.rationale}
          </p>
        </div>
      ))}
    </div>
  );
}

function QuizTab({ lessonId }: { lessonId: string }) {
  const { data: quizzes, isLoading } = useLessonQuizzes(lessonId);

  if (isLoading) return <p style={{ color: "#999" }}>Loading…</p>;

  return (
    <div>
      {!quizzes?.length && <p style={{ color: "#666" }}>No quizzes yet. Use "Generate Quiz" in the Actions panel.</p>}
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {quizzes?.map((q) => (
          <li key={q.quiz_id}>
            <a href={`/quizzes/${q.quiz_id}`} style={{ color: "#60a5fa" }}>
              {q.quiz_id.slice(0, 12)}… ({q.item_count} items)
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.25rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
      <div style={{ fontSize: "0.9rem" }}>{children}</div>
    </div>
  );
}
