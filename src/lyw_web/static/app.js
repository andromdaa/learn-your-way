// Learn Your Way — test harness JS
// Handles: PDF upload + ingest poll, profile create, generate + poll + asset render.

function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = `status-bar ${type}`;
  el.hidden = !msg;
}

function splitCsv(str) {
  return str.split(",").map(s => s.trim()).filter(Boolean);
}

// ----- Ingest ----------------------------------------------------------------

const uploadForm = document.getElementById("upload-form");
if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusEl = document.getElementById("ingest-status");
    const file = document.getElementById("pdf-file").files[0];
    const title = document.getElementById("pdf-title").value.trim();

    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);

    setStatus(statusEl, "Uploading…", "info");
    let sourceId;
    try {
      const r = await fetch("/sources", { method: "POST", body: fd });
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
      const data = await r.json();
      sourceId = data.id;
    } catch (err) {
      setStatus(statusEl, String(err), "error");
      return;
    }

    const lessonId = "lesson_" + sourceId;
    setStatus(statusEl, `Ingesting… polling for ${lessonId}`, "info");
    let attempt = 0;
    const timer = setInterval(async () => {
      attempt++;
      if (attempt > 120) {
        clearInterval(timer);
        setStatus(statusEl, "Timed out waiting for ingest to complete.", "error");
        return;
      }
      try {
        const r = await fetch(`/lessons/${lessonId}`);
        if (r.ok) {
          clearInterval(timer);
          setStatus(statusEl, `Ingest complete — ${lessonId}`, "ok");
          setTimeout(() => location.reload(), 800);
        } else if (r.status !== 404) {
          clearInterval(timer);
          setStatus(statusEl, `Unexpected status ${r.status}`, "error");
        }
        // 404 → keep polling
      } catch {
        // network error → keep polling
      }
    }, 2000);
  });
}

// ----- Profile create --------------------------------------------------------

const profileForm = document.getElementById("profile-form");
if (profileForm) {
  profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusEl = document.getElementById("profile-status");
    const fd = new FormData(profileForm);
    const body = {
      grade_level: fd.get("grade_level"),
      interests: splitCsv(fd.get("interests") || ""),
      goals: splitCsv(fd.get("goals") || ""),
    };
    setStatus(statusEl, "Creating…", "info");
    try {
      const r = await fetch("/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`Create failed: ${r.status}`);
      setStatus(statusEl, "Profile created.", "ok");
      setTimeout(() => location.reload(), 600);
    } catch (err) {
      setStatus(statusEl, String(err), "error");
    }
  });
}

// ----- Generate + poll -------------------------------------------------------

