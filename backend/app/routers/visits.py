from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinical import Symptom, Visit
from app.models.patient import Patient
from app.models.user import User
from app.schemas.common import SymptomCreateRequest, VisitCreateRequest
from app.security.auth import (
    authorize_patient_clinical_access,
    get_client_ip,
    get_current_user,
    resolve_patient_by_identifier,
)
from app.services.audit import record_audit_log
from app.services.patient_id import generate_visit_code
from app.summarization.engine import generate_symptom_summary

router = APIRouter(prefix="/api/visits", tags=["Visits & Symptoms"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_visit(
    payload: VisitCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new separate visit record connected to the patient's permanent ID. Never overwrites prior visits."""
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    elif current_user.role in ("doctor", "admin"):
        if not payload.patient_identifier:
            raise HTTPException(status_code=400, detail="patient_identifier (e.g. MED-2026-00125) is required")
        patient = resolve_patient_by_identifier(db, payload.patient_identifier)
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visit = Visit(
        visit_code=generate_visit_code(db),
        patient_id=patient.id,
        doctor_id=payload.doctor_id or (current_user.doctor_profile.id if current_user.role == "doctor" and current_user.doctor_profile else None),
        department_id=payload.department_id or (current_user.doctor_profile.department_id if current_user.role == "doctor" and current_user.doctor_profile else None),
        visit_date=payload.visit_date or datetime.now(timezone.utc),
        visit_type=payload.visit_type,
        chief_complaint=payload.chief_complaint,
        status="registered",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    record_audit_log(
        db,
        action="visit_created",
        resource_type="visit",
        resource_id=visit.visit_code,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        details={"visit_id": visit.id, "permanent_patient_id": patient.permanent_patient_id},
        ip_address=get_client_ip(request),
    )

    return {
        "id": visit.id,
        "visit_code": visit.visit_code,
        "patient_id": patient.id,
        "permanent_patient_id": patient.permanent_patient_id,
        "visit_date": visit.visit_date.isoformat(),
        "visit_type": visit.visit_type,
        "chief_complaint": visit.chief_complaint,
        "status": visit.status,
    }


@router.get("/{visit_id}")
def get_visit(
    visit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    authorize_patient_clinical_access(db, current_user, visit.patient)

    return {
        "id": visit.id,
        "visit_code": visit.visit_code,
        "permanent_patient_id": visit.patient.permanent_patient_id,
        "visit_date": visit.visit_date.isoformat(),
        "visit_type": visit.visit_type,
        "chief_complaint": visit.chief_complaint,
        "status": visit.status,
        "symptoms": [
            {
                "id": s.id,
                "source_channel": s.source_channel,
                "language": s.language,
                "raw_transcript": s.raw_transcript,
                "edited_transcript": s.edited_transcript,
                "description": s.description,
                "duration": s.duration,
                "severity": s.severity,
                "current_medications": s.current_medications,
                "created_at": s.created_at.isoformat(),
            }
            for s in visit.symptoms
        ],
    }


@router.post("/{visit_id}/symptoms", status_code=status.HTTP_201_CREATED)
def add_visit_symptom(
    visit_id: int,
    payload: SymptomCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patient = authorize_patient_clinical_access(db, current_user, visit.patient)

    symptom = Symptom(
        visit_id=visit.id,
        patient_id=patient.id,
        source_channel=payload.source_channel,
        language=payload.language,
        raw_transcript=payload.raw_transcript,
        edited_transcript=payload.edited_transcript,
        description=payload.description.strip(),
        duration=payload.duration,
        severity=payload.severity,
        onset_date=payload.onset_date,
        additional_details=payload.additional_details,
        current_medications=payload.current_medications,
        patient_confirmed=payload.patient_confirmed,
        confirmed_at=datetime.now(timezone.utc) if payload.patient_confirmed else None,
    )
    db.add(symptom)
    if not visit.chief_complaint:
        visit.chief_complaint = payload.description.strip()[:250]
    db.commit()
    db.refresh(symptom)

    # Automatically generate structured AI Symptom Summary
    ai_summary = generate_symptom_summary(
        db,
        patient=patient,
        visit_id=visit.id,
        symptom=symptom,
        raw_text=payload.edited_transcript or payload.raw_transcript or payload.description,
        language=payload.language,
        duration=payload.duration,
        severity=payload.severity,
        current_medications=payload.current_medications,
    )

    record_audit_log(
        db,
        action="symptom_logged",
        resource_type="symptom",
        resource_id=str(symptom.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        details={"visit_id": visit.id, "ai_summary_id": ai_summary.id},
        ip_address=get_client_ip(request),
    )

    return {
        "symptom": {
            "id": symptom.id,
            "visit_id": visit.id,
            "description": symptom.description,
            "duration": symptom.duration,
            "severity": symptom.severity,
            "language": symptom.language,
            "created_at": symptom.created_at.isoformat(),
        },
        "ai_summary": {
            "id": ai_summary.id,
            "disclaimer": ai_summary.disclaimer,
            "ai_provider": ai_summary.ai_provider,
            "verification_status": ai_summary.verification_status,
            "ai_generated_json": ai_summary.ai_generated_json,
            "ai_generated_text": ai_summary.ai_generated_text,
        },
    }
