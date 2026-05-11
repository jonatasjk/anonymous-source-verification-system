# ASVS — Claude Code Context

## What this project is

Anonymous Source Verification System (ASVS) — a cryptographic evidence verification platform for
investigative journalists. Evidence packages are received from anonymous sources, timestamped via
RFC 3161 and Bitcoin blockchain anchoring (OpenTimestamps) **before any analysis**, then analysed
by an LLM, and a privacy-preserving Verification Certificate is issued with publication-ready
attribution language.

## Docs — read before making changes

All design decisions, invariants, and methodology are documented here:

- [`docs/AI_AGENT_INSTRUCTIONS.md`](docs/AI_AGENT_INSTRUCTIONS.md) — **Start here.** Stack, invariants, key file map, attribution format, colour palette, run commands.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System design, component boundaries, security model, what cryptography can and cannot prove.
- [`docs/BUSINESS_REQUIREMENTS.md`](docs/BUSINESS_REQUIREMENTS.md) — Objectives, sample scenario, expected certificate output format.
- [`docs/ANALYSIS_METHODOLOGY.md`](docs/ANALYSIS_METHODOLOGY.md) — How LLM scoring works, the three scoring dimensions and rubrics, attribution sentence generation and tone selection.

## Task-specific skills

Read the relevant skill before making changes in these areas:

- [`docs/skills/add-migration.md`](docs/skills/add-migration.md) — Liquibase changeset rules and template
- [`docs/skills/add-api-endpoint.md`](docs/skills/add-api-endpoint.md) — FastAPI route conventions
- [`docs/skills/add-celery-task.md`](docs/skills/add-celery-task.md) — Background task patterns

## Hard invariants — never violate

1. **Timestamp before analysis.** RFC 3161 and OTS are sealed at ingestion. Never defer or move timestamping.
2. **No source PII.** Filenames → `SHA-256(filename)` only. No IP addresses, email addresses, or source names in the database.
3. **Celery tasks use `db_session()`.** Never use FastAPI's `get_db()` dependency inside a task.
4. **Certificate language = provenance, not truth.** Every certificate must include: _"attests to provenance and integrity, not to the truth of the underlying allegations."_
5. **OTS confirmation is async.** The Beat task `poll_ots_confirmations` updates `bitcoin_block` in the background. It never blocks pipeline progress or certificate issuance.
6. **Attribution tone is per-claim.** The LLM writes complete sentences and selects `assertive`, `hedged`, or `alleged` per claim. Python only substitutes `{platform}` and `{cert_id}` placeholders — it does not rewrite or wrap sentences.

PLATFORM_NAME=ASVS          # appears in attribution sentences
```
