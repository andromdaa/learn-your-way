# 04 — API surface

The first-party API surface. The OpenAPI 3.1 stub below is the
authoritative specification; route handlers should be scaffolded from
it.

## Endpoints

- `POST /sources` — upload and parse a source document.
- `POST /profiles` — create or update an explicit learner profile.
- `POST /lessons/{id}/generate` — enqueue a personalization job (relevel or example replacement).
- `GET /lessons/{id}` — retrieve the canonical lesson graph.

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
      summary: Enqueue a personalization job (relevel or example replacement)
      operationId: generateLesson
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
                concept_id:
                  type: string
                profile_id:
                  type: string
                kind:
                  type: string
                  enum:
                    - relevel
                    - replace
              required: [concept_id, profile_id, kind]
      responses:
        '202':
          description: Job enqueued
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string

  /lessons/{id}/generate/{job_id}:
    get:
      summary: Poll personalization job status and retrieve result
      operationId: getGenerateResult
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
        - in: path
          name: job_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Job status
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                    enum: [pending, complete, not_found, failed]
                  result:
                    type: object
                    nullable: true

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
```

## Notes

- Personalization is asynchronous. `POST /lessons/{id}/generate` returns
  202 with a `job_id`. The client polls for completion via
  `GET /lessons/{id}/generate/{job_id}`.
