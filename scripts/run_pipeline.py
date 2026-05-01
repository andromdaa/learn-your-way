#!/usr/bin/env python3
"""End-to-end pipeline: ingest PDF → create profile → generate replace text.

Prerequisites:
    docker compose up -d        # Redis, Qdrant, Ollama
    ollama pull gemma3:4b       # if not already cached

Usage:
    uv run python scripts/run_pipeline.py [--pdf PATH] [--concepts first|all|N]

chapter.pdf is expected at the repo root by default.  Copy any chapter PDF
there before running, e.g.:
    cp tests/fixtures/openstax_chapter.pdf chapter.pdf
"""

from __future__ import annotations

import argparse
import subprocess
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

_BASE = "http://localhost:8000"
_API_READY_TIMEOUT = 30
_INGEST_TIMEOUT = 300  # seconds — Docling parse can be slow first run
_GEN_TIMEOUT = 180  # seconds per concept


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _tcp_ok(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3.0):
            return True
    except OSError:
        return False


def _select_concepts(concepts: list[dict], spec: str) -> list[dict]:
    if spec == "first":
        return concepts[:1]
    if spec == "all":
        return concepts
    try:
        n = int(spec)
        return concepts[:n]
    except ValueError:
        sys.exit(f"--concepts must be 'first', 'all', or an integer; got: {spec!r}")


def _preflight(pdf: Path, redis_url: str, ollama_url: str) -> None:
    if not pdf.exists():
        sys.exit(
            f"PDF not found: {pdf}\n"
            "  Place chapter.pdf in the repo root, or pass --pdf <path>."
        )

    parsed = urlparse(redis_url)
    redis_host = parsed.hostname or "localhost"
    redis_port = parsed.port or 6379
    if not _tcp_ok(redis_host, redis_port):
        sys.exit(
            f"Redis unreachable at {redis_host}:{redis_port}\n"
            "  Is `docker compose up -d` running?"
        )

    if not _tcp_ok("localhost", 6333):
        sys.exit(
            "Qdrant unreachable at localhost:6333\n  Is `docker compose up -d` running?"
        )

    try:
        httpx.get(f"{ollama_url}/api/tags", timeout=5).raise_for_status()
    except Exception:
        sys.exit(
            f"Ollama unreachable at {ollama_url}\n  Is `docker compose up -d` running?"
        )

    print(f"[preflight] PDF found; Redis, Qdrant, Ollama reachable")


def _wait_api_ready(client: httpx.Client) -> None:
    deadline = time.monotonic() + _API_READY_TIMEOUT
    print("[boot] Waiting for API …", end="", flush=True)
    while time.monotonic() < deadline:
        try:
            r = client.get(f"{_BASE}/lessons/__readiness__", timeout=2)
            if r.status_code in (200, 404, 422):
                print(" ready")
                return
        except httpx.RequestError:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    sys.exit(f"\nAPI did not become ready within {_API_READY_TIMEOUT}s")


def _poll_lesson(client: httpx.Client, lesson_id: str) -> dict:
    deadline = time.monotonic() + _INGEST_TIMEOUT
    print(f"[ingest] Waiting for lesson {lesson_id} …", end="", flush=True)
    while time.monotonic() < deadline:
        r = client.get(f"{_BASE}/lessons/{lesson_id}", timeout=10)
        if r.status_code == 200:
            print(" done")
            return r.json()
        print(".", end="", flush=True)
        time.sleep(2)
    sys.exit(f"\nIngest timed out after {_INGEST_TIMEOUT}s")


def _generate_concept(
    client: httpx.Client, lesson_id: str, concept: dict, profile_id: str
) -> str:
    cid = concept["id"]
    title = concept.get("title", cid)

    r = client.post(
        f"{_BASE}/lessons/{lesson_id}/generate",
        json={"concept_id": cid, "profile_id": profile_id, "kind": "replace"},
        timeout=15,
    )
    r.raise_for_status()
    job_id = r.json()["job_id"]
    print(f"[generate] '{title}' → job {job_id}", end="", flush=True)

    deadline = time.monotonic() + _GEN_TIMEOUT
    while time.monotonic() < deadline:
        poll = client.get(f"{_BASE}/lessons/{lesson_id}/generate/{job_id}", timeout=10)
        poll.raise_for_status()
        data = poll.json()
        if data["status"] == "complete":
            print(" done")
            asset_id = data["result"]["asset_id"]
            text_r = client.get(f"{_BASE}/v1/assets/{asset_id}", timeout=10)
            text_r.raise_for_status()
            return text_r.text
        if data["status"] == "not_found":
            sys.exit(f"\nJob {job_id} not found — did the worker start correctly?")
        print(".", end="", flush=True)
        time.sleep(2)
    sys.exit(f"\nGenerate timed out after {_GEN_TIMEOUT}s for concept {cid!r}")


