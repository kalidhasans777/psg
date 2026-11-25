from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class PatientIdSequence(Base):
    """Concurrency-safe sequence table for generating MED-YYYY-XXXXX permanent IDs."""
    __tablename__ = "patient_id_sequences"

    year = Column(Integer, primary_key=True)
    last_value = Column(Integer, nullable=False, default=0)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False)
    permanent_patient_id = Column(String(32), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(32), nullable=True)
    phone = Column(String(32), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    address = Column(Text, nullable=False)
    emergency_contact = Column(String(200), nullable=True)
    known_allergies = Column(Text, nullable=True)
    existing_conditions = Column(Text, nullable=True)
    relevant_medical_history = Column(Text, nullable=True)
    blood_group = Column(String(16), nullable=True)
    registration_date = Column(Date, default=date.today, nullable=False)
    account_status = Column(String(32), default="active", nullable=False)  # active | inactive | archived
    consent_status = Column(Boolean, default=True, nullable=False)
    is_synthetic_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="patient_profile")
    visits = relationship("Visit", back_populates="patient", order_by="Visit.visit_date.desc()")
    symptoms = relationship("Symptom", back_populates="patient")
    reports = relationship("MedicalReport", back_populates="patient")
    ai_summaries = relationship("AISummary", back_populates="patient")
    consultations = relationship("DoctorConsultation", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    consents = relationship("PatientConsent", back_populates="patient", cascade="all, delete-orphan")


class PatientConsent(Base):
    __tablename__ = "patient_consents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(64), nullable=False)  # privacy_policy | data_storage | voice_processing | ai_summarization
    consented = Column(Boolean, nullable=False, default=True)
    consent_version = Column(String(32), nullable=False, default="1.0")
    ip_address = Column(String(64), nullable=True)
    consented_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    patient = relationship("Patient", back_populates="consents")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(48), nullable=False, default="system")  # appointment | report | ai_summary | follow_up | system
    is_read = Column(Boolean, default=False, nullable=False)
    related_resource_type = Column(String(64), nullable=True)
    related_resource_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")
