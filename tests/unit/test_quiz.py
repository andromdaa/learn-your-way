"""Unit tests for SectionQuizGenerator — MCQGenerator and ModelClient mocked."""

from __future__ import annotations

import dataclasses
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from syrupy.assertion import SnapshotAssertion

from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.assessment.mcq import MCQGenerator
from lyw_core.assessment.quiz import GlowsGrows, SectionQuizGenerator
from lyw_core.db.dao import AttemptRecord


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=500
    )


def _concept(cid: str, title: str) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=f"Summary for {title}.",
        learning_objective=f"Understand {title}.",
        source_spans=[_span()],
    )


def _assessment_item(iid: str, cid: str, prompt: str) -> AssessmentItem:
    return AssessmentItem(
        id=iid,
        kind="mcq",
        prompt=prompt,
        rationale="Test rationale.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id=cid,
        correct_answer="Option A",
        bloom_level="understand",
    )


def _make_sqg(
    mcq_gen: MCQGenerator | MagicMock,
    model_client: Any = None,
) -> SectionQuizGenerator:
    if model_client is None:
        model_client = AsyncMock()
    return SectionQuizGenerator(
        mcq_generator=mcq_gen,
        model_client=model_client,
        dao=MagicMock(),
    )


# ---------------------------------------------------------------------------
# generate(): collects items per concept
# ---------------------------------------------------------------------------


async def test_section_quiz_collects_items_per_concept(
    snapshot: SnapshotAssertion,
) -> None:
    """3 concepts x 2 items each = 6 total; MCQGenerator called once per concept."""
    concepts = [
        _concept("c1", "Photosynthesis"),
        _concept("c2", "Cell Wall"),
        _concept("c3", "Mitochondria"),
    ]
    graph = LessonGraph(id="g1", source_id="doc-1", concepts=concepts)

    items_per_concept = {
        "c1": [
            _assessment_item("i1a", "c1", "Q1a"),
            _assessment_item("i1b", "c1", "Q1b"),
        ],
        "c2": [
            _assessment_item("i2a", "c2", "Q2a"),
            _assessment_item("i2b", "c2", "Q2b"),
        ],
        "c3": [
            _assessment_item("i3a", "c3", "Q3a"),
            _assessment_item("i3b", "c3", "Q3b"),
        ],
    }

    async def fake_generate(
        concept: ConceptNode, lg: LessonGraph
    ) -> list[AssessmentItem]:
        return items_per_concept[concept.id]

    mcq_gen = MagicMock(spec=MCQGenerator)
    mcq_gen.generate = AsyncMock(side_effect=fake_generate)
    dao = MagicMock()

    sqg = SectionQuizGenerator(
        mcq_generator=mcq_gen,
        model_client=AsyncMock(),
        dao=dao,
    )
    items = await sqg.generate(concepts, graph)

    assert len(items) == 6
    assert mcq_gen.generate.await_count == 3
    dao.add_assessment_item.assert_not_called()
    assert snapshot == [item.model_dump() for item in items]


async def test_section_quiz_generate_empty_concepts_returns_empty() -> None:
    mcq_gen = MagicMock(spec=MCQGenerator)
    mcq_gen.generate = AsyncMock(return_value=[])
    graph = LessonGraph(id="g1", source_id="doc-1", concepts=[])
    sqg = _make_sqg(mcq_gen)
    items = await sqg.generate([], graph)
    assert items == []
    mcq_gen.generate.assert_not_called()


async def test_section_quiz_generate_single_concept() -> None:
    concept = _concept("c1", "Photosynthesis")
    graph = LessonGraph(id="g1", source_id="doc-1", concepts=[concept])
    expected = [_assessment_item("i1", "c1", "Q1")]

    mcq_gen = MagicMock(spec=MCQGenerator)
    mcq_gen.generate = AsyncMock(return_value=expected)
    sqg = _make_sqg(mcq_gen)

    items = await sqg.generate([concept], graph)
    assert items == expected


# ---------------------------------------------------------------------------
# generate_glows_grows(): parses model response
# ---------------------------------------------------------------------------


