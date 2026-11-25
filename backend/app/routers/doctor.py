from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_knowledge import AISummary
from app.models.clinical import Appointment, DoctorConsultation, MedicalReport, Prescription, Visit
from app.models.patient import Patient
from app.models.user import User
from app.schemas.common import ConsultationCreateRequest, PrescriptionCreateRequest
from app.security.auth import get_client_ip, require_roles
from app.services.audit import create_notification, record_audit_log
from app.services.patient_id import calculate_age
from app.summarization.engine import generate_consultation_summary

router = APIRouter(prefix="/api/doctor", tags=["Doctor Clinical Workspace"])


@router.get("/dashboard")
def doctor_dashboard(
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    doc = current_user.doctor_profile
    today = date.today()

    appts = db.query(Appointment).order_by(Appointment.scheduled_at.asc()).all()
    today_appts = [a for a in appts if a.scheduled_at.date() == today]
    waiting_visits = (
        db.query(Visit)
        .filter(Visit.status.in_(["registered", "in_progress"]))
        .order_by(Visit.visit_date.desc())
        .limit(20)
        .all()
    )
    completed_consults = db.query(DoctorConsultation).count()
    pending_ai = db.query(AISummary).filter(AISummary.verification_status == "pending_verification").count()
    pending_reports = db.query(MedicalReport).filter(MedicalReport.verification_status == "pending").count()

    return {
        "doctor": {
            "id": doc.id if doc else None,
            "full_name": current_user.full_name,
            "specialization": doc.specialization if doc else "General Medicine",
            "department": doc.department.name if doc and doc.department else "General Medicine",
            "license_number": doc.license_number if doc else None,
            "qualification": doc.qualification if doc else None,
            "is_available": doc.is_available if doc else True,
        },
        "stats": {
            "todays_appointments": len(today_appts),
            "waiting_patients": len(waiting_visits),
            "completed_consultations": completed_consults,
            "pending_ai_verification": pending_ai,
            "pending_report_verification": pending_reports,
        },
        "todays_appointments_list": [
            {
                "id": a.id,
                "appointment_code": a.appointment_code,
                "patient_name": a.patient.full_name,
                "permanent_patient_id": a.patient.permanent_patient_id,
                "scheduled_at": a.scheduled_at.isoformat(),
                "reason": a.reason,
                "status": a.status,
            }
            for a in today_appts
        ],
        "waiting_queue": [
            {
                "visit_id": v.id,
                "visit_code": v.visit_code,
                "patient_id": v.patient.id,
                "permanent_patient_id": v.patient.permanent_patient_id,
                "patient_name": v.patient.full_name,
                "age": calculate_age(v.patient.date_of_birth),
                "chief_complaint": v.chief_complaint,
                "visit_date": v.visit_date.isoformat(),
                "status": v.status,
                "pending_ai_count": sum(1 for s in v.ai_summaries if s.verification_status == "pending_verification"),
                "reports_count": len(v.reports),
            }
            for v in waiting_visits
        ],
    }


@router.get("/patients")
def doctor_patients_list(
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    patients = db.query(Patient).order_by(Patient.updated_at.desc()).limit(50).all()
    return [
        {
            "id": p.id,
            "permanent_patient_id": p.permanent_patient_id,
            "full_name": p.full_name,
            "age": calculate_age(p.date_of_birth),
            "gender": p.gender,
            "phone": p.phone,
            "known_allergies": p.known_allergies,
            "existing_conditions": p.existing_conditions,
            "total_visits": len(p.visits),
            "last_visit_date": p.visits[0].visit_date.isoformat() if p.visits else None,
            "is_synthetic_demo": p.is_synthetic_demo,
        }
        for p in patients
    ]


@router.get("/ai-summaries")
def doctor_ai_summaries(
    status_filter: str = "all",
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    q = db.query(AISummary)
    if status_filter != "all":
        q = q.filter(AISummary.verification_status == status_filter)
    items = q.order_by(AISummary.created_at.desc()).limit(50).all()
    return [
        {
            "id": s.id,
            "patient_id": s.patient_id,
            "permanent_patient_id": s.patient.permanent_patient_id if s.patient else None,
            "patient_name": s.patient.full_name if s.patient else None,
            "visit_id": s.visit_id,
            "summary_type": s.summary_type,
            "source_reference": s.source_reference,
            "ai_generated_json": s.ai_generated_json,
            "ai_generated_text": s.ai_generated_text,
            "ai_provider": s.ai_provider,
            "model_identifier": s.model_identifier,
            "disclaimer": s.disclaimer,
            "verification_status": s.verification_status,
            "doctor_edited_text": s.doctor_edited_text,
            "review_notes": s.review_notes,
            "created_at": s.created_at.isoformat(),
        }
        for s in items
    ]


@router.post("/consultations", status_code=status.HTTP_201_CREATED)
def create_consultation(
    payload: ConsultationCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == payload.visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    doc = current_user.doctor_profile
    if not doc:
        raise HTTPException(status_code=403, detail="Doctor profile required")

    consult = DoctorConsultation(
        visit_id=visit.id,
        patient_id=visit.patient_id,
        doctor_id=doc.id,
        chief_complaints=payload.chief_complaints,
        observations=payload.observations,
        clinical_assessment=payload.clinical_assessment,
        diagnosis=payload.diagnosis,
        treatment_plan=payload.treatment_plan,
        follow_up_date=payload.follow_up_date,
        consultation_notes=payload.consultation_notes,
    )
    db.add(consult)
    visit.status = "completed"
    if not visit.doctor_id:
        visit.doctor_id = doc.id
    db.flush()

    created_rx = None
    if payload.medications:
        created_rx = Prescription(
            consultation_id=consult.id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            doctor_id=doc.id,
            medications_json=[m.model_dump() for m in payload.medications],
            instructions=payload.prescription_instructions,
        )
        db.add(created_rx)

    db.commit()
    db.refresh(consult)

    # Also auto-generate Type 4 Consultation Summary (preserving doctor's record separately)
    generate_consultation_summary(db, patient=visit.patient, consultation=consult)

    if visit.patient and visit.patient.user_id:
        fu_text = f" Follow-up scheduled for {payload.follow_up_date}." if payload.follow_up_date else ""
        create_notification(
            db,
            user_id=visit.patient.user_id,
            title="Consultation Completed",
            message=f"Dr. {current_user.full_name} completed your consultation for visit {visit.visit_code}.{fu_text}",
            category="follow_up" if payload.follow_up_date else "system",
            related_resource_type="visit",
            related_resource_id=visit.id,
        )

    record_audit_log(
        db,
        action="doctor_consultation_recorded",
        resource_type="doctor_consultation",
        resource_id=str(consult.id),
        user_id=current_user.id,
        user_role="doctor",
        patient_id=visit.patient_id,
        details={"visit_code": visit.visit_code, "diagnosis": payload.diagnosis},
        ip_address=get_client_ip(request),
    )

    return {
        "id": consult.id,
        "visit_id": visit.id,
        "visit_code": visit.visit_code,
        "diagnosis": consult.diagnosis,
        "follow_up_date": str(consult.follow_up_date) if consult.follow_up_date else None,
        "prescription_id": created_rx.id if created_rx else None,
    }


@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == payload.visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    doc = current_user.doctor_profile
    if not doc:
        raise HTTPException(status_code=403, detail="Doctor profile required")

    rx = Prescription(
        consultation_id=payload.consultation_id,
        visit_id=visit.id,
        patient_id=visit.patient_id,
        doctor_id=doc.id,
        medications_json=[m.model_dump() for m in payload.medications],
        instructions=payload.instructions,
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)

    record_audit_log(
        db,
        action="prescription_issued",
        resource_type="prescription",
        resource_id=str(rx.id),
        user_id=current_user.id,
        user_role="doctor",
        patient_id=visit.patient_id,
        ip_address=get_client_ip(request),
    )
    return {
        "id": rx.id,
        "visit_id": rx.visit_id,
        "issued_date": str(rx.issued_date),
        "medications": rx.medications_json,
        "instructions": rx.instructions,
    }
