# Test fixtures

Phase 1 acceptance requires an OpenStax sample chapter PDF at
`openstax_chapter.pdf` in this directory.

The fixture is not committed; it should be supplied locally before
running phase 1 tests.

Suggested chapters:

- A short chapter with clear section boundaries for first-pass
  concept extraction.
- A chapter with at least one figure or table for ingest edge cases.

After adding the fixture, run:

```bash
uv run pytest tests/
```
