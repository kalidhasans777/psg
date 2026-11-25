from datetime import date, datetime, timezone
from pathlib import Path
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models.clinical import MedicalReport, ReportFinding, Visit
from app.models.user import User
from app.reports.processor import process_report_file
from app.schemas.common import ReportVerifyRequest
from app.security.auth import (
    authorize_patient_clinical_access,
    get_client_ip,
    get_current_user,
    require_roles,
)
from app.services.audit import create_notification, record_audit_log
from app.summarization.engine import generate_report_summary

settings = get_settings()
router = APIRouter(prefix="/api", tags=["Medical Reports & Extraction"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}


def _process_report_background(report_id: int) -> None:
    db = SessionLocal()
    try:
        report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
        if not report:
            return
        report.processing_status = "processing"
        db.commit()

        result = process_report_file(Path(report.stored_path), report.mime_type)
        report.extracted_text = result["extracted_text"]
        report.ocr_confidence_note = result["ocr_confidence_note"]
        report.processing_status = result["processing_status"]

        for f in result["findings"]:
            db.add(
                ReportFinding(
                    report_id=report.id,
                    test_name=f["test_name"],
                    observed_value=f["observed_value"],
                    numeric_value=f["numeric_value"],
                    unit=f["unit"],
                    reference_range=f["reference_range"],
                    status_relative_to_range=f["status_relative_to_range"],
                    is_uncertain=f["is_uncertain"],
                    original_extracted_value=f["original_extracted_value"],
                )
            )
        db.commit()
        db.refresh(report)

        generate_report_summary(db, patient=report.patient, report=report)
        if report.patient and report.patient.user_id:
            create_notification(
                db,
                user_id=report.patient.user_id,
                title="Medical Report Processed",
                message=f"Report '{report.file_name}' ({report.category}) has been extracted and an AI summary is ready for doctor verification.",
                category="report",
                related_resource_type="medical_report",
                related_resource_id=report.id,
            )
    except Exception as exc:
        report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
        if report:
            report.processing_status = "failed"
            report.ocr_confidence_note = f"Processing error: {exc}"
            db.commit()
    finally:
        db.close()


@router.post("/visits/{visit_id}/reports", status_code=status.HTTP_201_CREATED)
async def upload_medical_report(
    visit_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form("CBC"),
    report_date: str = Form(None),
    process_sync: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patient = authorize_patient_clinical_access(db, current_user, visit.patient)

    content_type = (file.content_type or "").lower()
    ext = Path(file.filename or "").suffix.lower()
    if content_type not in ALLOWED_MIME_TYPES and ext not in (".pdf", ".jpg", ".jpeg", ".png"):
        raise HTTPException(status_code=400, detail="Unsupported file format. Allowed: PDF, JPG, PNG.")

    raw_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    # Basic magic-byte check
    if ext == ".pdf" or content_type == "application/pdf":
        if not raw_bytes.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Invalid PDF file header")
        mime_type = "application/pdf"
        safe_ext = ".pdf"
    elif ext in (".jpg", ".jpeg") or content_type in ("image/jpeg", "image/jpg"):
        mime_type = "image/jpeg"
        safe_ext = ".jpg"
    else:
        mime_type = "image/png"
        safe_ext = ".png"

    patient_dir = Path(settings.UPLOAD_DIR) / patient.permanent_patient_id
    patient_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{secrets.token_hex(8)}_{Path(file.filename or 'report').stem[:40]}{safe_ext}"
    stored_path = patient_dir / safe_name
    stored_path.write_bytes(raw_bytes)

    parsed_date = date.today()
    if report_date:
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError:
            pass

    report = MedicalReport(
        visit_id=visit.id,
        patient_id=patient.id,
        category=category,
        file_name=file.filename or safe_name,
        stored_path=str(stored_path),
        mime_type=mime_type,
        file_size_bytes=len(raw_bytes),
        report_date=parsed_date,
        processing_status="pending",
        verification_status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    record_audit_log(
        db,
        action="medical_report_uploaded",
        resource_type="medical_report",
        resource_id=str(report.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=patient.id,
        details={"file_name": report.file_name, "category": category, "visit_id": visit.id},
        ip_address=get_client_ip(request),
    )

    if process_sync:
        _process_report_background(report.id)
        db.refresh(report)
    else:
        background_tasks.add_task(_process_report_background, report.id)

    return _serialize_report(report)


def _serialize_report(r: MedicalReport) -> dict:
    return {
        "id": r.id,
        "visit_id": r.visit_id,
        "patient_id": r.patient_id,
        "category": r.category,
        "file_name": r.file_name,
        "mime_type": r.mime_type,
        "file_size_bytes": r.file_size_bytes,
        "report_date": str(r.report_date),
        "upload_date": r.upload_date.isoformat(),
        "processing_status": r.processing_status,
        "extracted_text": r.extracted_text,
        "ocr_confidence_note": r.ocr_confidence_note,
        "verification_status": r.verification_status,
        "findings": [
            {
                "id": f.id,
                "test_name": f.test_name,
                "observed_value": f.observed_value,
                "numeric_value": f.numeric_value,
                "unit": f.unit,
                "reference_range": f.reference_range,
                "status_relative_to_range": f.status_relative_to_range,
                "is_uncertain": f.is_uncertain,
                "doctor_corrected": f.doctor_corrected,
                "original_extracted_value": f.original_extracted_value,
            }
            for f in r.findings
        ],
    }


@router.get("/reports/{report_id}")
def get_report(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")
    try:
        authorize_patient_clinical_access(db, current_user, report.patient)
    except HTTPException as exc:
        record_audit_log(
            db,
            action="report_access_denied",
            resource_type="medical_report",
            resource_id=str(report_id),
            user_id=current_user.id,
            user_role=current_user.role,
            patient_id=report.patient_id,
            details={"reason": exc.detail},
            ip_address=get_client_ip(request),
            status="denied",
        )
        raise
    return _serialize_report(report)


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Medical report not found")
    authorize_patient_clinical_access(db, current_user, report.patient)

    path = Path(report.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored report file missing on server")

    record_audit_log(
        db,
        action="medical_report_downloaded",
        resource_type="medical_report",
        resource_id=str(report.id),
        user_id=current_user.id,
        user_role=current_user.role,
        patient_id=report.patient_id,
        ip_address=get_client_ip(request),
    )
    return FileResponse(path=str(path), media_type=report.mime_type, filename=report.file_name)


@router.put("/reports/{report_id}/verify")
def verify_or_correct_report(
    report_id: int,
    payload: ReportVerifyRequest,
    request: Request,
    current_user: User = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.findings:
        # Update existing findings or add missing ones while preserving original_extracted_value
        existing_map = {f.id: f for f in report.findings}
        for item in payload.findings:
            if item.finding_id and item.finding_id in existing_map:
                f = existing_map[item.finding_id]
                f.test_name = item.test_name
                f.observed_value = item.observed_value
                f.unit = item.unit
                f.reference_range = item.reference_range
                f.status_relative_to_range = item.status_relative_to_range
                f.is_uncertain = item.status_relative_to_range == "uncertain"
                f.doctor_corrected = True
            else:
                db.add(
                    ReportFinding(
                        report_id=report.id,
                        test_name=item.test_name,
                        observed_value=item.observed_value,
                        unit=item.unit,
                        reference_range=item.reference_range,
                        status_relative_to_range=item.status_relative_to_range,
                        is_uncertain=item.status_relative_to_range == "uncertain",
                        doctor_corrected=True,
                        original_extracted_value="Manual doctor entry",
                    )
                )

    report.verification_status = payload.verification_status
    report.verified_by_doctor_id = current_user.doctor_profile.id if current_user.doctor_profile else None
    report.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)

    record_audit_log(
        db,
        action="medical_report_verified",
        resource_type="medical_report",
        resource_id=str(report.id),
        user_id=current_user.id,
        user_role="doctor",
        patient_id=report.patient_id,
        details={"verification_status": payload.verification_status},
        ip_address=get_client_ip(request),
    )
    return _serialize_report(report)


@router.get("/reports/sample/cbc-demo")
def download_sample_cbc_pdf():
    """Provides a synthetic CBC PDF report for hackathon live upload testing."""
    sample_path = Path(__file__).resolve().parent.parent.parent / "sample_reports" / "sample_cbc_demo_patient.pdf"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample CBC PDF not generated yet")
    return FileResponse(path=str(sample_path), media_type="application/pdf", filename="sample_cbc_demo_patient.pdf")
