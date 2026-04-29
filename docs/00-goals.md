# 00 — Goals and non-goals

## What we are building

A self-hosted, single-user system that replicates the text and visual
feature set of Google's Learn Your Way. It turns a source PDF
(textbook chapter, course reading, technical document) into a
personalized, multimodal, assessment-driven study experience while
preserving source fidelity.

The system is structured as a two-stage pedagogical transformation
pipeline:

1. **Personalization**: source text is re-leveled to the learner's
   grade and selectively rewritten to use examples tied to the
   learner's interests.
2. **Modality generation**: the personalized text becomes the basis
   for immersive text, slides, mind maps, timelines, and embedded
   assessment.

All modalities are generated from a canonical lesson graph, never
directly from the raw PDF.

## Modalities in scope

- Immersive text (re-leveled, interest-personalized)
- Slides (text + speaker notes; no narration)
- Mind maps
- Timelines
- Embedded multiple-choice questions
- Section-level quizzes with rationale and "Glows" / "Grows" feedback
- Mnemonic memory aids

## Modalities out of scope

- Audio lessons of any kind
- Slide narration / TTS
- Generated illustrations (deferred; reliable educational image
  generation requires a fine-tuned domain model and a verifier layer)

## What we are NOT building

- A general chatbot. The product is a guided study environment with
  modality switching, not a single-turn Q&A surface.
- A multi-user platform. This is a single-user self-hosted tool.
- A web search tool. Generation is grounded in user-provided source
  documents only.
- A monolithic prompt-driven app. Each modality has its own generator
  and validator working over the shared lesson graph.
- A recommender platform in v1. Personalization is explicit-profile
  plus quiz-feedback. Sequencing models or contextual bandits are out
  of scope until v2.

## Audience

A single self-learner running the system on their own machine or
homelab. The deployment shape is one process (or a small docker
compose), one user, one data directory.

## Success criteria

Phase 1 is successful when an OpenStax sample chapter parses into a
lesson graph in which 100% of `ConceptNode.source_spans` resolve to
valid offsets in the source PDF, and the inspection CLI shows a
coherent concept tree.

Phase 2 is successful when text personalization is diffable against
source, embedded questions and section quizzes are produced with
rationale and citation, and quiz feedback steers the learner back to
weak sections.

Phase 3 is successful when slides, mind maps, and timelines can be
generated from the lesson graph with the same source-span guarantees,
and asynchronous generation does not block interactive paths.
