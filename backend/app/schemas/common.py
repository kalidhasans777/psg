from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Auth & Users ---
class UserLoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, description="Email or registered phone number")
    password: str = Field(..., min_length=6)


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=3)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class PatientRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    date_of_birth: date
    gender: Optional[str] = Field(default="Prefer not to say", max_length=32)
    phone: str = Field(..., min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    address: str = Field(..., min_length=4, max_length=500)
    emergency_contact: Optional[str] = Field(default=None, max_length=200)
    known_allergies: Optional[str] = None
    existing_conditions: Optional[str] = None
    relevant_medical_history: Optional[str] = None
    blood_group: Optional[str] = Field(default=None, max_length=16)
    password: str = Field(..., min_length=6, max_length=128)
    consent_accepted: bool = Field(..., description="Privacy and consent acknowledgement")

    @field_validator("date_of_birth")
    @classmethod
    def dob_must_be_past(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @field_validator("consent_accepted")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Privacy and consent acknowledgement is required to register")
        return v


class UserOut(BaseModel):
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    full_name: str
    is_active: bool
    permanent_patient_id: Optional[str] = None
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Patient ---
class PatientUpdateRequest(BaseModel):
    phone: Optional[str] = Field(default=None, min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, min_length=4, max_length=500)
    emergency_contact: Optional[str] = None
    known_allergies: Optional[str] = None
    existing_conditions: Optional[str] = None
    blood_group: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    user_id: int
    permanent_patient_id: str
    full_name: str
    date_of_birth: date
    age: int
    gender: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: str
    emergency_contact: Optional[str] = None
    known_allergies: Optional[str] = None
    existing_conditions: Optional[str] = None
    relevant_medical_history: Optional[str] = None
    blood_group: Optional[str] = None
    registration_date: date
    account_status: str
    consent_status: bool
    is_synthetic_demo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Visits & Symptoms ---
class VisitCreateRequest(BaseModel):
    patient_identifier: Optional[str] = None  # MED-YYYY-XXXXX or numeric id (optional for patient self-visit)
    doctor_id: Optional[int] = None
    department_id: Optional[int] = None
    visit_type: str = "outpatient"
    chief_complaint: Optional[str] = None
    visit_date: Optional[datetime] = None


class SymptomCreateRequest(BaseModel):
    source_channel: str = "text"  # text | voice_ta | voice_en | voice_mixed
    language: str = "en-IN"
    raw_transcript: Optional[str] = None
    edited_transcript: Optional[str] = None
    description: str = Field(..., min_length=2)
    duration: Optional[str] = None
    severity: Optional[str] = "moderate"
    onset_date: Optional[str] = None
    additional_details: Optional[str] = None
    current_medications: Optional[str] = None
    patient_confirmed: bool = True


# --- Voice ---
class VoiceAssistantTurnRequest(BaseModel):
    language: str = "ta-IN"  # ta-IN | en-IN | mixed
    step: int = 0
    patient_utterance: str = ""
    collected_data: Dict[str, Any] = Field(default_factory=dict)


class VoiceConfirmTranscriptRequest(BaseModel):
    visit_id: Optional[int] = None
    language: str = "ta-IN"
    raw_transcript: str
    confirmed_transcript: str
    duration: Optional[str] = None
    severity: Optional[str] = "moderate"
    additional_details: Optional[str] = None
    current_medications: Optional[str] = None
    audio_consent: bool = True
    generate_ai_summary: bool = True


# --- AI Summarization ---
class SummarizeSymptomsRequest(BaseModel):
    patient_identifier: Optional[str] = None
    visit_id: Optional[int] = None
    symptom_id: Optional[int] = None
    text: Optional[str] = None
    language: str = "en-IN"
    duration: Optional[str] = None
    severity: Optional[str] = None
    current_medications: Optional[str] = None


class SummarizeReportRequest(BaseModel):
    report_id: int


class SummarizeHistoryRequest(BaseModel):
    patient_identifier: str


class SummarizeConsultationRequest(BaseModel):
    consultation_id: int


class PatientOverviewRequest(BaseModel):
    patient_identifier: str
    current_visit_id: Optional[int] = None


class CompareReportsRequest(BaseModel):
    patient_identifier: str
    report_ids: Optional[List[int]] = None


class AISummaryReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|edited|rejected)$")
    edited_text: Optional[str] = None
    edited_json: Optional[Dict[str, Any]] = None
    review_notes: Optional[str] = None


# --- Report Findings Verification ---
class FindingCorrectionItem(BaseModel):
    finding_id: Optional[int] = None
    test_name: str
    observed_value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status_relative_to_range: str = "uncertain"


class ReportVerifyRequest(BaseModel):
    verification_status: str = Field(..., pattern="^(verified|corrected)$")
    findings: Optional[List[FindingCorrectionItem]] = None


# --- Doctor Consultation & Prescription ---
class MedicationItem(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None


class ConsultationCreateRequest(BaseModel):
    visit_id: int
    chief_complaints: str = Field(..., min_length=2)
    observations: Optional[str] = None
    clinical_assessment: str = Field(..., min_length=2)
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None
    consultation_notes: Optional[str] = None
    medications: Optional[List[MedicationItem]] = None
    prescription_instructions: Optional[str] = None


class PrescriptionCreateRequest(BaseModel):
    visit_id: int
    consultation_id: Optional[int] = None
    medications: List[MedicationItem]
    instructions: Optional[str] = None


# --- Appointments ---
class AppointmentCreateRequest(BaseModel):
    patient_identifier: Optional[str] = None
    doctor_id: int
    department_id: int
    scheduled_at: datetime
    reason: Optional[str] = None


class AppointmentUpdateRequest(BaseModel):
    status: Optional[str] = None
    doctor_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None


# --- Admin ---
class DoctorCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=32)
    password: str = Field(..., min_length=6)
    department_id: int
    license_number: str = Field(..., min_length=3, max_length=64)
    specialization: str = Field(..., min_length=2, max_length=150)
    qualification: Optional[str] = None


class DoctorUpdateRequest(BaseModel):
    department_id: Optional[int] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=24)
    description: Optional[str] = None
    head_doctor_name: Optional[str] = None


class PatientStatusUpdateRequest(BaseModel):
    account_status: str = Field(..., pattern="^(active|inactive|archived)$")
