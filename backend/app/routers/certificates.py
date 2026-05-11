import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db import Submission, Certificate
from app.models.schemas import CertificateResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_certificate_or_404(submission_id: str, db: Session) -> Certificate:
    try:
        sid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid submission_id format.")

    submission = db.query(Submission).filter(Submission.id == sid).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if submission.status != "COMPLETE":
        raise HTTPException(
            status_code=202,
            detail=f"Certificate not yet ready. Current status: {submission.status}",
        )
    if not submission.certificate:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    return submission.certificate


@router.get("/submissions/{submission_id}/certificate", response_model=CertificateResponse)
def get_certificate(submission_id: str, db: Session = Depends(get_db)):
    """Return the VerificationCertificate JSON for a completed submission."""
    cert = _get_certificate_or_404(submission_id, db)
    return cert.payload


@router.get("/submissions/{submission_id}/certificate.pdf")
def get_certificate_pdf(submission_id: str, db: Session = Depends(get_db)):
    """Generate and return a printable PDF of the verification certificate."""
    cert = _get_certificate_or_404(submission_id, db)
    payload = cert.payload

    try:
        pdf_bytes = _generate_pdf(payload)
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="PDF generation failed.")

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{payload["certificate_id"]}.pdf"'
        },
    )


def _generate_pdf(payload: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=12)
    heading_style = ParagraphStyle("heading", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    body_style = styles["BodyText"]
    mono_style = ParagraphStyle("mono", parent=styles["Code"], fontSize=8, leading=12)

    analysis = payload.get("analysis", {})
    proofs = payload.get("timestamp_proofs", {})

    story.append(Paragraph("Verification Certificate", title_style))
    story.append(Paragraph(f"Certificate ID: {payload['certificate_id']}", body_style))
    story.append(Paragraph(f"Issued: {payload['issued_at']}", body_style))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Confidence Scores", heading_style))
    score_data = [
        ["Dimension", "Score"],
        ["Overall Confidence", f"{analysis.get('overall_confidence', '—')}/100"],
        ["Consistency", f"{analysis.get('consistency_score', '—')}/100"],
        ["Corroboration", f"{analysis.get('corroboration_score', '—')}/100"],
        ["Plausibility", f"{analysis.get('plausibility_score', '—')}/100"],
        ["Reliability Class", analysis.get("reliability_class", "—")],
    ]
    t = Table(score_data, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    if rfc := proofs.get("rfc3161"):
        story.append(Paragraph("RFC 3161 Timestamp Proof", heading_style))
        story.append(Paragraph(f"TSA: {rfc.get('tsa')}", body_style))
        story.append(Paragraph(f"Algorithm: {rfc.get('tsa_cert_algorithm')}", body_style))
        story.append(Paragraph(f"Timestamp: {rfc.get('timestamp')}", body_style))
        story.append(Paragraph(f"Token hash: {rfc.get('token_hash', '')[:32]}...", mono_style))
        story.append(Spacer(1, 0.3 * cm))

    if ots := proofs.get("opentimestamps"):
        story.append(Paragraph("OpenTimestamps (Bitcoin) Proof", heading_style))
        confirmed = ots.get("confirmed", False)
        story.append(Paragraph(f"Confirmed: {'Yes' if confirmed else 'Pending'}", body_style))
        if ots.get("bitcoin_block"):
            story.append(Paragraph(f"Bitcoin block: {ots['bitcoin_block']}", body_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Attribution Language", heading_style))
    for line in payload.get("attribution_language", []):
        story.append(Paragraph(f"• {line}", body_style))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "This certificate attests to provenance and integrity, not to the truth of the underlying allegations.",
        ParagraphStyle("disclaimer", parent=styles["Italic"], fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    return buf.getvalue()