const generateForm = document.getElementById("generate-form");
if (generateForm) {
  const lessonId = generateForm.dataset.lessonId;
  const kindSelect = document.getElementById("kind-select");
  const conceptLabel = document.getElementById("concept-label");
  const conceptSelect = document.getElementById("concept-select");
  const lessonScopedKinds = new Set(["mind_map", "timeline", "slides"]);

  function updateConceptVisibility() {
    const isLessonScoped = lessonScopedKinds.has(kindSelect.value);
    conceptLabel.style.opacity = isLessonScoped ? "0.4" : "1";
    conceptSelect.disabled = isLessonScoped;
    if (isLessonScoped) conceptSelect.value = "__lesson__";
  }
  kindSelect.addEventListener("change", updateConceptVisibility);
  updateConceptVisibility();

  generateForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusEl = document.getElementById("generate-status");
    const viewerEl = document.getElementById("asset-viewer");
    const fd = new FormData(generateForm);
    const body = {
      concept_id: fd.get("concept_id"),
      profile_id: fd.get("profile_id"),
      kind: fd.get("kind"),
    };
    setStatus(statusEl, "Queuing job…", "info");
    viewerEl.hidden = true;
    viewerEl.innerHTML = "";

    let jobId;
    try {
      const r = await fetch(`/lessons/${lessonId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        throw new Error(`${r.status}: ${detail.detail || r.statusText}`);
      }
      const data = await r.json();
      jobId = data.job_id;
    } catch (err) {
      setStatus(statusEl, String(err), "error");
      return;
    }

    setStatus(statusEl, `Job ${jobId} — polling…`, "info");
    let attempt = 0;
    const timer = setInterval(async () => {
      attempt++;
      if (attempt > 120) {
        clearInterval(timer);
        setStatus(statusEl, "Timed out waiting for job.", "error");
        return;
      }
      try {
        const r = await fetch(`/lessons/${lessonId}/generate/${jobId}`);
        if (!r.ok) { clearInterval(timer); setStatus(statusEl, `Poll error ${r.status}`, "error"); return; }
        const data = await r.json();
        if (data.status === "complete") {
          clearInterval(timer);
          if (data.result?.skipped) {
            setStatus(statusEl, `Skipped: ${data.result.reason}`, "info");
          } else {
            setStatus(statusEl, "Done — rendering asset…", "ok");
            await renderAsset(data.result.asset_id, viewerEl, body.kind);
            setTimeout(() => location.reload(), 1200);
          }
        } else if (data.status === "not_found") {
          clearInterval(timer);
          setStatus(statusEl, "Job not found.", "error");
        }
        // pending → keep polling
      } catch {
        // network error → keep polling
      }
    }, 1500);
  });
}

// ----- Existing asset view buttons ------------------------------------------

document.querySelectorAll(".view-asset").forEach(btn => {
  btn.addEventListener("click", async () => {
    const assetId = btn.dataset.assetId;
    const viewerRow = document.getElementById(`viewer-${assetId}`);
    const contentEl = document.getElementById(`content-${assetId}`);
    if (!viewerRow.hidden) { viewerRow.hidden = true; return; }
    viewerRow.hidden = false;
    contentEl.textContent = "Loading…";
    const row = btn.closest("tr");
    const kindBadge = row.querySelector(".kind-badge");
    const kind = kindBadge ? kindBadge.textContent.trim() : "";
    await renderAsset(assetId, contentEl, kind);
  });
});

// ----- Asset render ----------------------------------------------------------

async function renderAsset(assetId, container, kind) {
  try {
    const r = await fetch(`/v1/assets/${assetId}`);
    if (!r.ok) { container.textContent = `Error fetching asset: ${r.status}`; return; }
    const ct = r.headers.get("content-type") || "";
    const body = await r.text();
    if (ct.includes("application/json")) {
      renderSlides(JSON.parse(body), container);
    } else if (body.trimStart().startsWith("flowchart") || body.trimStart().startsWith("timeline")) {
      await renderMermaid(body, container);
    } else {
      container.innerHTML = `<pre>${escHtml(body)}</pre>`;
    }
    container.hidden = false;
  } catch (err) {
    container.textContent = String(err);
  }
}

async function renderMermaid(src, container) {
  try {
    const id = "mmd-" + Math.random().toString(36).slice(2);
    const { svg } = await window.mermaid.render(id, src);
    container.innerHTML = `<div class="mermaid">${svg}</div>`;
  } catch (err) {
    container.innerHTML = `<pre>${escHtml(src)}</pre><p style="color:red;font-size:.8rem">${escHtml(String(err))}</p>`;
  }
}

function renderSlides(deck, container) {
  if (!deck.slides || !deck.slides.length) {
    container.textContent = "Empty slide deck.";
    return;
  }
  container.innerHTML = deck.slides.map(slide => `
    <article class="slide">
      <h2>${escHtml(slide.title || "")}</h2>
      <p>${escHtml(slide.body || "")}</p>
      ${slide.speaker_notes ? `<details><summary>Speaker notes</summary><p>${escHtml(slide.speaker_notes)}</p></details>` : ""}
      ${(slide.source_spans || []).map(s => `<span class="source-badge">${escHtml(s.doc_id)}:${s.page_start}</span>`).join("")}
    </article>
  `).join("");
}

function escHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
