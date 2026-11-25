from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinical import Symptom, Visit
from app.models.patient import Patient, PatientConsent
from app.models.user import User
from app.schemas.common import VoiceAssistantTurnRequest, VoiceConfirmTranscriptRequest
from app.security.auth import get_client_ip, get_current_user, require_roles
from app.services.audit import record_audit_log
from app.services.patient_id import generate_visit_code
from app.summarization.engine import generate_symptom_summary
from app.voice.provider import (
    get_active_speech_provider,
    get_voice_capabilities,
    process_voice_assistant_turn,
)

router = APIRouter(prefix="/api/voice", tags=["Tamil-First Voice Assistant"])


@router.get("/capabilities")
def voice_capabilities():
    return get_voice_capabilities()


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("ta-IN"),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribes uploaded microphone audio using configured cloud speech provider (Google Cloud / Azure).
    Audio is processed in-memory and NOT unnecessarily persisted on disk.
    """
    provider = get_active_speech_provider()
    if not provider:
        return {
            "success": False,
            "configured": False,
            "provider": None,
            "fallback": "browser_webspeech",
            "message": "No server-side Cloud Speech API key (Google Cloud Speech or Azure Speech) is configured. Use Browser Web Speech API (ta-IN / en-IN) or manual typing.",
        }

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    return await provider.transcribe_audio(audio_bytes, audio.content_type or "audio/webm", language)


@router.post("/assistant")
def voice_assistant_turn(
    payload: VoiceAssistantTurnRequest,
    current_user: User = Depends(get_current_user),
):
    return process_voice_assistant_turn(
        language=payload.language,
        step=payload.step,
        patient_utterance=payload.patient_utterance,
        collected_data=payload.collected_data,
    )


@router.post("/confirm-transcript")
def confirm_voice_transcript(
    payload: VoiceConfirmTranscriptRequest,
    request: Request,
    current_user: User = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """
    Saves patient-confirmed Tamil/English voice transcript to a visit and generates AI symptom summary.
    Requires explicit patient confirmation and records voice processing consent.
    """
    if not payload.audio_consent:
        raise HTTPException(status_code=400, detail="Patient consent for voice transcript processing is required.")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    ip = get_client_ip(request)
    db.add(
        PatientConsent(
            patient_id=patient.id,
            consent_type="voice_processing",
            consented=True,
            consent_version="1.0",
            ip_address=ip,
        )
    )

    if payload.visit_id:
        visit = db.query(Visit).filter(Visit.id == payload.visit_id, Visit.patient_id == patient.id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
    else:
        # Use latest open visit or create a new visit record automatically
        visit = (
            db.query(Visit)
            .filter(Visit.patient_id == patient.id, Visit.status.in_(["registered", "in_progress"]))
            .order_by(Visit.visit_date.desc())
            .first()
        )
        if not visit:
            visit = Visit(
                visit_code=generate_visit_code(db),
                patient_id=patient.id,
                visit_type="outpatient",
                chief_complaint=payload.confirmed_transcript[:200],
                status="registered",
            )
            db.add(visit)
            db.flush()

    source_channel = "voice_ta" if payload.language.startswith("ta") else "voice_mixed" if payload.language == "mixed" else "voice_en"
    symptom = Symptom(
        visit_id=visit.id,
        patient_id=patient.id,
        source_channel=source_channel,
        language=payload.language,
        raw_transcript=payload.raw_transcript,
        edited_transcript=payload.confirmed_transcript,
        description=payload.confirmed_transcript,
        duration=payload.duration,
        severity=payload.severity,
        additional_details=payload.additional_details,
        current_medications=payload.current_medications,
        patient_confirmed=True,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(symptom)
    if not visit.chief_complaint:
        visit.chief_complaint = payload.confirmed_transcript[:200]
    db.commit()
    db.refresh(symptom)
    db.refresh(visit)

    ai_summary_data = None
    if payload.generate_ai_summary:
        summary = generate_symptom_summary(
            db,
            patient=patient,
            visit_id=visit.id,
            symptom=symptom,
            raw_text=payload.confirmed_transcript,
            language=payload.language,
            duration=payload.duration,
            severity=payload.severity,
            current_medications=payload.current_medications,
        )
        ai_summary_data = {
            "id": summary.id,
            "disclaimer": summary.disclaimer,
            "ai_provider": summary.ai_provider,
            "verification_status": summary.verification_status,
            "ai_generated_json": summary.ai_generated_json,
            "ai_generated_text": summary.ai_generated_text,
        }

    record_audit_log(
        db,
        action="voice_transcript_confirmed",
        resource_type="symptom",
        resource_id=str(symptom.id),
        user_id=current_user.id,
        user_role="patient",
        patient_id=patient.id,
        details={"visit_code": visit.visit_code, "language": payload.language},
        ip_address=ip,
    )

    return {
        "visit_id": visit.id,
        "visit_code": visit.visit_code,
        "symptom_id": symptom.id,
        "confirmed_transcript": symptom.edited_transcript,
        "ai_summary": ai_summary_data,
    }
