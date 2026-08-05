# Mock Wiki rules

- `sources/` stores immutable source snapshots.
- Generated knowledge belongs in `wiki/concepts/`.
- Every generated note has YAML properties: `title`, `tags`, `type`, `status`, `created`, `updated`, and `sources` when evidence exists.
- `tags` includes `llm-wiki`; concept `type` is `concept`; `status` is `active` or `needs-review`.
- Read `wiki/index.md` before writing.
- Add new concept pages to `wiki/index.md` with a one-line description.
- Append every ingestion to `logs/ingest-log.md`; do not rewrite existing entries.
