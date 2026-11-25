from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class MedicalKnowledgeDocument(Base):
    __tablename__ = "medical_knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(120), nullable=False)  # WHO | ICMR | NHM | MoHFW | MedlinePlus | LabRef
    document_title = Column(String(300), nullable=False)
    publication_date = Column(String(32), nullable=True)
    last_updated_date = Column(String(32), nullable=True)
    category = Column(String(80), nullable=False, index=True)
    source_url = Column(String(500), nullable=True)
    version = Column(String(40), nullable=True)
    retrieval_date = Column(String(32), nullable=False)
    content_snippet = Column(Text, nullable=False)
    keywords_json = Column(JSON, nullable=False, default=list)


class AISummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="SET NULL"), nullable=True, index=True)
    summary_type = Column(String(48), nullable=False, index=True)
    # symptom | report | history | consultation | patient_overview | report_comparison
    source_reference = Column(String(255), nullable=True)
    ai_generated_json = Column(JSON, nullable=False)
    ai_generated_text = Column(Text, nullable=False)
    ai_provider = Column(String(64), nullable=False)
    model_identifier = Column(String(100), nullable=False)
    disclaimer = Column(
        String(255),
        nullable=False,
        default="AI-Generated Summary – Pending Doctor Verification",
    )
    generation_status = Column(String(32), default="completed", nullable=False)  # pending | completed | failed
    verification_status = Column(String(32), default="pending_verification", nullable=False)
    # pending_verification | approved | edited | rejected
    doctor_edited_text = Column(Text, nullable=True)
    doctor_edited_json = Column(JSON, nullable=True)
    reviewing_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    review_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    patient = relationship("Patient", back_populates="ai_summaries")
    visit = relationship("Visit", back_populates="ai_summaries")
    sources = relationship("AISummarySource", back_populates="summary", cascade="all, delete-orphan")


class AISummarySource(Base):
    __tablename__ = "ai_summary_sources"

    id = Column(Integer, primary_key=True, index=True)
    summary_id = Column(Integer, ForeignKey("ai_summaries.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_doc_id = Column(Integer, ForeignKey("medical_knowledge_documents.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(String(48), nullable=False)  # visit | report | symptom | consultation | knowledge
    source_record_id = Column(Integer, nullable=True)
    citation_note = Column(String(300), nullable=True)

    summary = relationship("AISummary", back_populates="sources")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_role = Column(String(32), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    details_json = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    status = Column(String(32), default="success", nullable=False)  # success | failure | denied
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
