# GitHub Copilot Instructions — ASVS

> **Full context lives in [`docs/AI_AGENT_INSTRUCTIONS.md`](../docs/AI_AGENT_INSTRUCTIONS.md).**
> Read it before making any changes. It contains the stack, hard invariants, key file map,
> attribution sentence format, colour palette, and run commands.
>
> Task-specific skills are in [`docs/skills/`](../docs/skills/):
> - [`add-migration.md`](../docs/skills/add-migration.md) — Liquibase changeset rules and template
> - [`add-api-endpoint.md`](../docs/skills/add-api-endpoint.md) — FastAPI route conventions
> - [`add-celery-task.md`](../docs/skills/add-celery-task.md) — Background task patterns

---

## Quick reference

**Docs:**
[ARCHITECTURE.md](../docs/ARCHITECTURE.md) ·
[BUSINESS_REQUIREMENTS.md](../docs/BUSINESS_REQUIREMENTS.md) ·
[ANALYSIS_METHODOLOGY.md](../docs/ANALYSIS_METHODOLOGY.md)

---

## Stack

- **Backend**: FastAPI (Python 3.12) · SQLAlchemy 2 (sync) · PostgreSQL 17 · Redis 7 · Celery 5
- **LLM**: OpenAI `gpt-4o` via `client.beta.chat.completions.parse` (structured Pydantic output)
- **Crypto**: AES-256-GCM, SHA-256, RFC 3161, OpenTimestamps (Bitcoin)
- **Migrations**: Liquibase YAML (`backend/db/changelog/`)
- **Frontend**: React 18 + TypeScript + Vite 6 + Tailwind CSS v3 + TanStack Query v5

---

## Hard invariants — never violate

- Timestamp before analysis — RFC 3161 + OTS sealed at ingestion, before any LLM read.
- No source PII — `SHA-256(filename)` only, no IP/email/names in the DB.
- Celery tasks use `db_session()`, never `get_db()`.
- Every certificate must say: _"attests to provenance and integrity, not to the truth of the underlying allegations."_
- OTS confirmation is async (Beat task `poll_ots_confirmations`) — never blocks the pipeline.
- Attribution tone is per-claim (`assertive` / `hedged` / `alleged`). Python substitutes `{platform}` and `{cert_id}` only.

---

## Colour tokens

`surface` #f7f4ed · `surface-card` #ede9e0 · `surface-border` #d4cfc4 ·
`ink` #0a0a09 · `brand` #470c1d · `brand-dark` #3a0918 · `brand-light` #6b1228
