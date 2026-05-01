# 00 — Goals and non-goals

## What we are building

A self-hosted, single-user system that replicates the text
personalization features of Google's Learn Your Way. It turns a source PDF
(textbook chapter, course reading, technical document) into a
personalized study experience while preserving source fidelity.

The system is structured as a personalization pipeline:

1. **Personalization**: source text is re-leveled to the learner's
   grade and selectively rewritten to use examples tied to the
   learner's interests.

Personalization is grounded in a canonical lesson graph, never
directly from the raw PDF.

## Modalities in scope

- Immersive text (re-leveled, interest-personalized)

## Modalities out of scope

- Audio lessons of any kind
- Slide narration / TTS
- Generated illustrations (deferred; reliable educational image
  generation requires a fine-tuned domain model and a verifier layer)

## What we are NOT building

- A general chatbot. The product is a personalized text learning tool,
  not a single-turn Q&A surface.
- A multi-user platform. This is a single-user self-hosted tool.
- A web search tool. Personalization is grounded in user-provided source
  documents only.
- A monolithic prompt-driven app. Personalization operates over the
  shared lesson graph with independent re-leveling and replacement
  generators.
- A recommender platform in v1. Personalization is explicit-profile
  based. Sequencing models or contextual bandits are out of scope
  until v2.

## Audience

A single self-learner running the system on their own machine or
homelab. The deployment shape is one process (or a small docker
compose), one user, one data directory.

## Success criteria

Phase 1 is successful when an OpenStax sample chapter parses into a
lesson graph in which 100% of `ConceptNode.source_spans` resolve to
valid offsets in the source PDF, and the inspection CLI shows a
coherent concept tree.

Phase 2 is successful when text personalization (re-leveling and
interest-based replacement) is diffable against source and learner
profiles can be created and applied to personalize content.
