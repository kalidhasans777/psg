from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinical import Appointment
from app.models.patient import Patient
from app.models.user import Department, Doctor, User
from app.schemas.common import AppointmentCreateRequest, AppointmentUpdateRequest
from app.security.auth import get_client_ip, get_current_user, resolve_patient_by_identifier
from app.services.audit import create_notification, record_audit_log
from app.services.patient_id import generate_appointment_code

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.get("/departments-doctors")
def list_departments_and_doctors(db: Session = Depends(get_db)):
    depts = db.query(Department).filter(Department.is_active.is_(True)).all()
    docs = db.query(Doctor).filter(Doctor.is_active.is_(True)).all()
    return {
        "departments": [{"id": d.id, "name": d.name, "code": d.code, "description": d.description} for d in depts],
        "doctors": [
            {
                "id": doc.id,
                "full_name": doc.user.full_name,
                "department_id": doc.department_id,
                "department_name": doc.department.name if doc.department else None,
                "specialization": doc.specialization,
                "is_available": doc.is_available,
            }
            for doc in docs
        ],
    }


@router.get("")
def list_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Appointment)
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        q = q.filter(Appointment.patient_id == patient.id)
    elif current_user.role == "doctor" and current_user.doctor_profile:
        q = q.filter(Appointment.doctor_id == current_user.doctor_profile.id)

    appts = q.order_by(Appointment.scheduled_at.desc()).all()
    return [_serialize_appointment(a) for a in appts]


def _serialize_appointment(a: Appointment) -> dict:
    return {
        "id": a.id,
        "appointment_code": a.appointment_code,
        "patient_id": a.patient_id,
        "permanent_patient_id": a.patient.permanent_patient_id if a.patient else None,
        "patient_name": a.patient.full_name if a.patient else None,
        "doctor_id": a.doctor_id,
        "doctor_name": a.doctor.user.full_name if a.doctor and a.doctor.user else None,
        "department_id": a.department_id,
        "department_name": a.department.name if a.department else None,
        "scheduled_at": a.scheduled_at.isoformat(),
        "reason": a.reason,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    else:
        if not payload.patient_identifier:
            raise HTTPException(status_code=400, detail="patient_identifier is required")
        patient = resolve_patient_by_identifier(db, payload.patient_identifier)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doc = db.query(Doctor).filter(Doctor.id == payload.doctor_id).first()
    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not doc or not dept:
        raise HTTPException(status_code=404, detail="Doctor or department not found")

    appt = Appointment(
        appointment_code=generate_appointment_code(db),
        patient_id=patient.id,
        doctor_id=doc.id,
        department_id=dept.id,
        scheduled_at=payload.scheduled_at,
        reason=payload.reason,
        status="confirmed" if current_user.role in ("admin", "doctor") else "scheduled",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    if patient.user_id:
        create_notification(
            db,
            user_id=patient.user_id,
            title="Appointment Scheduled",
            message=f"Appointment {appt.appointment_code} with Dr. {doc.user.full_name} ({dept.name}) is {appt.status} for {appt.scheduled_at.strftime('%Y-%m-%d %H:%M')}.",
            category="appointment",
            related_resource_type="appointment",
            related_resource_id=appt.id,
        )
    if doc.user_id:
        create_notification(
            db,
            user_id=doc.user_id,
            title="New Patient Appointment",
            message=f"{patient.full_name} ({patient.permanent_patient_id}) scheduled for {appt.scheduled_at.strftime('%Y-%m-%d %H:%M')}.",
            category="appointment",
            related_resource_type="appointment",
            related_resource_id=appt.id,
        )

    record_audit_log(
        db,
        action="appointment_created",
        resource_type="appointment",
        resource_id=appt.appointment_code,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        ip_address=get_client_ip(request),
    )
    return _serialize_appointment(appt)


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role == "patient" and appt.patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if payload.status:
        appt.status = payload.status
    if payload.doctor_id and current_user.role in ("admin", "doctor"):
        appt.doctor_id = payload.doctor_id
    if payload.scheduled_at:
        appt.scheduled_at = payload.scheduled_at
    if payload.notes is not None:
        appt.notes = payload.notes

    db.commit()
    db.refresh(appt)

    if appt.patient and appt.patient.user_id:
        create_notification(
            db,
            user_id=appt.patient.user_id,
            title="Appointment Updated",
            message=f"Appointment {appt.appointment_code} status is now '{appt.status}'.",
            category="appointment",
            related_resource_type="appointment",
            related_resource_id=appt.id,
        )

    record_audit_log(
        db,
        action="appointment_updated",
        resource_type="appointment",
        resource_id=appt.appointment_code,
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=appt.patient_id,
        details={"status": appt.status},
        ip_address=get_client_ip(request),
    )
    return _serialize_appointment(appt)
