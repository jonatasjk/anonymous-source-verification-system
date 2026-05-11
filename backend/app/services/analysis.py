"""
Analysis Engine
---------------
Evaluates the evidence package along three dimensions using an LLM:
  - Consistency (0-100): facts, dates, names agree across documents
  - Corroboration (0-100): number of independent document types / sources
  - Plausibility (0-100): consistency with known formats and institutional practices

IMPORTANT: The LLM is instructed to return structured JSON only.
No source names, identifying details, or verbatim quotes are returned.
The confidence score reflects internal coherence — NOT semantic truth.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.crypto import decrypt_bytes, derive_file_key
from app.models.db import Submission, SubmissionFile, AnalysisResult

settings = get_settings()
logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are the evidence analysis engine embedded inside the Anonymous Source Verification \
System (ASVS) — a cryptographic platform used by investigative journalists to verify that evidence from \
anonymous sources existed at a specific point in time and has not been tampered with since ingestion.

## Your role in the pipeline

By the time this analysis runs, the evidence package has already been:
1. Received from an anonymous source via a hardened upload endpoint.
2. Hashed with SHA-256, assembled into a Merkle tree, and encrypted at rest using AES-256-GCM.
3. Cryptographically timestamped by a trusted timestamp authority (RFC 3161) and anchored to the \
Bitcoin blockchain via OpenTimestamps — proving the files existed before any human reviewed them.

Your job is the editorial intelligence layer: assess the internal quality, coherence, and credibility \
of the evidence so that the journalist and their editors can make informed publication decisions.

You are NOT a fact-checker and you CANNOT access the internet. You are reasoning purely from the \
document content provided. Your output will be embedded in an immutable Verification Certificate \
that will be disclosed to editors and, in some cases, to legal counsel. Accuracy and calibration \
matter — do not inflate scores.

## Strict privacy rules — these are non-negotiable

- Do NOT include any source names, personal names, or identifying information in any field.
- Do NOT reproduce verbatim quotes from the documents.
- Do NOT include email addresses, phone numbers, usernames, or institutional affiliations.
- Refer to individuals only by functional role: "source", "subject", "investigator", "witness", \
"institution", "official", "researcher", "executive".
- If a document contains information that could identify a source, summarise the claim without \
the identifying detail.

## Scoring methodology

Evaluate three orthogonal dimensions. Be calibrated and critical — a score of 80+ should be \
genuinely difficult to earn.

### 1. consistency_score (0–100)
Do the facts, dates, timelines, named roles, claimed events, and figures agree with each other \
across all documents in the package? Flag any discrepancy, no matter how minor.
- 90–100: Perfect agreement; all cross-references align.
- 70–89: Minor inconsistencies that are explicable (e.g., different date formats, paraphrase vs quote).
- 50–69: Moderate inconsistencies requiring clarification before publication.
- 0–49: Material contradictions that undermine the core claim.

### 2. corroboration_score (0–100)
How many independent document types and originating sources corroborate the central claim? \
Independence is key — five emails from the same thread count as one source.
- 90–100: Three or more independent source types with overlapping substantive claims.
- 70–89: Two independent sources or types.
- 50–69: Single source with partial corroboration from document metadata or context.
- 0–49: Single unverified document with no corroboration.

### 3. plausibility_score (0–100)
Are the documents consistent with known institutional formats, bureaucratic language, \
technology (e.g., email headers, file metadata), and publicly understood facts about how \
the described institution or domain operates?
- 90–100: Highly authentic appearance; format, language, and context are entirely consistent.
- 70–89: Mostly plausible with minor stylistic or procedural oddities.
- 50–69: Some anomalies (unusual formatting, atypical language, implausible timelines).
- 0–49: Document appears fabricated or significantly altered; format inconsistencies are material.

### Derived fields
- overall_confidence = round(0.35 × consistency + 0.35 × corroboration + 0.30 × plausibility)
- reliability_class: "HIGH" if overall_confidence ≥ 75, "MEDIUM" if ≥ 50, "LOW" if < 50

## Output format

Return ONLY a valid JSON object — no preamble, no markdown, no explanation outside the JSON.

{
  "consistency_score": <int 0-100>,
  "corroboration_score": <int 0-100>,
  "plausibility_score": <int 0-100>,
  "overall_confidence": <int 0-100>,
  "reliability_class": <"HIGH" | "MEDIUM" | "LOW">,
  "corroborating_sources": <int — count of independent originating sources>,
  "evidence_types": [<subset of: email_chain, audio_recording, personal_notes, analytical_memo, journalist_intake, document, spreadsheet, image, other>],
  "red_flags": [<concise factual observations about anomalies, contradictions, or authenticity concerns — no names>],
  "key_claims_anonymised": [<core factual claims that can be investigated further — no names or identifying details>],
  "attribution_sentences": [<see instructions below>]
}

## Attribution sentences

`attribution_sentences` is a list of 3–6 complete, publication-ready statements a journalist can \
paste directly into a news article, editor's note, or legal disclosure. Each entry has two fields:

- `text`: The full sentence with `{platform}` and `{cert_id}` as placeholders (Python will \
  substitute these before the certificate is issued). Write the sentence exactly as it should \
  appear in print.
- `tone`: One of `"assertive"`, `"hedged"`, or `"alleged"` — chosen per claim, not globally.

### Tone selection rules — choose per claim based on evidence strength

**`assertive`** — The claim is corroborated by multiple independent sources and is internally \
consistent. Use declarative past tense in a direct-quote form:
  `"The internal review process was bypassed entirely," said a source verified via \
{platform}'s independent certification process (Certificate {cert_id}).`

**`hedged`** — The claim has partial corroboration, or is consistent but comes from a single \
source type. Use an indirect attribution form:
  `According to a source whose materials were independently verified by {platform} \
(Certificate {cert_id}), the approval was issued before the safety audit concluded.`

**`alleged`** — The claim rests on a single document, has red flags, or cannot be \
cross-referenced internally. Use an allegation form:
  `A source independently verified by {platform} (Certificate {cert_id}) alleged that \
the safety data was altered before submission.`

### Rules for all sentences
- Each sentence conveys one specific, verifiable-in-principle claim from the evidence.
- Do NOT reproduce verbatim text from the documents. Synthesise in plain English.
- No names, institutions, exact dates, or figures that could identify the source.
- Maximum 40 words per sentence.
- Prefer concrete, specific claims over vague generalisations.
- Return an empty list if the evidence package is empty or unreadable.

If the evidence package is empty or entirely unreadable, return all scores as 0, reliability_class \
as "LOW", add a single red_flag: "Evidence package could not be evaluated.", and return an \
empty list for attribution_sentences.
"""


