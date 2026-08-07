---
name: query-obsidian
description: Search the user's Obsidian ai-wiki knowledge base and answer from the material already stored there. Use this skill whenever the user asks to “在我的知识库查找相关内容”, “查一下知识库 / ai-wiki / Obsidian”, “基于我的笔记回答”, “我以前保存过什么”, or otherwise wants retrieval from their personal knowledge base—even when they do not name this skill. Do not trigger for saving or distilling material into the knowledge base, ordinary repository search, general web research, or Obsidian editing without a retrieval request.
compatibility: Requires filesystem search and read access. Obsidian CLI is optional; the workflow must work while Obsidian is closed.
---

# Query Obsidian

Answer a question from the user's existing `ai-wiki` knowledge base. Treat the generated Wiki as the primary synthesis layer and the stored sources as evidence to consult only when the Wiki is insufficient.

## Core contract

- Keep ordinary queries read-only. Do not create notes, update pages, append logs, or change vault metadata merely because the user asked a question.
- Start from the Wiki's navigation and local rules instead of searching the entire vault indiscriminately.
- Prefer a concise synthesized answer with links to the relevant notes over a raw dump of search results.
- Distinguish what the Wiki says, what an underlying source establishes, and what remains uncertain.
- Never guess a vault location or create a replacement vault when the configured target cannot be validated.
- Do not expose secrets, personal data, or unrelated private material encountered during retrieval.

## 1. Resolve the retrieval request

Identify the topic or question the user wants answered. Expand it into a small set of useful search terms when appropriate:

- Chinese and original-language terms;
- aliases, abbreviations, project names, APIs, and code identifiers;
- closely related concepts that are necessary to locate the owning page.

Keep the expansion bounded by the user's question. A broad request such as “知识库里关于 Rust 有什么” calls for a domain overview, not an exhaustive dump of every matching line.

If the request combines retrieval with an explicit write-back request, complete the read-only query first, then use `distill-to-obsidian` for the authorized write portion. A request to save, extract, distill, or preserve current material without a retrieval goal belongs to `distill-to-obsidian`, not this workflow.

## 2. Resolve and validate the vault

If the user explicitly supplies a vault root for the current request, validate and use it only for this run. If a test or temporary task explicitly supplies a separate candidate-location file, use only that file and do not read the persistent device list.

Otherwise, read [references/vault-locations.md](references/vault-locations.md) and check candidate roots in priority order. A candidate is valid only when `<vault-root>/ai-wiki/AGENTS.md` exists.

- One valid candidate: use it.
- Several valid candidates: use the highest-priority candidate and mention the choice only when it could surprise the user.
- No valid candidate: stop and ask for the vault root. Explain that a valid target must contain `ai-wiki/AGENTS.md`.

The knowledge workspace is `<vault-root>/ai-wiki/`. Do not search other vault directories unless the user explicitly expands the scope and the local rules permit it.

## 3. Load the local query rules

Before searching for an answer:

1. Read `<vault-root>/ai-wiki/AGENTS.md` completely.
2. Read the Wiki entry point required by that file, normally `wiki/index.md`.
3. Follow any domain routing, read boundaries, or query workflow declared there.

The vault's `AGENTS.md` overrides this skill on directory ownership, privacy boundaries, navigation, and evidence handling. If its rules conflict with the requested access, explain the conflict and stop rather than bypassing it.

`obsidian-cli` may help with vault-aware search or navigation when Obsidian is running. It is optional: ordinary filesystem reads and literal `rg` searches are the reliable default, so the query must still work while Obsidian is closed.

## 4. Search the generated Wiki first

Use `wiki/index.md` to identify likely domain, concept, project, overview, or shared pages. Then search only `wiki/` for the prepared terms, considering:

1. exact title, filename, alias, or technical identifier matches;
2. index and domain-page links;
3. headings and frontmatter such as `tags` or `domains`;
4. body-text matches and nearby wikilinks.

Use literal searches for user-provided terms so punctuation in APIs or identifiers is not interpreted as a regular expression. Read a small, relevant candidate set rather than every matching note. Prefer pages that own or synthesize the concept over pages that merely mention it.

For a narrow question, normally inspect the strongest few candidates. For a broad domain request, read the domain entry plus its central linked pages and summarize the structure at a useful level.

## 5. Consult sources only when needed

Search the read-only `sources/` layer only when at least one of these conditions applies:

- the generated Wiki does not contain enough information to answer;
- the question asks for evidence, provenance, exact wording, or source verification;
- relevant Wiki pages mark a claim as uncertain, conflicting, stale, or needing review.

Keep source retrieval bounded to terms and source families related to the question. Do not edit, rename, normalize, or summarize source files in place. Do not search `personal/` unless the user explicitly names an allowed file and the vault rules authorize reading it.

If the Wiki and a source disagree, report the disagreement and favor neither silently. If neither layer answers the question, say so. Do not automatically turn a knowledge-base query into web research; browse externally only when the user separately requests current or external verification.

## 6. Compose the answer

Use Chinese by default unless the user or vault rules require another language. Preserve project names, APIs, paths, commands, and established technical terms in their original form.

Lead with the answer, then support it with inline links to the relevant Wiki notes. Use vault-relative wikilinks such as `[[wiki/concepts/页面名|页面标题]]` when appropriate. When the interface supports clickable local paths, a local file link may supplement the wikilink.

Adapt the response to the request:

- For a direct question, synthesize a direct answer and cite the supporting pages near the relevant claims.
- For “查找相关内容” or a topic without a specific question, give a compact topic overview followed by the most relevant notes.
- When `sources/` was needed, identify which claims were source-verified and cite those source notes or URLs separately.
- When coverage is incomplete, end with a brief “知识库缺口” statement describing what was not found or remains uncertain.
- When there is no meaningful match, state that clearly and mention the terms and Wiki areas searched at a high level; do not fabricate related content.

Avoid long excerpts and unranked match lists. The goal is to help the user use what they already know, not to reproduce their vault.

## 7. Preserve the read-only boundary

An ordinary query does not authorize writes. In particular, do not:

- append a query, ingest, or audit log;
- create a cache, answer note, or temporary file inside the vault;
- update stale pages while answering;
- broaden the search into `personal/`, unrelated vault folders, or external services.

If the answer produces a durable synthesis that would improve the Wiki, you may briefly suggest the existing page where it could be integrated. Write it back only after the user explicitly asks, using `distill-to-obsidian` and the vault's write rules.

## Completion check

Before responding, confirm that:

- the selected root was validated through `ai-wiki/AGENTS.md`;
- `wiki/index.md` and the relevant generated pages were read first;
- `sources/` was searched only if the Wiki needed supplementation or verification;
- every substantive knowledge-base claim is traceable to a cited page or source;
- no vault file was changed.