def _teardown(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
    grace_until = time.monotonic() + 5
    for proc in procs:
        remaining = max(0.0, grace_until - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("chapter.pdf"),
        help="Path to the PDF to ingest (default: ./chapter.pdf)",
    )
    parser.add_argument(
        "--concepts",
        default="first",
        metavar="first|all|N",
        help="How many concepts to generate text for (default: first)",
    )
    args = parser.parse_args()

    redis_url = "redis://localhost:6379/0"
    ollama_url = "http://localhost:11434"
    data_dir = Path("./data")
    db_path = Path("./data/lyw.db")
    try:
        from lyw_core.settings import Settings

        s = Settings()
        redis_url = str(s.redis_url)
        ollama_url = str(s.ollama_base_url)
        data_dir = Path(s.data_dir)
        db_path = Path(s.db_path)
    except Exception:
        pass

    _preflight(args.pdf, redis_url, ollama_url)

    # Pre-create data dir so the worker's SQLite connect doesn't race the API's
    # DataDir.bootstrap() at lifespan startup.
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    procs: list[subprocess.Popen] = []
    try:
        # uvicorn is not a project dependency, so resolve it on the fly via `uv run --with uvicorn`.
        procs.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "--with",
                    "uvicorn",
                    "uvicorn",
                    "lyw_core.api.app:app",
                    "--port",
                    "8000",
                ]
            )
        )
        procs.append(
            subprocess.Popen(
                [sys.executable, "-m", "arq", "lyw_core.worker.settings.WorkerSettings"]
            )
        )
        print(f"[boot] uvicorn PID {procs[0].pid}, arq PID {procs[1].pid}")

        with httpx.Client() as client:
            _wait_api_ready(client)

            # Ingest
            pdf_bytes = args.pdf.read_bytes()
            print(f"[ingest] Uploading {args.pdf} ({len(pdf_bytes):,} bytes) …")
            r = client.post(
                f"{_BASE}/sources",
                files={"file": (args.pdf.name, pdf_bytes, "application/pdf")},
                data={"title": args.pdf.stem},
                timeout=30,
            )
            r.raise_for_status()
            doc_id = r.json()["id"]
            lesson_id = f"lesson_{doc_id}"

            graph = _poll_lesson(client, lesson_id)
            concepts: list[dict] = graph.get("concepts", [])
            print(f"[ingest] Complete — {len(concepts)} concept(s) found")

            if not concepts:
                sys.exit(
                    "No concepts extracted from PDF — check the Docling parse logs above."
                )

            # Create learner profile
            pr = client.post(
                f"{_BASE}/profiles",
                json={
                    "grade_level": "undergraduate",
                    "interests": ["space exploration"],
                    "goals": ["pass the midterm"],
                },
                timeout=10,
            )
            pr.raise_for_status()
            profile_id = pr.json()["id"]
            print(f"[profile] Created profile {profile_id}")

            # Generate replace text
            selected = _select_concepts(concepts, args.concepts)
            print(
                f"[generate] Generating replace text for {len(selected)} of {len(concepts)} concept(s) …"
            )
            for concept in selected:
                text = _generate_concept(client, lesson_id, concept, profile_id)
                title = concept.get("title", concept["id"])
                print(f"\n{'=' * 60}")
                print(f"concept: {title}")
                print(f"id:      {concept['id']}")
                print("=" * 60)
                print(text)

        print("\n[done] Pipeline complete.")

    finally:
        print("\n[teardown] Stopping API and worker …")
        _teardown(procs)
        print("[teardown] Done")


if __name__ == "__main__":
    main()
