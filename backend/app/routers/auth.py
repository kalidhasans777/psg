from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient, PatientConsent
from app.models.user import User
from app.schemas.common import (
    ForgotPasswordRequest,
    PatientRegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserOut,
)
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_client_ip,
    get_current_user,
    hash_password,
    verify_password,
)
from app.services.audit import create_notification, record_audit_log
from app.services.patient_id import calculate_age, generate_permanent_patient_id

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _build_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        permanent_patient_id=user.patient_profile.permanent_patient_id if user.patient_profile else None,
        patient_id=user.patient_profile.id if user.patient_profile else None,
        doctor_id=user.doctor_profile.id if user.doctor_profile else None,
    )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Public patient registration workflow.
    Generates ONE permanent, unique Patient ID (MED-YYYY-XXXXX) in PostgreSQL/DB.
    Doctor and Administrator accounts cannot be created via public registration.
    """
    ip = get_client_ip(request)
    # Check duplicate phone or email
    filters = [User.phone == payload.phone.strip()]
    if payload.email:
        filters.append(User.email == payload.email.lower().strip())
    existing_user = db.query(User).filter(or_(*filters)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number or email already exists. Returning patients should log in or verify with hospital staff using their Permanent Patient ID.",
        )

    # Also detect potential returning patient profile by phone + DOB
    existing_patient = (
        db.query(Patient)
        .filter(Patient.phone == payload.phone.strip(), Patient.date_of_birth == payload.date_of_birth)
        .first()
    )
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A patient profile matching this phone and date of birth already exists ({existing_patient.permanent_patient_id}). Please log in instead of creating a duplicate profile.",
        )

    try:
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

        permanent_id = generate_permanent_patient_id(db)

        patient = Patient(
            user_id=user.id,
            permanent_patient_id=permanent_id,
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
            is_synthetic_demo=False,
        )
        db.add(patient)
        db.flush()

        for ctype in ("privacy_policy", "data_storage", "ai_summarization"):
            db.add(
                PatientConsent(
                    patient_id=patient.id,
                    consent_type=ctype,
                    consented=True,
                    consent_version="1.0",
                    ip_address=ip,
                )
            )

        db.commit()
        db.refresh(user)
        db.refresh(patient)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}")

    record_audit_log(
        db,
        action="patient_registered",
        resource_type="patient",
        resource_id=patient.permanent_patient_id,
        user_id=user.id,
        user_role="patient",
        patient_id=patient.id,
        details={"permanent_patient_id": patient.permanent_patient_id},
        ip_address=ip,
    )
    create_notification(
        db,
        user_id=user.id,
        title="Welcome to MEDORA",
        message=f"Your Permanent Patient ID {patient.permanent_patient_id} is active. Use this ID for all future hospital visits.",
        category="system",
        related_resource_type="patient",
        related_resource_id=patient.id,
    )

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return {
        "message": "PATIENT REGISTRATION SUCCESSFUL",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _build_user_out(user).model_dump(),
        "patient_card": {
            "patient_name": patient.full_name,
            "permanent_patient_id": patient.permanent_patient_id,
            "registration_date": str(patient.registration_date),
            "age": calculate_age(patient.date_of_birth),
            "phone": patient.phone,
        },
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    ident = payload.identifier.strip()
    user = (
        db.query(User)
        .filter(or_(User.email == ident.lower(), User.phone == ident))
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        record_audit_log(
            db,
            action="login_failed",
            resource_type="auth",
            resource_id=ident,
            user_id=user.id if user else None,
            user_role=user.role if user else None,
            ip_address=ip,
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    record_audit_log(
        db,
        action="login_success",
        resource_type="auth",
        resource_id=str(user.id),
        user_id=user.id,
        user_role=user.role,
        patient_id=user.patient_profile.id if user.patient_profile else None,
        ip_address=ip,
    )

    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        user=_build_user_out(user),
    )


@router.post("/refresh", response_model=dict)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token, expected_type="refresh")
    user = db.query(User).filter(User.id == int(payload["sub"]), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record_audit_log(
        db,
        action="logout",
        resource_type="auth",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        user_role=current_user.role,
        ip_address=get_client_ip(request),
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _build_user_out(current_user)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ident = payload.identifier.strip()
    user = db.query(User).filter(or_(User.email == ident.lower(), User.phone == ident)).first()
    if not user:
        # Generic response to prevent user enumeration
        return {"message": "If an account exists for that identifier, a password reset token has been generated."}

    token = secrets.token_urlsafe(24)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    record_audit_log(
        db,
        action="password_reset_requested",
        resource_type="auth",
        resource_id=str(user.id),
        user_id=user.id,
        user_role=user.role,
        ip_address=get_client_ip(request),
    )
    return {
        "message": "Password reset token generated (for local/hackathon verification without external SMTP).",
        "demo_reset_token": token,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    exp = user.reset_token_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    record_audit_log(
        db,
        action="password_reset_completed",
        resource_type="auth",
        resource_id=str(user.id),
        user_id=user.id,
        user_role=user.role,
        ip_address=get_client_ip(request),
    )
    return {"message": "Password has been reset successfully. You can now log in."}
