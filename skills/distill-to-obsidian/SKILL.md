---
name: distill-to-obsidian
description: Distill durable, reusable knowledge from the source code, repositories, articles, documents, or discussion currently being read into the user's Obsidian knowledge base. Use this skill whenever the user asks to “提取到知识库”、“蒸馏到知识库”、“沉淀到 Obsidian / ai-wiki”、“把刚才读到的内容保存下来”、“把这个知识点记到我的知识库”, or otherwise expresses an intent to preserve current material as long-term personal knowledge—even if they do not name this skill. Do not trigger for a temporary summary, ordinary project documentation, “记住这个” without durable knowledge-base intent, or verbatim archival without knowledge distillation.
compatibility: Requires filesystem search/read/write access. Web-page ingestion also requires the defuddle skill. Obsidian Markdown editing should use the obsidian-markdown skill; Obsidian CLI is optional.
---

# Distill to Obsidian

Turn the material the user is currently studying into a small, durable improvement to their existing Obsidian Wiki. Treat this as knowledge integration, not transcript dumping or one-source-one-summary note taking.

## Core contract

- The user's explicit request to extract, distill, preserve, or save current material to their knowledge base authorizes the necessary minimal writes to the matched vault.
- Prefer improving an existing concept, shared framework, project page, or domain page over creating a parallel summary.
- Preserve provenance and uncertainty. A generated Wiki page is a synthesis layer, not a substitute for checking its sources.
- Do not scan an entire repository, vault, or large collection merely because it is available.
- Never write to a guessed vault. Resolve and validate the target first.
- Never expose or preserve credentials, tokens, private keys, personal data, or other secrets found in source material.

## 1. Resolve the material being referenced

Infer “这些内容”, “刚才的内容”, or similar references from the current task context. Normally this means the most recently read or discussed source files, symbols, article, document, or excerpt and the user's current question about them.

Include only information that is directly relevant to the user's focus and likely to remain useful. Exclude transient debugging attempts, conversational filler, tool output, and unsupported speculation.

If the user explicitly names several sources, that is authorization to process that bounded set. If several sources are merely present in context and the intended set is ambiguous, list the proposed sources and ask for confirmation. Do not silently widen the scope.

If the user only asks for a temporary summary, explanation, ordinary Markdown, project documentation, or verbatim archival—and does not express durable knowledge-base intent—do not run this workflow.

## 2. Resolve and validate the vault

If the user explicitly supplies a vault root for the current request, validate and use it for this run. If the user explicitly supplies a separate candidate-location file for a test or temporary environment, use only that file for the current run. Do not add either override to the persistent list without asking.

Otherwise, read [references/vault-locations.md](references/vault-locations.md) and check candidate roots in listed priority order. A candidate is valid only when `<vault-root>/ai-wiki/AGENTS.md` exists.

- One valid candidate: use it.
- Several valid candidates: use the highest-priority candidate and mention the choice in the completion report.
- No valid candidate: stop before writing, ask for the vault root, and validate it. Then ask whether to add the new root to the location list.

The knowledge workspace is `<vault-root>/ai-wiki/`. Never create a replacement `ai-wiki` structure merely to make an invalid candidate pass validation.

## 3. Load the vault's local rules

Before deciding what to change:

1. Read `<vault-root>/ai-wiki/AGENTS.md` completely.
2. Read the Wiki entry point required by that file, normally `wiki/index.md`.
3. Load `obsidian-markdown` before creating or editing Markdown notes.
4. Use `obsidian-cli` when its search, navigation, or vault-aware operations materially help; ordinary file edits do not require the CLI.
5. Load any source-specific skill required by `AGENTS.md`, such as `defuddle` for a web page.

The vault's `AGENTS.md` overrides this skill on directory ownership, schema, naming, ingestion, indexing, logs, and confirmation boundaries. If its rules cannot be followed, stop and explain the conflict rather than inventing a parallel structure.

## 4. Preserve provenance according to source type

### Web page

