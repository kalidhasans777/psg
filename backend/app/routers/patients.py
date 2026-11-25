from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_knowledge import AISummary
from app.models.clinical import Appointment, DoctorConsultation, MedicalReport, Prescription, Visit
from app.models.patient import Notification, Patient, PatientConsent
from app.models.user import User
from app.schemas.common import PatientOut, PatientRegisterRequest, PatientUpdateRequest
from app.security.auth import (
    authorize_patient_clinical_access,
    get_client_ip,
    get_current_user,
    hash_password,
    require_roles,
    resolve_patient_by_identifier,
)
from app.services.audit import record_audit_log
from app.services.patient_id import calculate_age, generate_permanent_patient_id

router = APIRouter(prefix="/api/patients", tags=["Patients & Medical History"])


def _patient_to_dict(p: Patient) -> dict:
    return PatientOut(
        id=p.id,
        user_id=p.user_id,
        permanent_patient_id=p.permanent_patient_id,
        full_name=p.full_name,
        date_of_birth=p.date_of_birth,
        age=calculate_age(p.date_of_birth),
        gender=p.gender,
        phone=p.phone,
        email=p.email,
        address=p.address,
        emergency_contact=p.emergency_contact,
        known_allergies=p.known_allergies,
        existing_conditions=p.existing_conditions,
        relevant_medical_history=p.relevant_medical_history,
        blood_group=p.blood_group,
        registration_date=p.registration_date,
        account_status=p.account_status,
        consent_status=p.consent_status,
        is_synthetic_demo=p.is_synthetic_demo,
        created_at=p.created_at,
    ).model_dump()


@router.post("", status_code=status.HTTP_201_CREATED)
def staff_create_patient(
    payload: PatientRegisterRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor", "admin")),
    db: Session = Depends(get_db),
):
    """Hospital staff-assisted registration with duplicate detection & permanent ID generation."""
    ip = get_client_ip(request)
    existing_patient = (
        db.query(Patient)
        .filter(Patient.phone == payload.phone.strip(), Patient.date_of_birth == payload.date_of_birth)
        .first()
    )
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Returning patient detected with Permanent ID {existing_patient.permanent_patient_id}. Retrieve existing profile instead of creating a duplicate.",
        )

    filters = [User.phone == payload.phone.strip()]
    if payload.email:
        filters.append(User.email == payload.email.lower().strip())
    if db.query(User).filter(or_(*filters)).first():
        raise HTTPException(status_code=409, detail="Phone or email already registered to a user account.")

    user = User(
        email=payload.email.lower().strip() if payload.email else None,
        phone=payload.phone.strip(),
        password_hash=hash_password(payload.password),
        role="patient",
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    db.add(user)
    db.flush()

    pid = generate_permanent_patient_id(db)
    patient = Patient(
        user_id=user.id,
        permanent_patient_id=pid,
        full_name=payload.full_name.strip(),
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        phone=payload.phone.strip(),
        email=payload.email.lower().strip() if payload.email else None,
        address=payload.address.strip(),
        emergency_contact=payload.emergency_contact,
        known_allergies=payload.known_allergies,
        existing_conditions=payload.existing_conditions,
        relevant_medical_history=payload.relevant_medical_history,
        blood_group=payload.blood_group,
        consent_status=payload.consent_accepted,
    )
    db.add(patient)
    db.flush()
    db.add(PatientConsent(patient_id=patient.id, consent_type="privacy_policy", consented=True, ip_address=ip))
    db.commit()
    db.refresh(patient)

    record_audit_log(
        db,
        action="staff_registered_patient",
        resource_type="patient",
        resource_id=patient.permanent_patient_id,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=ip,
    )
    return _patient_to_dict(patient)


@router.get("/me")
def get_my_patient_profile(
    current_user: User = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    visits = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.desc()).all()
    reports_count = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id).count()
    upcoming_appts = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient.id, Appointment.status.in_(["scheduled", "confirmed", "checked_in"]))
        .order_by(Appointment.scheduled_at.asc())
        .all()
    )
    recent_notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "patient": _patient_to_dict(patient),
        "stats": {
            "total_visits": len(visits),
            "uploaded_reports": reports_count,
            "previous_visit_date": visits[0].visit_date.isoformat() if visits else None,
            "upcoming_appointment": (
                {
                    "id": upcoming_appts[0].id,
                    "appointment_code": upcoming_appts[0].appointment_code,
                    "scheduled_at": upcoming_appts[0].scheduled_at.isoformat(),
                    "doctor_name": upcoming_appts[0].doctor.user.full_name if upcoming_appts[0].doctor and upcoming_appts[0].doctor.user else None,
                    "department": upcoming_appts[0].department.name if upcoming_appts[0].department else None,
                    "status": upcoming_appts[0].status,
                }
                if upcoming_appts
                else None
            ),
        },
        "recent_notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in recent_notifs
        ],
    }


