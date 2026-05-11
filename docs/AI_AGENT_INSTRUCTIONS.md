# AI Agent Instructions — Anonymous Source Verification System (ASVS)

This file is the single source of truth for AI agent context. Both
`.github/copilot-instructions.md` (GitHub Copilot) and `CLAUDE.md` (Claude Code) reference it.
Do not duplicate this content in those files — update it here.

---

## What this project is

ASVS is a cryptographic evidence verification platform for investigative journalists. Evidence
packages are received from anonymous sources, timestamped via RFC 3161 and Bitcoin blockchain
anchoring (OpenTimestamps) **before any analysis**, then analysed by an LLM, and a
privacy-preserving Verification Certificate is issued with publication-ready attribution language.

---

## Documentation index

Read the relevant doc before making changes in that area:

| Document | When to read |
|---|---|
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | System design, component boundaries, security model, what cryptography can/cannot prove |
| [`docs/BUSINESS_REQUIREMENTS.md`](BUSINESS_REQUIREMENTS.md) | Objectives, sample scenario, expected certificate output format |
| [`docs/ANALYSIS_METHODOLOGY.md`](ANALYSIS_METHODOLOGY.md) | LLM scoring dimensions, rubrics, attribution sentence generation, tone selection |
| [`docs/skills/`](skills/) | Reusable task-specific AI skills for common operations in this codebase |

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12), sync handlers |
| ORM | SQLAlchemy 2 (sync) + psycopg2 + PostgreSQL 17 |
| Cache / broker | Redis 7 |
| Task queue | Celery 5 + Beat |
| LLM | OpenAI `gpt-4o` via `client.beta.chat.completions.parse` (structured Pydantic output) |
| Crypto | AES-256-GCM, SHA-256, RFC 3161, OpenTimestamps (Bitcoin) |
| Migrations | Liquibase YAML (`backend/db/changelog/`) |
| Frontend | React 18 + TypeScript + Vite 6 + Tailwind CSS v3 + TanStack Query v5 |

---

## Hard invariants — never violate

1. **Timestamp before analysis.** RFC 3161 and OTS are sealed at ingestion. Never defer or move
   timestamping.
2. **No source PII.** Filenames → `SHA-256(filename)` only. No IP addresses, email addresses, or
   source names anywhere in the database.
3. **Celery tasks use `db_session()`.** Never use FastAPI's `get_db()` dependency inside a task.
4. **Certificate language = provenance, not truth.** Every certificate must include:
   _"attests to provenance and integrity, not to the truth of the underlying allegations."_
5. **OTS confirmation is async.** The Beat task `poll_ots_confirmations` updates `bitcoin_block`
   in the background. It never blocks pipeline progress or certificate issuance.
6. **Attribution tone is per-claim.** The LLM writes complete sentences and selects `assertive`,
   `hedged`, or `alleged` per claim. Python only substitutes `{platform}` and `{cert_id}`
   placeholders — it does not rewrite or wrap sentences.

---

## Key files

```
backend/app/
  core/
    config.py           pydantic-settings v2 Settings; PLATFORM_NAME, OPENAI_MODEL, …
                        @lru_cache singleton via get_settings()
    database.py         SQLAlchemy engine, get_db() (FastAPI dep), db_session() (Celery),
                        Redis helpers: set_submission_status(), get_submission_status()
    crypto.py           AES-256-GCM, SHA-256, derive_file_key, encrypt_bytes, decrypt_bytes
    merkle.py           build_merkle_tree(), verify_inclusion()
  models/
    db.py               ORM: Submission, SubmissionFile, TimestampProof,
                        AnalysisResult (+key_claims, attribution_quotes JSONB), Certificate
    schemas.py          Pydantic schemas — SubmissionResponse uses validation_alias="id"
  services/
    ingestion.py        files → SHA-256 hash → Merkle tree → AES encrypt → persist
    timestamping.py     RFC 3161 TSR + OpenTimestamps .ots anchoring
    analysis.py         ANALYSIS_SYSTEM_PROMPT, _AttributionSentence, _AnalysisOutput,
                        _call_openai(), _mock_analysis()
    certificate.py      _build_attribution_language(), generate_certificate()
  tasks/
    celery_app.py       Celery app + Beat schedule (OTS poll every 5 min)
    pipeline.py         task_timestamp → task_analyse → task_certify chain
                        enqueue_pipeline(submission_id) helper
    ots_confirmation.py Beat task: upgrade .ots, write bitcoin_block + block_timestamp
  routers/
    submissions.py      POST /api/submissions (202), GET /api/submissions/{id}/status
    certificates.py     GET /api/certificates/{id} JSON + PDF (ReportLab)
    verify.py           POST /api/verify, GET /api/submissions/{id}/files/{hash}/proof
  main.py               FastAPI app, CORS, router registration, /health

backend/db/changelog/
  db.changelog-root.yaml            Liquibase root — includes all releases
  releases/v001__initial_schema.yaml
  releases/v002__add_attribution_columns.yaml

frontend/src/
  components/
    UploadWizard/        Multi-step file upload (drag-and-drop, privacy warning, submit)
    StatusDashboard/     Pipeline progress polling (3 s interval until COMPLETE/FAILED)
    CertificateViewer/   Certificate display + per-tone attribution copy buttons
  api/client.ts          Axios typed client: submitFiles, getStatus, getCertificate, …
  hooks/useSubmission.ts useSubmissionStatus (polls), useCertificate (staleTime: Infinity)
  types/certificate.ts   TypeScript interfaces matching backend schemas
```

---

## Attribution sentences format

The `attribution_language` field in a certificate payload contains:

1. Two auto-generated provenance paragraphs (timestamp anchor + provenance caveat).
2. 3–6 LLM-produced sentences stored as `{"text": "...", "tone": "..."}` in `attribution_quotes`.

Tone values and when the LLM chooses them:

| Tone | Evidence strength | Form |
|---|---|---|
| `assertive` | Multiple independent corroborating sources | Direct-quote: `"Claim," said a source verified via {platform} (Certificate {cert_id}).` |
| `hedged` | Partial corroboration or single source type | Indirect: `According to a source verified by {platform} (Certificate {cert_id}), …` |
| `alleged` | Single document, red flags, or unverifiable claim | Allegation: `A source verified by {platform} (Certificate {cert_id}) alleged that …` |

Python substitutes `{platform}` and `{cert_id}` only — never rewrites the sentence.

---

## Colour palette (Tailwind custom tokens)

| Token | Hex | Usage |
|---|---|---|
| `surface` | `#f7f4ed` | Page background |
| `surface-card` | `#ede9e0` | Card backgrounds |
| `surface-border` | `#d4cfc4` | Borders, dividers |
| `ink` | `#0a0a09` | Primary text |
| `brand` | `#470c1d` | Primary actions, headings |
| `brand-dark` | `#3a0918` | Hover states |
| `brand-light` | `#6b1228` | Lighter brand accents |

---

## Running locally

```bash
# Infrastructure
cd backend && docker compose up -d

# Migrations
docker compose --profile migrate up liquibase

# Backend  (from backend/ with .venv active)
uvicorn app.main:app --reload

# Celery worker  (separate terminal, same dir)
celery -A app.tasks.celery_app worker --loglevel=info

# Frontend
cd frontend && npm run dev
```

## Key environment variables (`backend/.env`)

```
POSTGRES_PASSWORD=...
SECRET_KEY=...
OPENAI_API_KEY=...     # leave empty to use mock analysis
OPENAI_MODEL=gpt-4o
PLATFORM_NAME=ASVS     # appears in attribution sentences
```

Full list in `backend/.env.example`.