Use the `defuddle` skill to extract clean Markdown. Before saving, search the source layer for the canonical URL or an existing snapshot.

- Reuse an existing matching source instead of duplicating it.
- For a new page, save the cleaned source under the source directory required by `AGENTS.md`, with source URL, title, and capture date in its metadata.
- Do not overwrite an older immutable snapshot. If a materially changed version must be retained, create a dated version and relate it to the older source.

### Local source code or repository

Do not copy an entire repository into the vault. Record enough stable provenance to find the code again:

- repository name and remote URL when available;
- commit hash or release/tag;
- repository-relative file path;
- symbol, class, function, or module name;
- relevant line range as a convenience, recognizing that lines drift;
- whether the working tree had relevant uncommitted changes.

Prefer symbols and commit-pinned links over bare line numbers. Include only small code excerpts necessary to preserve the idea. Do not reproduce large copyrighted files or secrets.

### Existing source in `ai-wiki/sources/`

Treat it as immutable input. Read it and update the generated Wiki layer; do not clean up, reformat, rename, or summarize in place.

### Ephemeral or conversation-only material

When the material cannot be recovered later, save a compact source snapshot with date and context before synthesis. Preserve only the evidence needed for the durable claims, not the entire conversation.

## 5. Find the smallest useful integration

Search the index, titles, aliases, tags, headings, body text, and backlinks for related concepts. Then decide on the smallest coherent change set:

1. Update an existing concept, shared framework, or project page when it already owns the idea.
2. Create a page only when the topic is likely to recur, needs a stable hub, or the user explicitly requested an independent note.
3. Update a domain entry only when its route, core links, recent sources, or open questions materially change.
4. Update the global index only when global navigation changes.
5. Append the required ingest/query log entry; never rewrite history.

Avoid one-note-per-source accumulation. A new source should strengthen, qualify, contradict, or connect existing knowledge whenever possible.

## 6. Distill for understanding and retrieval

Adapt the page to its topic rather than forcing a rigid template. Preserve the following when they add value:

- a one-sentence core conclusion;
- key concepts and their relationships;
- mechanism, causal chain, or design rationale;
- where the idea applies and where it breaks down;
- for code, important symbols, control/data flow, invariants, and concise excerpts;
- counterexamples, common confusions, tradeoffs, and uncertainty;
- source links or source-note wikilinks;
- aliases, original terminology, and search terms that improve later retrieval;
- wikilinks to genuinely related existing notes.

Use Chinese by default unless the vault or user requires another language. Keep identifiers, APIs, commands, paths, project names, and established technical terms in their original form when translation would reduce precision.

Do not add flashcards, exercises, or a long tutorial by default. Add memory prompts or practice material only when the user also asks to learn, remember, or review the topic.

## 7. Handle evidence and uncertainty

Default to the current sources plus the local vault. Do not turn a distillation request into open-ended web research.

- Attribute source-specific claims.
- Separate observed behavior from interpretation.
- Mark weak, conflicting, stale, or unverified claims as such.
- If a contradiction materially affects the note, preserve both positions and identify what would resolve it.
- Ask before doing external research unless the user also requested verification, supplementation, or current information.

## 8. Write and validate

Perform the minimal authorized writes directly; a separate preview is not required after an explicit distillation request. Pause only when the target vault is unresolved, source scope is ambiguous, a conflict risks destructive overwrite, or the operation has expanded into an unexpectedly large batch.

After editing:

1. Verify required properties and allowed values from `AGENTS.md`.
2. Check that new wikilink targets and referenced local sources exist.
3. Confirm immutable source files were not modified.
4. Confirm logs were appended rather than rewritten.
5. Review the diff or changed files for accidental unrelated edits and secrets.

## Completion report

Tell the user:

- which vault was selected;
- which source material was distilled;
- which files were created or updated;
- the most important knowledge added or revised;
- any uncertainty, conflict, or follow-up question that remains.

Keep the report concise and link to local files when the interface supports clickable paths.
