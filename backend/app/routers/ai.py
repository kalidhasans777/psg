from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_knowledge import AISummary, MedicalKnowledgeDocument
from app.models.clinical import DoctorConsultation, MedicalReport, Symptom
from app.models.patient import Patient
from app.models.user import User
from app.schemas.common import (
    AISummaryReviewRequest,
    CompareReportsRequest,
    PatientOverviewRequest,
    SummarizeConsultationRequest,
    SummarizeHistoryRequest,
    SummarizeReportRequest,
    SummarizeSymptomsRequest,
)
from app.security.auth import (
    authorize_patient_clinical_access,
    get_client_ip,
    get_current_user,
    require_roles,
    resolve_patient_by_identifier,
)
from app.services.audit import create_notification, record_audit_log
from app.summarization.engine import (
    generate_consultation_summary,
    generate_history_summary,
    generate_patient_overview,
    generate_report_comparison_summary,
    generate_report_summary,
    generate_symptom_summary,
)

router = APIRouter(prefix="/api/ai", tags=["AI Medical Summarizer"])


def _serialize_summary(s: AISummary) -> dict:
    return {
        "id": s.id,
        "patient_id": s.patient_id,
        "visit_id": s.visit_id,
        "summary_type": s.summary_type,
        "source_reference": s.source_reference,
        "ai_generated_json": s.ai_generated_json,
        "ai_generated_text": s.ai_generated_text,
        "ai_provider": s.ai_provider,
        "model_identifier": s.model_identifier,
        "disclaimer": s.disclaimer,
        "generation_status": s.generation_status,
        "verification_status": s.verification_status,
        "doctor_edited_text": s.doctor_edited_text,
        "doctor_edited_json": s.doctor_edited_json,
        "reviewing_doctor_id": s.reviewing_doctor_id,
        "review_notes": s.review_notes,
        "review_timestamp": s.review_timestamp.isoformat() if s.review_timestamp else None,
        "created_at": s.created_at.isoformat(),
        "sources": [
            {
                "source_type": src.source_type,
                "source_record_id": src.source_record_id,
                "citation_note": src.citation_note,
            }
            for src in s.sources
        ],
    }


def _resolve_authorized_patient(db: Session, current_user: User, identifier: str | None) -> Patient:
    if current_user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if identifier and own and identifier.upper() != own.permanent_patient_id and identifier != str(own.id):
            raise HTTPException(status_code=403, detail="Access denied: cannot summarize another patient's record.")
        if not own:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        return own
    if not identifier:
        raise HTTPException(status_code=400, detail="patient_identifier is required")
    patient = resolve_patient_by_identifier(db, identifier)
    return authorize_patient_clinical_access(db, current_user, patient)


