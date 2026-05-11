# Architecture: Anonymous Source Verification System

## 1. Problem Statement

Any journalist or adversary can hash a file *after* creating it and claim it existed earlier. The core challenge is **provenance**: proving that a piece of evidence existed at a specific point in time and has not been altered since. This system solves that by anchoring evidence to an externally-verifiable, tamper-evident timestamp at the moment of ingestion — before any analysis occurs.

---

## 2. What This System Can and Cannot Prove

This distinction is critical and must be understood by any operator, journalist, or reader of a certificate produced by this system.

### What cryptography proves

| Property | Mechanism |
|---|---|
| **Integrity** | SHA-256 hash detects any bit-level change to the file after ingestion |
| **Chronology** | RFC 3161 TSA token and Bitcoin `OP_RETURN` anchor establish an upper bound on when the content existed |
| **Provenance chain** | Merkle root ties all files in a submission to a single verifiable fingerprint |
| **Non-tampering after capture** | Any modification after timestamping invalidates the hash and the timestamp proofs |
| **Custody** | The system records which files were received together, in what state, at what moment |

### What cryptography cannot prove

> **Cryptography cannot prove semantic truth — that the content of the evidence is accurate, genuine, or unmanufactured.**

A sophisticated adversary can:
- Fabricate a convincing document and submit it before making any claim
- Stage an email thread or personal notes with full control over the content
- Produce audio using voice synthesis, then submit it

The timestamp proves the file existed at a point in time and was not altered afterward. It says nothing about whether the events described within it actually occurred.

### Implications for this system's design

The **confidence score** produced by the Analysis Engine reflects internal consistency, corroboration across document types, and plausibility against known facts — not ground truth. It is a structured editorial aid, not a verdict.

The certificate and attribution language must be read accordingly:
- A score of 90/100 means the evidence package is internally coherent and well-corroborated — not that the underlying allegation is true.
- A score of 40/100 means the package contains contradictions or thin corroboration — not that the allegation is false.

**Certificate language must never imply factual truth.** It asserts only: *this evidence existed at this time and has not been altered since.*

---

## 2. High-Level Architecture

See [sequence-diagram.puml](sequence-diagram.puml) for the full end-to-end flow, including the async Celery pipeline, Merkle proof path computation, selective disclosure, and independent verification steps.

**Layers at a glance:**

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript (Vite) |
| API | FastAPI (Python) |
| Async pipeline | Celery worker chained tasks |
| Task broker & status cache | Redis |
| Metadata store | PostgreSQL (Liquibase migrations) |
| Encrypted file store | Local filesystem (dev) / S3 (prod) |
| Timestamp anchors | RFC 3161 TSA (FreeTSA.org) + OpenTimestamps (Bitcoin) |

---

## 3. Components

### 3.1 Frontend — React + TypeScript (Vite)

| View | Purpose |
|---|---|
| **Upload Wizard** | Multi-step form: select files, add optional metadata (date range, subject area), submit. No source identity fields. |
| **Status Dashboard** | Shows ingestion → timestamping → analysis progress per submission. |
| **Certificate Viewer** | Renders the privacy-preserving certificate (ID, timestamp proof, confidence breakdown, attribution text). Includes copy-to-clipboard and printable view. |

**Key libraries**: React Query (async state), React Dropzone (file upload), Tailwind CSS (styling).

---

### 3.2 Backend — Python + FastAPI

#### 3.2.1 Ingestion Service

Responsibilities:
1. Accept a multipart upload of one or more evidence files.
2. Compute **SHA-256** of each file immediately upon receipt (before writing to disk).
3. Build a **Merkle tree** across all file hashes and compute the root — a single fingerprint for the entire evidence package.
4. For each leaf (file), compute and store its **Merkle proof path**: the ordered list of sibling hashes from that leaf up to the root. This enables selective disclosure (see below).
5. Assign a random, opaque `submission_id` (UUIDv4). No IP address, no user account, no source metadata stored.
6. Store files encrypted at rest (AES-256-GCM, per-file key wrapped by a master key).

**Why Merkle tree with proof paths?**

