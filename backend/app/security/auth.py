from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.patient import Patient
from app.models.user import Doctor, User

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
        )
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return dependency


def get_client_ip(request: Optional[Request]) -> str:
    if not request:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def resolve_patient_by_identifier(db: Session, identifier: str) -> Optional[Patient]:
    """Resolve patient by either Permanent Patient ID (MED-YYYY-XXXXX) or numeric ID."""
    clean = identifier.strip()
    if clean.upper().startswith("MED-"):
        return db.query(Patient).filter(Patient.permanent_patient_id == clean.upper()).first()
    if clean.isdigit():
        return db.query(Patient).filter(Patient.id == int(clean)).first()
    return db.query(Patient).filter(Patient.permanent_patient_id == clean).first()


def authorize_patient_clinical_access(
    db: Session,
    current_user: User,
    patient: Optional[Patient],
    allow_admin_clinical: bool = False,
) -> Patient:
    """
    Enforces strict backend patient ownership & RBAC:
    - Patients can ONLY access their own Patient record.
    - Doctors (active) can access authorized patient clinical records.
    - Admins do NOT get unrestricted clinical record access unless explicitly flagged for administrative endpoints.
    """
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient record not found")

    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to access another patient's medical records.",
            )
        return patient

    if current_user.role == "doctor":
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id, Doctor.is_active.is_(True)).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active doctor profile required to access patient records.",
            )
        return patient

    if current_user.role == "admin":
        if allow_admin_clinical:
            return patient
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Hospital administrators cannot access confidential clinical histories directly.",
        )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