async def test_section_quiz_generates_glows_grows(
    snapshot: SnapshotAssertion,
) -> None:
    items = [_assessment_item("i1", "c1", "Q1")]
    attempts = [
        AttemptRecord(
            id="a1",
            profile_id="p1",
            item_id="i1",
            response="Option A",
            correct=True,
            attempted_at="2026-04-30T00:00:00Z",
        )
    ]

    model_client = AsyncMock()
    model_client.complete = AsyncMock(
        return_value=json.dumps(
            {
                "glows": "You showed great understanding!",
                "grows": "Focus on applying concepts.",
            }
        )
    )

    sqg = _make_sqg(MagicMock(spec=MCQGenerator), model_client)
    result = await sqg.generate_glows_grows(items, attempts)

    assert isinstance(result, GlowsGrows)
    assert result.glows == "You showed great understanding!"
    assert result.grows == "Focus on applying concepts."
    assert snapshot == dataclasses.asdict(result)


async def test_glows_grows_invalid_json_returns_empty() -> None:
    model_client = AsyncMock()
    model_client.complete = AsyncMock(return_value="not json at all")
    sqg = _make_sqg(MagicMock(spec=MCQGenerator), model_client)
    result = await sqg.generate_glows_grows([], [])
    assert result == GlowsGrows(glows="", grows="")


async def test_glows_grows_missing_grows_key_returns_empty() -> None:
    model_client = AsyncMock()
    model_client.complete = AsyncMock(return_value='{"glows": "Good job"}')
    sqg = _make_sqg(MagicMock(spec=MCQGenerator), model_client)
    result = await sqg.generate_glows_grows([], [])
    assert result == GlowsGrows(glows="", grows="")


async def test_glows_grows_non_dict_response_returns_empty() -> None:
    model_client = AsyncMock()
    model_client.complete = AsyncMock(return_value='["glows", "grows"]')
    sqg = _make_sqg(MagicMock(spec=MCQGenerator), model_client)
    result = await sqg.generate_glows_grows([], [])
    assert result == GlowsGrows(glows="", grows="")


async def test_glows_grows_non_string_values_returns_empty() -> None:
    model_client = AsyncMock()
    model_client.complete = AsyncMock(
        return_value=json.dumps({"glows": 42, "grows": None})
    )
    sqg = _make_sqg(MagicMock(spec=MCQGenerator), model_client)
    result = await sqg.generate_glows_grows([], [])
    assert result == GlowsGrows(glows="", grows="")


# ---------------------------------------------------------------------------
# quiz_id threading (T0c-r3)
# ---------------------------------------------------------------------------


async def test_section_quiz_generate_threads_quiz_id_to_all_items() -> None:
    """When quiz_id is supplied, all returned items carry it."""
    concept = _concept("c1", "Photosynthesis")
    graph = LessonGraph(id="g1", source_id="doc-1", concepts=[concept])

    items_without_quiz_id = [
        _assessment_item("i1", "c1", "Q1"),
        _assessment_item("i2", "c1", "Q2"),
    ]

    async def fake_generate(
        concept: ConceptNode, lg: LessonGraph, *, quiz_id: str | None = None
    ) -> list[AssessmentItem]:
        # Simulate MCQGenerator stamping quiz_id onto returned items
        return [item.model_copy(update={"quiz_id": quiz_id}) for item in items_without_quiz_id]

    mcq_gen = MagicMock(spec=MCQGenerator)
    mcq_gen.generate = AsyncMock(side_effect=fake_generate)

    sqg = _make_sqg(mcq_gen)
    items = await sqg.generate([concept], graph, quiz_id="quiz-xyz")

    assert all(item.quiz_id == "quiz-xyz" for item in items)
    # verify quiz_id was forwarded to MCQGenerator
    call_kwargs = mcq_gen.generate.call_args_list[0].kwargs
    assert call_kwargs.get("quiz_id") == "quiz-xyz"


async def test_section_quiz_generate_without_quiz_id_preserves_none() -> None:
    """When quiz_id is not supplied (default None), items retain quiz_id=None."""
    concept = _concept("c1", "Photosynthesis")
    graph = LessonGraph(id="g1", source_id="doc-1", concepts=[concept])

    async def fake_generate(
        concept: ConceptNode, lg: LessonGraph, *, quiz_id: str | None = None
    ) -> list[AssessmentItem]:
        return [_assessment_item("i1", "c1", "Q1")]

    mcq_gen = MagicMock(spec=MCQGenerator)
    mcq_gen.generate = AsyncMock(side_effect=fake_generate)

    sqg = _make_sqg(mcq_gen)
    items = await sqg.generate([concept], graph)

    assert all(item.quiz_id is None for item in items)
    call_kwargs = mcq_gen.generate.call_args_list[0].kwargs
    assert call_kwargs.get("quiz_id") is None
