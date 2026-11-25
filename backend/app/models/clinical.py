from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    visit_code = Column(String(40), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True)
    visit_date = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    visit_type = Column(String(48), default="outpatient", nullable=False)  # outpatient | follow_up | emergency | initial
    chief_complaint = Column(Text, nullable=True)
    status = Column(String(32), default="registered", nullable=False)  # registered | in_progress | completed | cancelled
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("Doctor", back_populates="visits")
    department = relationship("Department", back_populates="visits")
    symptoms = relationship("Symptom", back_populates="visit", cascade="all, delete-orphan")
    reports = relationship("MedicalReport", back_populates="visit")
    ai_summaries = relationship("AISummary", back_populates="visit")
    consultations = relationship("DoctorConsultation", back_populates="visit")
    prescriptions = relationship("Prescription", back_populates="visit")


class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_channel = Column(String(32), default="text", nullable=False)  # text | voice_ta | voice_en | voice_mixed
    language = Column(String(16), default="en-IN", nullable=False)  # ta-IN | en-IN | mixed
    raw_transcript = Column(Text, nullable=True)
    edited_transcript = Column(Text, nullable=True)
    symptom_list_json = Column(JSON, nullable=True)
    description = Column(Text, nullable=False)
    duration = Column(String(120), nullable=True)
    severity = Column(String(48), nullable=True)  # mild | moderate | severe
    onset_date = Column(String(64), nullable=True)
    additional_details = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    patient_confirmed = Column(Boolean, default=True, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    visit = relationship("Visit", back_populates="symptoms")
    patient = relationship("Patient", back_populates="symptoms")


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    category = Column(String(64), nullable=False, default="CBC")
    file_name = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    report_date = Column(Date, default=date.today, nullable=False)
    processing_status = Column(String(32), default="pending", nullable=False)  # pending | processing | completed | failed
    extracted_text = Column(Text, nullable=True)
    ocr_confidence_note = Column(Text, nullable=True)
    verification_status = Column(String(32), default="pending", nullable=False)  # pending | verified | corrected
    verified_by_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    upload_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    visit = relationship("Visit", back_populates="reports")
    patient = relationship("Patient", back_populates="reports")
    findings = relationship("ReportFinding", back_populates="report", cascade="all, delete-orphan")


class ReportFinding(Base):
    __tablename__ = "report_findings"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("medical_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    test_name = Column(String(150), nullable=False)
    observed_value = Column(String(80), nullable=False)
    numeric_value = Column(String(40), nullable=True)
    unit = Column(String(48), nullable=True)
    reference_range = Column(String(120), nullable=True)
    status_relative_to_range = Column(String(32), default="uncertain", nullable=False)  # below | within | above | uncertain
    is_uncertain = Column(Boolean, default=False, nullable=False)
    doctor_corrected = Column(Boolean, default=False, nullable=False)
    original_extracted_value = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    report = relationship("MedicalReport", back_populates="findings")


class DoctorConsultation(Base):
    __tablename__ = "doctor_consultations"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    chief_complaints = Column(Text, nullable=False)
    observations = Column(Text, nullable=True)
    clinical_assessment = Column(Text, nullable=False)
    diagnosis = Column(String(300), nullable=True)
    treatment_plan = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    consultation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    visit = relationship("Visit", back_populates="consultations")
    patient = relationship("Patient", back_populates="consultations")
    doctor = relationship("Doctor", back_populates="consultations")
    prescriptions = relationship("Prescription", back_populates="consultation")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("doctor_consultations.id", ondelete="SET NULL"), nullable=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    medications_json = Column(JSON, nullable=False)
    instructions = Column(Text, nullable=True)
    issued_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    consultation = relationship("DoctorConsultation", back_populates="prescriptions")
    visit = relationship("Visit", back_populates="prescriptions")
    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("Doctor", back_populates="prescriptions")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_code = Column(String(40), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="SET NULL"), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    status = Column(String(32), default="scheduled", nullable=False)  # scheduled | confirmed | checked_in | completed | cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    department = relationship("Department", back_populates="appointments")
