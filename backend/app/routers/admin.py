from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_knowledge import AISummary, AuditLog
from app.models.clinical import Appointment, MedicalReport, Visit
from app.models.patient import Patient
from app.models.user import Department, Doctor, User
from app.schemas.common import (
    DepartmentCreateRequest,
    DoctorCreateRequest,
    DoctorUpdateRequest,
    PatientStatusUpdateRequest,
)
from app.security.auth import get_client_ip, hash_password, require_roles
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/admin", tags=["Hospital Administration"])


@router.get("/dashboard")
def admin_dashboard(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    today = date.today()
    visits = db.query(Visit).all()
    todays_visits = sum(1 for v in visits if v.visit_date.date() == today)
    upcoming_appts = db.query(Appointment).filter(Appointment.status.in_(["scheduled", "confirmed"])).count()

    ai_summaries = db.query(AISummary).all()
    reports = db.query(MedicalReport).all()

    return {
        "stats": {
            "total_patients": db.query(Patient).count(),
            "total_doctors": db.query(Doctor).count(),
            "todays_visits": todays_visits,
            "total_visits": len(visits),
            "upcoming_appointments": upcoming_appts,
            "total_departments": db.query(Department).count(),
        },
        "ai_monitor": {
            "pending_summaries": sum(1 for s in ai_summaries if s.generation_status == "pending"),
            "completed_summaries": sum(1 for s in ai_summaries if s.generation_status == "completed"),
            "failed_ai_requests": sum(1 for s in ai_summaries if s.generation_status == "failed"),
            "pending_doctor_verification": sum(1 for s in ai_summaries if s.verification_status == "pending_verification"),
            "approved_summaries": sum(1 for s in ai_summaries if s.verification_status in ("approved", "edited")),
            "pending_report_extraction": sum(1 for r in reports if r.processing_status in ("pending", "processing")),
            "failed_ocr_jobs": sum(1 for r in reports if r.processing_status == "failed"),
        },
    }


@router.get("/patients")
def admin_list_patients(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Returns administrative patient details only (clinical symptoms & doctor notes are omitted)."""
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "permanent_patient_id": p.permanent_patient_id,
            "full_name": p.full_name,
            "phone": p.phone,
            "email": p.email,
            "registration_date": str(p.registration_date),
            "account_status": p.account_status,
            "consent_status": p.consent_status,
            "total_visits": len(p.visits),
            "is_synthetic_demo": p.is_synthetic_demo,
        }
        for p in patients
    ]


@router.put("/patients/{patient_id}/status")
def admin_update_patient_status(
    patient_id: int,
    payload: PatientStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    old_status = patient.account_status
    patient.account_status = payload.account_status
    if patient.user:
        patient.user.is_active = payload.account_status == "active"
    db.commit()

    record_audit_log(
        db,
        action="patient_account_status_changed",
        resource_type="patient",
        resource_id=patient.permanent_patient_id,
        user_id=current_user.id,
        user_role="admin",
        patient_id=patient.id,
        details={"old_status": old_status, "new_status": payload.account_status},
        ip_address=get_client_ip(request),
    )
    return {"id": patient.id, "permanent_patient_id": patient.permanent_patient_id, "account_status": patient.account_status}


@router.get("/doctors")
def admin_list_doctors(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    doctors = db.query(Doctor).all()
    return [
        {
            "id": d.id,
            "user_id": d.user_id,
            "full_name": d.user.full_name,
            "email": d.user.email,
            "phone": d.phone or d.user.phone,
            "department_id": d.department_id,
            "department_name": d.department.name if d.department else None,
            "license_number": d.license_number,
            "specialization": d.specialization,
            "qualification": d.qualification,
            "is_available": d.is_available,
            "is_active": d.is_active,
        }
        for d in doctors
    ]


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
def admin_create_doctor(
    payload: DoctorCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(or_(User.email == payload.email.lower(), User.phone == payload.phone)).first():
        raise HTTPException(status_code=409, detail="Email or phone already in use")
    if db.query(Doctor).filter(Doctor.license_number == payload.license_number).first():
        raise HTTPException(status_code=409, detail="License number already exists")
    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    user = User(
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="doctor",
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    doc = Doctor(
        user_id=user.id,
        department_id=payload.department_id,
        license_number=payload.license_number,
        specialization=payload.specialization,
        qualification=payload.qualification,
        phone=payload.phone,
        is_available=True,
        is_active=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    record_audit_log(
        db,
        action="doctor_account_created",
        resource_type="doctor",
        resource_id=str(doc.id),
        user_id=current_user.id,
        user_role="admin",
        details={"doctor_name": payload.full_name, "department": dept.name},
        ip_address=get_client_ip(request),
    )
    return {"id": doc.id, "full_name": user.full_name, "department": dept.name, "license_number": doc.license_number}


@router.put("/doctors/{doctor_id}")
def admin_update_doctor(
    doctor_id: int,
    payload: DoctorUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    for field in ("department_id", "specialization", "qualification", "is_available", "is_active"):
        val = getattr(payload, field)
        if val is not None:
            setattr(doc, field, val)
    if payload.is_active is not None and doc.user:
        doc.user.is_active = payload.is_active
    db.commit()
    db.refresh(doc)

    record_audit_log(
        db,
        action="doctor_updated",
        resource_type="doctor",
        resource_id=str(doc.id),
        user_id=current_user.id,
        user_role="admin",
        ip_address=get_client_ip(request),
    )
    return {"id": doc.id, "is_available": doc.is_available, "is_active": doc.is_active}


@router.get("/departments")
def admin_list_departments(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    depts = db.query(Department).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "description": d.description,
            "head_doctor_name": d.head_doctor_name,
            "doctor_count": len(d.doctors),
            "is_active": d.is_active,
        }
        for d in depts
    ]


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def admin_create_department(
    payload: DepartmentCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if db.query(Department).filter(or_(Department.name == payload.name, Department.code == payload.code)).first():
        raise HTTPException(status_code=409, detail="Department name or code already exists")
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)

    record_audit_log(
        db,
        action="department_created",
        resource_type="department",
        resource_id=str(dept.id),
        user_id=current_user.id,
        user_role="admin",
        details={"name": dept.name, "code": dept.code},
        ip_address=get_client_ip(request),
    )
    return {"id": dept.id, "name": dept.name, "code": dept.code}


@router.get("/ai-monitor")
def admin_ai_monitor(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Operational status monitor only — hides private clinical text."""
    summaries = db.query(AISummary).order_by(AISummary.created_at.desc()).limit(30).all()
    reports = db.query(MedicalReport).order_by(MedicalReport.created_at.desc()).limit(30).all()
    return {
        "ai_jobs": [
            {
                "id": s.id,
                "summary_type": s.summary_type,
                "ai_provider": s.ai_provider,
                "model_identifier": s.model_identifier,
                "generation_status": s.generation_status,
                "verification_status": s.verification_status,
                "created_at": s.created_at.isoformat(),
            }
            for s in summaries
        ],
        "report_jobs": [
            {
                "id": r.id,
                "category": r.category,
                "processing_status": r.processing_status,
                "verification_status": r.verification_status,
                "upload_date": r.upload_date.isoformat(),
            }
            for r in reports
        ],
    }


@router.get("/audit-logs")
def admin_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "user_role": l.user_role,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "status": l.status,
            "ip_address": l.ip_address,
            "details": l.details_json,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