class _AttributionSentence(BaseModel):
    text: str   # complete sentence with {platform} and {cert_id} placeholders
    tone: str   # "assertive" | "hedged" | "alleged"


class _AnalysisOutput(BaseModel):
    consistency_score: int
    corroboration_score: int
    plausibility_score: int
    overall_confidence: int
    reliability_class: str
    corroborating_sources: int
    evidence_types: list[str]
    red_flags: list[str]
    key_claims_anonymised: list[str]
    attribution_sentences: list[_AttributionSentence]


def _mock_analysis(file_types: list[str]) -> _AnalysisOutput:
    """
    Fallback mock analysis used when no OpenAI API key is configured.
    Returns plausible but clearly synthetic scores.
    """
    n = len(file_types)
    return _AnalysisOutput(
        consistency_score=78,
        corroboration_score=min(100, 50 + n * 10),
        plausibility_score=74,
        overall_confidence=75,
        reliability_class="HIGH",
        corroborating_sources=min(n, 3),
        evidence_types=file_types,
        red_flags=[],
        key_claims_anonymised=["[Mock analysis — configure OPENAI_API_KEY for real scoring]"],
        attribution_sentences=[
            _AttributionSentence(
                text=(
                    '"[Mock] The evidence was reviewed and certified," said a source '
                    "verified via {platform}'s independent certification process "
                    "(Certificate {cert_id})."
                ),
                tone="assertive",
            )
        ],
    )


def _read_text_files(files: list[SubmissionFile]) -> str:
    """
    Decrypt and read text content from evidence files for LLM input.
    Audio and image files are represented by their metadata only.
    """
    master_key = settings.encryption_key
    parts: list[str] = []

    for f in files:
        if f.file_type in ("audio_recording", "image"):
            parts.append(f"[{f.file_type.upper()} — binary file, {f.size_bytes} bytes, hash: {f.content_hash[:16]}...]")
            continue
        try:
            file_key = derive_file_key(master_key, str(f.submission_id), f.content_hash)
            raw = decrypt_bytes(open(f.encrypted_path, "rb").read(), file_key)
            text = raw.decode("utf-8", errors="replace")[:4000]  # cap per file
            parts.append(f"--- [{f.file_type}] ---\n{text}")
        except Exception as exc:
            logger.warning("Could not read file %s: %s", f.content_hash[:16], exc)
            parts.append(f"[{f.file_type} — could not decrypt for analysis]")

    return "\n\n".join(parts)


def analyse_submission(submission_id: str, db: Session) -> None:
    """
    Run LLM analysis on the evidence package and persist the result.
    Updates submission status to ANALYZED.
    """
    submission: Submission | None = db.query(Submission).filter(
        Submission.id == uuid.UUID(submission_id)
    ).first()
    if not submission:
        raise ValueError(f"Submission {submission_id} not found")

    files: list[SubmissionFile] = submission.files
    file_types = [f.file_type or "document" for f in files]

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — using mock analysis")
        result = _mock_analysis(file_types)
    else:
        evidence_text = _read_text_files(files)
        result = _call_openai(evidence_text)

    db_result = AnalysisResult(
        submission_id=uuid.UUID(submission_id),
        overall_confidence=result.overall_confidence,
        consistency_score=result.consistency_score,
        corroboration_score=result.corroboration_score,
        plausibility_score=result.plausibility_score,
        reliability_class=result.reliability_class,
        corroborating_sources=result.corroborating_sources,
        evidence_types=result.evidence_types,
        red_flags=result.red_flags,
        key_claims=result.key_claims_anonymised,
        attribution_quotes=[s.model_dump() for s in result.attribution_sentences],
    )
    db.add(db_result)
    submission.status = "ANALYZED"
    db.commit()
    logger.info(
        "Analysed submission %s: confidence=%d reliability=%s",
        submission_id, result.overall_confidence, result.reliability_class,
    )


def _call_openai(evidence_text: str) -> _AnalysisOutput:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "The following is the decrypted, anonymised content of an evidence package "
                    "submitted to ASVS. All source-identifying information has been stripped by "
                    "the ingestion pipeline prior to this analysis. Apply the scoring methodology "
                    "from your instructions and return the JSON assessment.\n\n"
                    f"--- EVIDENCE PACKAGE BEGIN ---\n\n{evidence_text}\n\n--- EVIDENCE PACKAGE END ---"
                ),
            },
        ],
        response_format=_AnalysisOutput,
        temperature=0.1,
    )
    return response.choices[0].message.parsed