The Merkle root is what gets timestamped — a single hash representing the entire submission. But storing the per-file proof path unlocks two additional properties:

- **Selective verification**: Given a file hash + its proof path + the Merkle root, anyone can verify that file was part of the original timestamped package in O(log n) operations, without knowing any other file in the bundle.
- **Selective disclosure**: A journalist can publish and authenticate a single document from a multi-file submission by sharing only that file's hash and its proof path. The existence of other files is not revealed — their hashes are represented only as opaque siblings in the path.

$$\text{valid} \iff \text{hash}(\text{leaf} + \text{proof path}) = \text{merkle\_root}$$

Without proof paths, authenticating any single file requires revealing all file hashes to reconstruct the root — undermining source protection when only part of the evidence is published.

#### 3.2.2 Timestamping Service

This is what distinguishes the system from simple hashing.

**Primary: RFC 3161 Trusted Timestamp**
- Send the Merkle root hash to a trusted, accredited Timestamp Authority (TSA) such as [FreeTSA.org](https://freetsa.org) or DigiCert.
- The TSA returns a signed timestamp token (`.tsr` file) containing: the hash, the TSA's signature, and a UTC timestamp.
- The token is independently verifiable by anyone with the TSA's public certificate — no trust in *this* system is required.

> **FreeTSA certificate note (March 2026):** FreeTSA.org rotated its TSA certificate in March 2026. The new certificate is valid from **16 March 2026 to February 2040** and uses **Elliptic-curve P-384 (secp384r1)** instead of RSA. The previous RSA certificate expired March 2026 and is archived as `tsa.crt_expired`.
>
> Operational requirements:
> - Verification of tokens issued **before March 2026** must use the old certificate (`tsa.crt_expired`), not the current one.
> - Verification of tokens issued **on or after 16 March 2026** uses the current `tsa.crt` (P-384).
> - The system must store which certificate generation signed each token (`tsa_cert_generation: "2026-2040"` or `"2016-2026"`) alongside the `.tsr` token so verifiers know which public key to use.
> - `rfc3161ng` and OpenSSL both support P-384; confirm the installed version handles `secp384r1` before deployment.

**Secondary: OpenTimestamps (Bitcoin blockchain)**
- Submit the same hash to [OpenTimestamps](https://opentimestamps.org/).
- The hash is aggregated with others and anchored into the Bitcoin blockchain via `OP_RETURN`.
- Once confirmed (~1 block, ~10 min), the timestamp is immutable: altering it would require rewriting the Bitcoin chain.

Two independent anchors make forgery essentially impossible: an adversary would need to compromise a TSA *and* rewrite the Bitcoin blockchain.

#### 3.2.3 Analysis Engine

Runs after timestamping. Uses an LLM (OpenAI GPT-4o or local Ollama model) with structured output to evaluate the evidence package along three dimensions:

| Dimension | Description |
|---|---|
| **Consistency** | Do the accounts, dates, names, and facts across documents agree with each other? |
| **Corroboration** | How many independent sources or document types support the core claim? |
| **Plausibility** | Are the documents consistent with known facts, formats, and institutional practices? |

Each dimension is scored 0–100. A weighted composite produces the **Overall Confidence Score** (0–100).

The engine also extracts:
- Key claims (anonymized)
- Evidence type per file (email, audio, notes, memo, etc.)
- Red flags (contradictions, anomalies)

**Privacy constraint**: The LLM prompt explicitly instructs the model to return structured JSON only. No source names, identifying details, or verbatim quotes appear in the certificate output.

#### 3.2.4 Task Queue — Celery + Redis

Timestamping and analysis are not instant: the RFC 3161 round-trip takes seconds, OpenTimestamps confirmation takes ~10 minutes, and LLM analysis may take 30–90 seconds. Blocking an HTTP request for any of this would be unacceptable.

**Design**: The Ingestion Service enqueues Celery tasks immediately after storing files and returns `202 Accepted` to the frontend. A Celery worker processes the pipeline asynchronously.

| Component | Role |
|---|---|
| **Redis** | Celery message broker and result backend; also stores per-submission status strings (e.g. `INGESTED`, `TIMESTAMPED`, `ANALYZED`, `COMPLETE`) |
| **Celery worker** | Executes the three-stage pipeline: `timestamp_submission` → `analyze_submission` → `generate_certificate`, chained via Celery `chain()` |
| **Task chaining** | Each stage updates submission status in PostgreSQL and Redis before triggering the next; failures are retried with exponential back-off |
| **Status polling** | `GET /api/submissions/{id}/status` reads the Redis key for sub-second response without hitting PostgreSQL on every poll |

The Bitcoin OpenTimestamps confirmation is handled by a separate periodic Celery Beat task that checks pending `.ots` receipts every 5 minutes and writes the confirmed block height back to PostgreSQL.

---

#### 3.2.5 Certificate Service

Generates a `VerificationCertificate` object:

```json
{
  "certificate_id": "CERT-2026-A3F9B1",
  "submission_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "issued_at": "2026-05-10T14:32:00Z",
  "evidence_package": {
    "file_count": 5,
    "merkle_root": "a3f9b1c2d4e5f6...",
    "files": [
      {
        "filename_hash": "sha256_of_filename",
        "content_hash": "sha256_of_content",
        "file_type": "email_chain",
        "size_bytes": 14382
      }
    ]
  },
  "timestamp_proofs": {
    "rfc3161": {
      "tsa": "freetsa.org",
      "tsa_cert_generation": "2026-2040",
      "tsa_cert_algorithm": "EC P-384 (secp384r1)",
      "token_hash": "...",
      "timestamp": "2026-05-10T14:30:01Z"
    },
    "opentimestamps": {
      "bitcoin_block": 895123,
      "block_timestamp": "2026-05-10T14:41:00Z",
      "ots_file_hash": "..."
    }
  },
  "analysis": {
    "overall_confidence": 81,
    "consistency_score": 87,
    "corroboration_score": 79,
    "plausibility_score": 76,
    "evidence_types": ["email_chain", "audio_recording", "personal_notes", "analytical_memo", "journalist_intake"],
    "corroborating_sources": 3,
    "red_flags": [],
    "reliability_class": "HIGH"
  },
  "attribution_language": [
    "A source verified via our independent certification process (Certificate CERT-2026-A3F9B1) provided documentation corroborated by 3 independent sources with an overall confidence score of 81/100.",
    "\"The internal review process was bypassed entirely,\" said a source verified via our independent certification process.",
    "Evidence reviewed for this report was authenticated using cryptographic timestamps anchored to the Bitcoin blockchain and a trusted timestamp authority, ensuring the materials predate publication."
  ]
}
```

Each file entry in `evidence_package.files` includes a `merkle_proof` array — the ordered sibling hashes from that leaf to the root. A verifier can confirm a single file's inclusion without seeing any other file:

```python
def verify_inclusion(file_hash: str, proof_path: list[str], merkle_root: str) -> bool:
    node = file_hash
    for sibling in proof_path:
        node = sha256(node + sibling)  # direction encoded in ordering convention
    return node == merkle_root
```

The certificate never contains: source name, IP address, file contents, or verbatim quotes.

---

### 3.3 Storage

| Store | Technology | Contents |
|---|---|---|
| Encrypted file store | Local filesystem (dev) / S3 (prod) | AES-256-GCM encrypted evidence files + `.tsr` timestamp tokens + `.ots` OpenTimestamps files |
| Metadata DB | PostgreSQL | Submission records, file hashes, analysis results, certificates — no PII |
| Task broker & status cache | Redis | Celery task queue, result backend, and per-submission status strings |

---

## 4. Data Flow

The detailed sequence is in [sequence-diagram.puml](sequence-diagram.puml). Summary of stages:

1. **Ingest** — SHA-256 each file, build Merkle tree + proof paths, encrypt files, enqueue Celery chain, return `202 Accepted`.
2. **Timestamp** — Celery worker sends Merkle root to RFC 3161 TSA (`.tsr` token) and OpenTimestamps (`.ots` receipt).
3. **OTS confirmation** — Celery Beat polls every 5 min until the Bitcoin block is confirmed.
4. **Analyse** — LLM scores consistency, corroboration, and plausibility; returns structured JSON (no PII).
5. **Certify** — Certificate Service assembles `VerificationCertificate`, writes to PostgreSQL, sets Redis status to `COMPLETE`.
6. **Retrieve** — Frontend polls Redis for status, then fetches certificate JSON including per-file Merkle proof paths.
7. **Verify** — Any third party can independently verify the `.tsr` token and `.ots` file without trusting this system.

---

## 5. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/submissions` | Upload evidence package (multipart). Returns `submission_id`. |
| `GET` | `/api/submissions/{id}/status` | Poll ingestion/timestamping/analysis progress. |
| `GET` | `/api/submissions/{id}/certificate` | Retrieve the final certificate JSON. |
| `GET` | `/api/submissions/{id}/certificate.pdf` | Download printable PDF certificate. |
| `POST` | `/api/verify` | Given a `certificate_id` + `merkle_root`, independently verify the timestamp proofs. Public endpoint. |
| `GET` | `/api/submissions/{id}/files/{file_hash}/proof` | Return the Merkle proof path for a single file, enabling selective disclosure without revealing other files in the bundle. |

---

## 6. Security & Privacy Design

| Concern | Mitigation |
|---|---|
| Source identity | No auth required; no IP logged; ephemeral session token only |
| File contents | AES-256-GCM at rest; TLS 1.3 in transit; files never sent to external services verbatim |
| LLM privacy | Only anonymized summaries and hashes sent to LLM API; or run a local Ollama model |
| Certificate forgery | RFC 3161 token verifiable by any third party without trusting this system |
| Tamper detection | Merkle root + dual timestamp anchors; any file modification changes the root |
| Selective disclosure | Merkle proof paths let a journalist authenticate one file without revealing others exist |

---

## 7. Project Structure

```
objection/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint
│   │   ├── routers/
│   │   │   ├── submissions.py       # POST /submissions, GET /status
│   │   │   ├── certificates.py      # GET /certificate
│   │   │   └── verify.py            # POST /verify (public); GET /files/{hash}/proof
│   │   ├── services/
│   │   │   ├── ingestion.py         # Hashing, Merkle tree, file storage
│   │   │   ├── timestamping.py      # RFC 3161 + OpenTimestamps
│   │   │   ├── analysis.py          # LLM analysis engine
│   │   │   └── certificate.py       # Certificate assembly + PDF
│   │   ├── tasks/
│   │   │   ├── celery_app.py        # Celery app + Redis broker config
│   │   │   ├── pipeline.py          # Chained tasks: timestamp → analyze → certify
│   │   │   └── ots_confirmation.py  # Celery Beat task: poll pending OTS receipts
│   │   ├── models/
│   │   │   ├── db.py                # SQLAlchemy models (PostgreSQL, no migration logic)
│   │   │   └── schemas.py           # Pydantic request/response schemas
│   │   └── core/
│   │       ├── config.py            # Settings (env vars)
│   │       ├── crypto.py            # AES encryption helpers
│   │       └── merkle.py            # Merkle tree, root, and proof path computation
│   ├── db/
│   │   └── changelog/
│   │       ├── db.changelog-root.xml        # Root changelog (includes all releases)
│   │       └── releases/
│   │           └── v001__initial_schema.xml # Initial tables: submissions, files, proofs, certs
│   ├── tests/
│   ├── sample_evidence/             # The 5 test files from the scenario
│   ├── requirements.txt
│   └── docker-compose.yml           # PostgreSQL + Redis services for local dev
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadWizard/
│   │   │   ├── StatusDashboard/
│   │   │   └── CertificateViewer/
│   │   ├── hooks/
│   │   │   └── useSubmission.ts     # React Query hooks
│   │   ├── types/
│   │   │   └── certificate.ts       # TypeScript types matching backend schemas
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── docs/
    ├── requirements.md
    └── ARCHITECTURE.md
```

---

## 8. Sample Evidence Plan

The five files from the scenario will be created as realistic plaintext/binary fixtures under `backend/sample_evidence/`. The system will be demonstrated end-to-end by ingesting this package and producing a real certificate.

| File | Type | Role in Analysis |
|---|---|---|
| `journalist_intake_notes.txt` | Text | Corroborating narrative; establishes timeline |
| `email_chain_vasquez_hargrove.txt` | Text | Primary source communication; consistency check |
| `recorded_conversation_march_19.mp3` | Audio | Independent witness; transcribed for analysis |
| `data_comparison_memo.txt` | Text | Quantitative anomaly evidence; plausibility check |
| `vasquez_personal_notes.txt` | Text | Source's contemporaneous record; corroboration |

---

## 9. Key Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI | Async, typed, fast — good fit for I/O-heavy pipeline |
| Timestamp (primary) | RFC 3161 via `rfc3161ng` | Industry standard; legally admissible in many jurisdictions |
| Timestamp (secondary) | `opentimestamps-client` | Decentralized, immutable, no single point of trust |
| LLM | OpenAI GPT-4o (configurable) | Structured JSON output mode; swap for Ollama for full privacy |
| PDF generation | `reportlab` or `weasyprint` | Certificate PDF rendering |
| Database | PostgreSQL | Reliable, concurrent writes; supports future horizontal scaling |
| DB ORM | SQLAlchemy | Models and queries; migrations managed separately by Liquibase |
| Migrations | Liquibase (XML changelogs) | Declarative, database-agnostic, versioned changesets with full rollback support; runs as a Docker service before the app starts |
| Task queue | Celery + Redis | Async pipeline execution; Redis doubles as status cache and result backend |
| Scheduler | Celery Beat | Periodic OTS confirmation polling (every 5 min) |
| Frontend build | Vite + React + TypeScript | Fast DX; strict typing matches backend schemas |
| Styling | Tailwind CSS | Utility-first; fast prototyping |

---

## 10. Scope Decisions

These decisions were made explicitly during architecture review.

### Built

| Decision | Rationale |
|---|---|
| **Merkle tree with per-file proof paths** | Enables selective disclosure — a journalist can authenticate one document from a bundle without revealing the others exist. Core to source protection. |
| **Dual timestamp anchors** (RFC 3161 + Bitcoin) | Two independent authorities make forgery require compromising both a TSA and the Bitcoin chain simultaneously. |
| **PostgreSQL** (not SQLite) | Concurrent writes from Celery workers, reliable JSON column support, and production-readiness without a later migration. |
| **Celery + Redis** for async pipeline | Timestamping and LLM analysis are long-running; the upload endpoint must return immediately. Redis doubles as status cache, eliminating DB polling. |
| **Celery Beat** for OTS confirmation | Bitcoin confirmation takes ~10 min; polling in the background on a schedule is cleaner than blocking a task or using a callback. |
| **No source authentication** | Requiring login would undermine anonymity. The system is intentionally open on ingestion. |
| **LLM output is structured JSON only** | Prevents the model from echoing source names, quotes, or identifying detail into the certificate. |
| **Confidence score as editorial aid** | Score reflects internal coherence, not truth. This is documented explicitly and enforced in certificate language. |

### Cut

| Decision | Why cut | If needed later |
|---|---|---|
| **Merkle chain across submissions** (append-only custody log) | Adds complexity for a use case — ongoing source relationships with multi-submission chains — that is out of scope for the prototype. Certificate Transparency logs use this pattern. | Hash each new submission's Merkle root together with the previous root before timestamping; store the chain in a dedicated table. |
| **Kafka** (instead of Redis/Celery) | Kafka's strengths — high-throughput fan-out, log retention, replay — are unnecessary for a low-volume, linear, three-stage pipeline. Operational overhead is not justified. | Adopt if independent downstream consumers (fraud detection, legal hold, notifications) need to subscribe to the same event stream. |
| **Device attestation** | Proving a file came from a specific device (e.g. EXIF-based chain of custody) requires hardware attestation (TPM, Apple Secure Enclave) and is out of scope. | Integrate Apple/Android attestation APIs or a hardware token flow at ingestion. |
| **Semantic truth verification** | Cryptography cannot prove content is accurate. No design decision can change this. The system proves provenance, not truth — and the certificate language reflects this explicitly. | Not addressable by technical means; requires editorial judgment. |