@router.put("/me")
def update_my_patient_profile(
    payload: PatientUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    changes = {}
    for field in ("phone", "email", "address", "emergency_contact", "known_allergies", "existing_conditions", "blood_group"):
        val = getattr(payload, field)
        if val is not None:
            changes[field] = {"old": getattr(patient, field), "new": val}
            setattr(patient, field, val)

    if payload.phone:
        current_user.phone = payload.phone
    if payload.email:
        current_user.email = payload.email.lower()

    db.commit()
    db.refresh(patient)

    record_audit_log(
        db,
        action="patient_profile_updated",
        resource_type="patient",
        resource_id=patient.permanent_patient_id,
        user_id=current_user.id,
        user_role="patient",
        patient_id=patient.id,
        details=changes,
        ip_address=get_client_ip(request),
    )
    return _patient_to_dict(patient)


@router.get("/notifications/me")
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in items
    ]


@router.put("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "ok"}


@router.get("/search")
def search_patients(
    q: str = Query(..., min_length=2, description="Permanent Patient ID (e.g. MED-2026-00125), name, or phone"),
    request: Request = None,
    current_user: User = Depends(require_roles("doctor", "admin")),
    db: Session = Depends(get_db),
):
    term = q.strip()
    matches = (
        db.query(Patient)
        .filter(
            or_(
                Patient.permanent_patient_id.ilike(f"%{term}%"),
                Patient.full_name.ilike(f"%{term}%"),
                Patient.phone.ilike(f"%{term}%"),
            )
        )
        .limit(20)
        .all()
    )
    record_audit_log(
        db,
        action="patient_search",
        resource_type="patient",
        resource_id=term,
        user_id=current_user.id,
        user_role=current_user.role,
        details={"query": term, "result_count": len(matches)},
        ip_address=get_client_ip(request),
    )

    if current_user.role == "admin":
        # Admin receives administrative identification metadata only
        return [
            {
                "id": p.id,
                "permanent_patient_id": p.permanent_patient_id,
                "full_name": p.full_name,
                "phone": p.phone,
                "registration_date": str(p.registration_date),
                "account_status": p.account_status,
                "is_synthetic_demo": p.is_synthetic_demo,
            }
            for p in matches
        ]

    return [_patient_to_dict(p) for p in matches]


@router.get("/{patient_identifier}")
def get_patient_detail(
    patient_identifier: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    patient = resolve_patient_by_identifier(db, patient_identifier)
    try:
        patient = authorize_patient_clinical_access(db, current_user, patient, allow_admin_clinical=False)
    except HTTPException as exc:
        record_audit_log(
            db,
            action="patient_record_access_denied",
            resource_type="patient",
            resource_id=patient_identifier,
            user_id=current_user.id,
            user_role=current_user.role,
            patient_id=patient.id if patient else None,
            details={"reason": exc.detail},
            ip_address=ip,
            status="denied",
        )
        raise

    record_audit_log(
        db,
        action="patient_record_viewed",
        resource_type="patient",
        resource_id=patient.permanent_patient_id,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=ip,
    )
    return _patient_to_dict(patient)


@router.get("/{patient_identifier}/history")
def get_patient_complete_history(
    patient_identifier: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    patient = resolve_patient_by_identifier(db, patient_identifier)
    try:
        patient = authorize_patient_clinical_access(db, current_user, patient, allow_admin_clinical=False)
    except HTTPException as exc:
        record_audit_log(
            db,
            action="patient_history_access_denied",
            resource_type="patient_history",
            resource_id=patient_identifier,
            user_id=current_user.id,
            user_role=current_user.role,
            patient_id=patient.id if patient else None,
            details={"reason": exc.detail},
            ip_address=ip,
            status="denied",
        )
        raise

    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient.id)
        .order_by(Visit.visit_date.desc(), Visit.id.desc())
        .all()
    )

    timeline = []
    for v in visits:
        timeline.append(
            {
                "id": v.id,
                "visit_code": v.visit_code,
                "visit_date": v.visit_date.isoformat(),
                "visit_year": v.visit_date.year,
                "visit_type": v.visit_type,
                "chief_complaint": v.chief_complaint,
                "status": v.status,
                "department_name": v.department.name if v.department else None,
                "doctor_name": v.doctor.user.full_name if v.doctor and v.doctor.user else None,
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
                        "additional_details": s.additional_details,
                        "current_medications": s.current_medications,
                        "patient_confirmed": s.patient_confirmed,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in v.symptoms
                ],
                "reports": [
                    {
                        "id": r.id,
                        "category": r.category,
                        "file_name": r.file_name,
                        "mime_type": r.mime_type,
                        "report_date": str(r.report_date),
                        "upload_date": r.upload_date.isoformat(),
                        "processing_status": r.processing_status,
                        "verification_status": r.verification_status,
                        "ocr_confidence_note": r.ocr_confidence_note,
                        "extracted_text": r.extracted_text,
                        "findings": [
                            {
                                "id": f.id,
                                "test_name": f.test_name,
                                "observed_value": f.observed_value,
                                "unit": f.unit,
                                "reference_range": f.reference_range,
                                "status_relative_to_range": f.status_relative_to_range,
                                "is_uncertain": f.is_uncertain,
                                "doctor_corrected": f.doctor_corrected,
                            }
                            for f in r.findings
                        ],
                    }
                    for r in v.reports
                ],
                "ai_summaries": [
                    {
                        "id": a.id,
                        "summary_type": a.summary_type,
                        "source_reference": a.source_reference,
                        "ai_generated_json": a.ai_generated_json,
                        "ai_generated_text": a.ai_generated_text,
                        "ai_provider": a.ai_provider,
                        "model_identifier": a.model_identifier,
                        "disclaimer": a.disclaimer,
                        "verification_status": a.verification_status,
                        "doctor_edited_text": a.doctor_edited_text,
                        "review_notes": a.review_notes,
                        "review_timestamp": a.review_timestamp.isoformat() if a.review_timestamp else None,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in v.ai_summaries
                ],
                "consultations": [
                    {
                        "id": c.id,
                        "doctor_name": c.doctor.user.full_name if c.doctor and c.doctor.user else None,
                        "chief_complaints": c.chief_complaints,
                        "observations": c.observations,
                        "clinical_assessment": c.clinical_assessment,
                        "diagnosis": c.diagnosis,
                        "treatment_plan": c.treatment_plan,
                        "follow_up_date": str(c.follow_up_date) if c.follow_up_date else None,
                        "consultation_notes": c.consultation_notes,
                        "created_at": c.created_at.isoformat(),
                    }
                    for c in v.consultations
                ],
                "prescriptions": [
                    {
                        "id": p.id,
                        "doctor_name": p.doctor.user.full_name if p.doctor and p.doctor.user else None,
                        "medications": p.medications_json,
                        "instructions": p.instructions,
                        "issued_date": str(p.issued_date),
                    }
                    for p in v.prescriptions
                ],
            }
        )

    # Also return patient-level summaries (e.g., history / overview / comparisons without single visit)
    patient_level_summaries = [
        {
            "id": a.id,
            "visit_id": a.visit_id,
            "summary_type": a.summary_type,
            "source_reference": a.source_reference,
            "ai_generated_json": a.ai_generated_json,
            "ai_generated_text": a.ai_generated_text,
            "ai_provider": a.ai_provider,
            "model_identifier": a.model_identifier,
            "disclaimer": a.disclaimer,
            "verification_status": a.verification_status,
            "doctor_edited_text": a.doctor_edited_text,
            "review_notes": a.review_notes,
            "created_at": a.created_at.isoformat(),
        }
        for a in db.query(AISummary).filter(AISummary.patient_id == patient.id).order_by(AISummary.created_at.desc()).all()
    ]

    record_audit_log(
        db,
        action="patient_history_viewed",
        resource_type="patient_history",
        resource_id=patient.permanent_patient_id,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=ip,
    )

    return {
        "patient": _patient_to_dict(patient),
        "total_visits": len(timeline),
        "visits": timeline,
        "all_ai_summaries": patient_level_summaries,
    }


@router.get("/{patient_identifier}/visits")
def get_patient_visits(
    patient_identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = resolve_patient_by_identifier(db, patient_identifier)
    patient = authorize_patient_clinical_access(db, current_user, patient, allow_admin_clinical=False)
    visits = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.desc()).all()
    return [
        {
            "id": v.id,
            "visit_code": v.visit_code,
            "visit_date": v.visit_date.isoformat(),
            "visit_type": v.visit_type,
            "chief_complaint": v.chief_complaint,
            "status": v.status,
            "department_name": v.department.name if v.department else None,
            "doctor_name": v.doctor.user.full_name if v.doctor and v.doctor.user else None,
        }
        for v in visits
    ]
