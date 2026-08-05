# Mock Wiki rules

- `sources/` is immutable input after creation.
- Generated knowledge belongs in `wiki/concepts/`.
- Prefer updating an existing page over creating a duplicate.
- Every generated note has YAML properties: `title`, `tags`, `type`, `status`, `created`, `updated`, and optional `sources`.
- `tags` includes `llm-wiki`; `type` is `concept`; `status` is `active`.
- Read `wiki/index.md` before writing.
- Append every ingestion to `logs/ingest-log.md`; do not rewrite existing entries.
- Only add `wiki/index.md` navigation when a new concept page is created.
