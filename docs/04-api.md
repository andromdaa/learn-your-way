# 04 — API surface

The first-party API surface. The OpenAPI 3.1 stub below is the
authoritative specification; route handlers should be scaffolded from
it.

## Endpoints

- `POST /sources` — upload and parse a source document.
- `POST /profiles` — create or update an explicit learner profile.
- `POST /lessons/{id}/generate` — kick off a modality generation job.
- `GET /lessons/{id}` — retrieve the canonical lesson graph.
- `POST /attempts` — record a quiz attempt and return feedback.
- `POST /recommendations/next` — get next-step guidance.

## OpenAPI 3.1 stub

```yaml
openapi: 3.1.0
info:
  title: Learn Your Way OSS API
  version: 0.1.0
  description: |
    First-party API for the self-hosted Learn Your Way replica.
    All generation paths are grounded in source documents and the
    canonical lesson graph.

servers:
  - url: http://localhost:8000/v1

paths:
  /sources:
    post:
      summary: Upload and parse a source document
      operationId: createSource
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                title:
                  type: string
              required: [file]
      responses:
        '202':
          description: Accepted; parsing in progress
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Source'

  /profiles:
    post:
      summary: Create or update a learner profile
      operationId: upsertProfile
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LearnerProfile'
      responses:
        '200':
          description: Profile saved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LearnerProfile'

  /lessons/{id}:
    get:
      summary: Retrieve the canonical lesson graph
      operationId: getLesson
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Lesson graph
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LessonGraph'

  /lessons/{id}/generate:
    post:
      summary: Generate a modality asset from the lesson
      operationId: generateAsset
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                modality:
                  type: string
                  enum:
                    - immersive_text
                    - slides
                    - mind_map
                    - timeline
                profile_id:
                  type: string
              required: [modality, profile_id]
      responses:
        '202':
          description: Generation job accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  asset_id:
                    type: string

  /attempts:
    post:
      summary: Record a quiz attempt and return feedback
      operationId: recordAttempt
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AttemptRequest'
      responses:
        '200':
          description: Attempt recorded with feedback
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AttemptFeedback'

  /recommendations/next:
    post:
      summary: Get next-step guidance for the learner
      operationId: nextRecommendation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                profile_id:
                  type: string
                lesson_id:
                  type: string
              required: [profile_id, lesson_id]
      responses:
        '200':
          description: Next-step guidance
          content:
            application/json:
              schema:
                type: object
                properties:
                  next_concept_id:
                    type: string
                  reason:
                    type: string

components:
  schemas:
    Source:
      type: object
      properties:
        id: { type: string }
        title: { type: string }
        status:
          type: string
          enum: [parsing, ready, failed]

    LearnerProfile:
      type: object
      properties:
        id: { type: string }
        grade_level: { type: string }
        interests:
          type: array
          items: { type: string }
        goals:
          type: array
          items: { type: string }
      required: [grade_level]

    SourceSpan:
      type: object
      properties:
        doc_id: { type: string }
        page_start: { type: integer }
        page_end: { type: integer }
        char_start: { type: integer }
        char_end: { type: integer }
      required:
        - doc_id
        - page_start
        - page_end
        - char_start
        - char_end

    ConceptNode:
      type: object
      properties:
        id: { type: string }
        title: { type: string }
        summary: { type: string }
        learning_objective: { type: string }
        source_spans:
          type: array
          items: { $ref: '#/components/schemas/SourceSpan' }
        prerequisites:
          type: array
          items: { type: string }
        provenance:
          type: string
          enum: [heuristic, llm_refined]
          default: heuristic
        temporal_position:
          type: integer
          nullable: true
          default: null
          description: >
            Integer ordering rank for chronologically structured content.
            Null means the concept has no temporal position (unordered or
            not applicable). Used by the timeline generator; if all
            concepts in a lesson have null temporal_position the timeline
            generator skips that lesson. Negative values are valid.

    LessonGraph:
      type: object
      properties:
        id: { type: string }
        source_id: { type: string }
        concepts:
          type: array
          items: { $ref: '#/components/schemas/ConceptNode' }

    AttemptRequest:
      type: object
      properties:
        profile_id: { type: string }
        item_id: { type: string }
        response: { type: string }
      required: [profile_id, item_id, response]

    AttemptFeedback:
      type: object
      properties:
        correct: { type: boolean }
        rationale: { type: string }
        source_spans:
          type: array
          items: { $ref: '#/components/schemas/SourceSpan' }
        suggested_next_concept_id:
          type: string
```

## Notes

- Generation is asynchronous. `POST /lessons/{id}/generate` returns
  202 with a `job_id` and the eventual `asset_id`. The client polls
  for completion or the UI subscribes via a websocket (added in phase
  3 if needed).
- `POST /recommendations/next` is the public surface of the gap
  detector. In v1 the implementation is rule-based against quiz
  signals; v2 may introduce a sequencing model.
