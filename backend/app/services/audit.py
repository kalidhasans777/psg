from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.ai_knowledge import AuditLog
from app.models.patient import Notification


def record_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
    patient_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        patient_id=patient_id,
        details_json=details or {},
        ip_address=ip_address,
        status=status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    category: str = "system",
    related_resource_type: Optional[str] = None,
    related_resource_id: Optional[int] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        related_resource_type=related_resource_type,
        related_resource_id=related_resource_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
