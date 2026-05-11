# Evidence Analysis Methodology

This document explains how ASVS scores an evidence package — what is measured, how the numbers are calculated, and what the results mean (and don't mean).

---

## 1. Where analysis fits in the pipeline

Analysis is the **fourth stage** of the pipeline, and it only runs after the evidence has already been:

1. Received and hashed (SHA-256 per file, Merkle root across the package).
2. Encrypted at rest (AES-256-GCM, per-file derived key).
3. Cryptographically timestamped — RFC 3161 token from a trusted authority, plus an OpenTimestamps file anchored to the Bitcoin blockchain.

This ordering is fundamental: the timestamp is sealed **before any human or algorithm reads the content**. The analysis score therefore cannot retroactively affect the timestamp, and the timestamp cannot be adjusted to match the analysis. The two proofs are independent.

---

## 2. What the analysis is — and is not

| The analysis **is** | The analysis **is not** |
|---|---|
| An automated assessment of internal coherence | A fact-check against external sources |
| A measure of document consistency and corroboration | A verdict on whether the underlying allegations are true |
| A structured editorial aid for journalists and editors | Legal evidence or an auditor's opinion |
| Produced by an LLM reasoning over decrypted document text | Produced by a human reviewer |

> **The confidence score reflects the quality of the evidence package. It does not reflect the truth of its contents.**

This caveat is printed verbatim on every Verification Certificate.

---

## 3. Input to the model

When a submission contains multiple files, **all files are included in a single LLM call** — the model analyses the entire package together, not each file individually. This is essential for the corroboration and consistency scores, which measure agreement _across_ documents.

Before the LLM call, the pipeline:

1. Decrypts each file using its per-file derived key.
2. Decodes to UTF-8 (binary files such as audio or images are represented by their type and size only).
3. Caps each file at **4,000 characters** to stay within context limits.
4. Concatenates all files with a `--- [file_type] ---` separator into a single evidence string.
5. Wraps the assembled text between `--- EVIDENCE PACKAGE BEGIN ---` and `--- EVIDENCE PACKAGE END ---` delimiters.

The assembled text is passed to the model with a framing header that identifies it as a pre-ingested, anonymised evidence package. Source-identifying information is stripped by the ingestion pipeline; the model is also instructed not to reproduce any that remains.

---

## 4. The three scoring dimensions

Each dimension is scored independently on a 0–100 integer scale. The model is instructed to be calibrated and critical — a score above 80 should be genuinely difficult to earn.

### 4.1 Consistency (0–100)

_Do the facts, dates, timelines, named roles, claimed events, and figures agree with each other across all documents?_

| Band | Meaning |
|---|---|
| 90–100 | Perfect agreement; all cross-references align |
| 70–89 | Minor inconsistencies that are explicable (different date formats, paraphrase vs. direct quote) |
| 50–69 | Moderate inconsistencies requiring clarification before publication |
| 0–49 | Material contradictions that undermine the core claim |

### 4.2 Corroboration (0–100)

_How many **independent** document types and originating sources corroborate the central claim?_

Independence is the key concept here. Five emails from the same email thread count as **one** source. A personal note and a separate analytical memo from different authors referencing the same event count as **two**.

| Band | Meaning |
|---|---|
| 90–100 | Three or more independent source types with overlapping substantive claims |
| 70–89 | Two independent sources or document types |
| 50–69 | Single source with partial corroboration from document metadata or context |
| 0–49 | Single unverified document with no corroboration |

### 4.3 Plausibility (0–100)

_Are the documents consistent with known institutional formats, bureaucratic language, technology (email headers, file metadata), and publicly understood facts about the described domain?_

| Band | Meaning |
|---|---|
| 90–100 | Highly authentic appearance; format, language, and context are entirely consistent |
| 70–89 | Mostly plausible with minor stylistic or procedural oddities |
| 50–69 | Some anomalies (unusual formatting, atypical language, implausible timelines) |
| 0–49 | Document appears fabricated or significantly altered; format inconsistencies are material |

---

## 5. Overall confidence and reliability class

```
overall_confidence = round(0.35 × consistency + 0.35 × corroboration + 0.30 × plausibility)
```

The weighting reflects that **coherence** (consistency) and **independence** (corroboration) are the strongest indicators of a credible evidence package, with plausibility as a supporting signal.

| Reliability class | overall_confidence |
|---|---|
| **HIGH** | ≥ 75 |
| **MEDIUM** | 50 – 74 |
| **LOW** | < 50 |

---

## 6. Additional output fields

Beyond the scores, the model returns:

| Field | Type | Description |
|---|---|---|
| `corroborating_sources` | int | Count of independent originating sources identified |
| `evidence_types` | string[] | Document types present (`email_chain`, `personal_notes`, `analytical_memo`, `journalist_intake`, `audio_recording`, `document`, `spreadsheet`, `image`, `other`) |
| `red_flags` | string[] | Concise factual observations about anomalies, contradictions, or authenticity concerns — **no names or identifying details** |
| `key_claims_anonymised` | string[] | Core factual claims that can be investigated further — **no names or identifying details** |
| `attribution_sentences` | object[] | Publication-ready sentences for direct use in reporting — see [Section 9](#9-interpreting-the-certificate) |

---

## 7. Privacy constraints enforced during analysis

The model operates under strict rules that are embedded in the system prompt and cannot be overridden by document content:

- No source names, personal names, or identifying information in any output field.
- No verbatim quotes from the documents.
- No email addresses, phone numbers, usernames, or institutional affiliations.
- Individuals referred to only by functional role: _source_, _subject_, _investigator_, _witness_, _institution_, _official_, _researcher_, _executive_.

Structured output parsing (via `client.beta.chat.completions.parse`) enforces the JSON schema on the response — any deviation by the model causes the call to fail rather than silently return malformed data.

---

## 8. Fallback behaviour

If `OPENAI_API_KEY` is not configured, the engine returns a clearly marked **mock analysis** with synthetic scores and a `key_claims_anonymised` entry noting that real scoring requires an API key. This allows the rest of the pipeline (timestamping, certificate generation) to complete without blocking.

---

## 9. Interpreting the certificate

When a Verification Certificate is issued, the `attribution_language` section contains pre-written statements that journalists can paste directly into reporting copy, editor's notes, or legal disclosures.

### Provenance paragraphs (always present)

Two boilerplate paragraphs are generated for every certificate:

1. A timestamping statement describing how and when the evidence was anchored, including whether Bitcoin confirmation is complete or pending.
2. A provenance caveat: _"The certificate attests to provenance and integrity, not to the truth of the underlying allegations."_

### Attribution sentences (evidence-specific)

The LLM produces 3–6 complete, publication-ready sentences derived from the evidence content. Each sentence has a **tone** chosen per claim based on how strongly the evidence supports it:

| Tone | When used | Example |
|---|---|---|
| `assertive` | Claim corroborated by multiple independent sources, internally consistent | `"The internal review process was bypassed entirely," said a source verified via ASVS's independent certification process (Certificate CERT-2026-A1B2C3).` |
| `hedged` | Partial corroboration, or consistent but single source type | `According to a source whose materials were independently verified by ASVS (Certificate CERT-2026-A1B2C3), the approval was issued before the safety audit concluded.` |
| `alleged` | Single document, red flags present, or claim cannot be cross-referenced | `A source independently verified by ASVS (Certificate CERT-2026-A1B2C3) alleged that the safety data was altered before submission.` |

The tone is chosen **per claim**, not globally. A single certificate can contain a mix of assertive and hedged sentences depending on which specific claims the evidence supports most strongly.

### Bitcoin confirmation state

The provenance paragraph adapts automatically:
- If the OpenTimestamps confirmation is **pending**: _"submitted for Bitcoin blockchain anchoring (confirmation pending)"_
- Once confirmed: _"anchored to the Bitcoin blockchain"_