@router.post("/summarize-symptoms")
def api_summarize_symptoms(
    payload: SummarizeSymptomsRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    symptom = None
    if payload.symptom_id:
        symptom = db.query(Symptom).filter(Symptom.id == payload.symptom_id).first()
        if not symptom:
            raise HTTPException(status_code=404, detail="Symptom not found")
        patient = authorize_patient_clinical_access(db, current_user, symptom.patient)
    else:
        patient = _resolve_authorized_patient(db, current_user, payload.patient_identifier)

    summary = generate_symptom_summary(
        db,
        patient=patient,
        visit_id=payload.visit_id or (symptom.visit_id if symptom else None),
        symptom=symptom,
        raw_text=payload.text,
        language=payload.language,
        duration=payload.duration,
        severity=payload.severity,
        current_medications=payload.current_medications,
    )
    record_audit_log(
        db,
        action="ai_symptom_summary_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.post("/summarize-report")
def api_summarize_report(
    payload: SummarizeReportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(MedicalReport).filter(MedicalReport.id == payload.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")
    patient = authorize_patient_clinical_access(db, current_user, report.patient)

    summary = generate_report_summary(db, patient=patient, report=report)
    record_audit_log(
        db,
        action="ai_report_summary_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.post("/summarize-history")
def api_summarize_history(
    payload: SummarizeHistoryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _resolve_authorized_patient(db, current_user, payload.patient_identifier)
    summary = generate_history_summary(db, patient=patient)
    record_audit_log(
        db,
        action="ai_history_summary_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.post("/summarize-consultation")
def api_summarize_consultation(
    payload: SummarizeConsultationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consult = db.query(DoctorConsultation).filter(DoctorConsultation.id == payload.consultation_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
    patient = authorize_patient_clinical_access(db, current_user, consult.patient)
    summary = generate_consultation_summary(db, patient=patient, consultation=consult)
    record_audit_log(
        db,
        action="ai_consultation_summary_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.post("/patient-overview")
def api_patient_overview(
    payload: PatientOverviewRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor", "patient")),
    db: Session = Depends(get_db),
):
    patient = _resolve_authorized_patient(db, current_user, payload.patient_identifier)
    summary = generate_patient_overview(db, patient=patient, current_visit_id=payload.current_visit_id)
    record_audit_log(
        db,
        action="ai_patient_overview_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.post("/compare-reports")
def api_compare_reports(
    payload: CompareReportsRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor", "patient")),
    db: Session = Depends(get_db),
):
    patient = _resolve_authorized_patient(db, current_user, payload.patient_identifier)
    summary = generate_report_comparison_summary(db, patient=patient, report_ids=payload.report_ids)
    record_audit_log(
        db,
        action="ai_report_comparison_generated",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.get("/summaries/{summary_id}")
def get_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = db.query(AISummary).filter(AISummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="AI summary not found")
    authorize_patient_clinical_access(db, current_user, summary.patient)
    return _serialize_summary(summary)


@router.put("/summaries/{summary_id}/review")
def review_ai_summary(
    summary_id: int,
    payload: AISummaryReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    """
    Doctor verification workflow: Approve, Edit, or Reject an AI summary.
    Original AI output (ai_generated_text / ai_generated_json) is preserved separately from doctor_edited_*!
    """
    summary = db.query(AISummary).filter(AISummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="AI summary not found")

    summary.verification_status = payload.decision
    if payload.edited_text is not None:
        summary.doctor_edited_text = payload.edited_text
    if payload.edited_json is not None:
        summary.doctor_edited_json = payload.edited_json
    summary.review_notes = payload.review_notes
    summary.reviewing_doctor_id = current_user.doctor_profile.id if current_user.doctor_profile else None
    summary.review_timestamp = datetime.now(timezone.utc)
    db.commit()
    db.refresh(summary)

    if summary.patient and summary.patient.user_id:
        create_notification(
            db,
            user_id=summary.patient.user_id,
            title=f"AI Summary {payload.decision.title()}",
            message=f"Dr. {current_user.full_name} reviewed your {summary.summary_type.replace('_', ' ')} summary (Status: {payload.decision}).",
            category="ai_summary",
            related_resource_type="ai_summary",
            related_resource_id=summary.id,
        )

    record_audit_log(
        db,
        action="ai_summary_reviewed",
        resource_type="ai_summary",
        resource_id=str(summary.id),
        user_id=current_user.id,
        user_role="doctor",
        patient_id=summary.patient_id,
        details={"decision": payload.decision, "review_notes": payload.review_notes},
        ip_address=get_client_ip(request),
    )
    return _serialize_summary(summary)


@router.get("/knowledge-sources")
def list_knowledge_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = db.query(MedicalKnowledgeDocument).all()
    return [
        {
            "id": d.id,
            "source_name": d.source_name,
            "document_title": d.document_title,
            "publication_date": d.publication_date,
            "last_updated_date": d.last_updated_date,
            "category": d.category,
            "source_url": d.source_url,
            "version": d.version,
            "retrieval_date": d.retrieval_date,
            "content_snippet": d.content_snippet,
        }
        for d in docs
    ]
