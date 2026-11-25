"""
MEDORA Advanced AI Medical Summarization Engine
Implements 6 specialized, context-aware clinical summary types with:
- Structured JSON schema validation
- Medical terminology normalization (Tamil <-> English)
- Trusted knowledge retrieval (WHO, ICMR, NHM, MoHFW, MedlinePlus)
- Strict separation of patient-reported vs doctor-confirmed vs historical vs current data
- Gemini API integration with transparent Deterministic Clinical NLP Fallback when GEMINI_API_KEY is unset
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.knowledge_base import retrieve_relevant_knowledge
from app.ai.terminology import extract_medical_terms
from app.config import get_settings
from app.models.ai_knowledge import AISummary, AISummarySource, MedicalKnowledgeDocument
from app.models.clinical import (
    DoctorConsultation,
    MedicalReport,
    Prescription,
    Symptom,
    Visit,
)
from app.models.patient import Patient

settings = get_settings()

DISCLAIMER_TEXT = "AI-Generated Summary – Pending Doctor Verification"


# --- Structured Output Validation Schemas ---
class SymptomSummarySchema(BaseModel):
    chief_complaints: List[str]
    tamil_original_statement: Optional[str] = None
    duration: str
    symptom_frequency: str
    patient_reported_severity: str
    additional_symptoms: List[str]
    medication_information: str
    information_to_verify: List[str]
    uncertainty_flags: List[str] = Field(default_factory=list)


class ReportParameterSummary(BaseModel):
    test_name: str
    observed_value: str
    unit: Optional[str] = None
    supplied_reference_range: Optional[str] = None
    status_relative_to_supplied_range: str
    is_uncertain: bool = False


class ReportSummarySchema(BaseModel):
    report_category: str
    report_date: str
    parameters: List[ReportParameterSummary]
    unreadable_or_uncertain_values: List[str]
    clinical_note: str


class HistorySummarySchema(BaseModel):
    permanent_patient_id: str
    total_visits: int
    recorded_allergies: str
    existing_conditions: str
    chronological_visits: List[Dict[str, Any]]
    historical_reports_overview: List[Dict[str, Any]]
    previous_prescriptions: List[Dict[str, Any]]
    follow_up_history: List[str]
    missing_or_uncertain_information: List[str]


class ConsultationSummarySchema(BaseModel):
    visit_date: str
    visit_code: str
    doctor_name: str
    chief_complaints: str
    doctor_assessment: str
    doctor_entered_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    prescriptions: List[Dict[str, Any]]
    follow_up_recommendations: Optional[str] = None


class PatientOverviewSchema(BaseModel):
    permanent_patient_id: str
    patient_name: str
    patient_reported_current_complaints: List[str]
    current_visit_details: Dict[str, Any]
    relevant_previous_medical_history: Dict[str, Any]
    current_report_findings: List[Dict[str, Any]]
    relevant_previous_report_comparisons: List[Dict[str, Any]]
    recorded_medications: List[str]
    doctor_confirmed_vs_patient_reported_distinction: Dict[str, Any]
    missing_or_uncertain_information: List[str]


class ReportComparisonSchema(BaseModel):
    permanent_patient_id: str
    compared_report_dates: List[str]
    parameter_trends: List[Dict[str, Any]]
    uncertainty_and_context_note: str


def _call_gemini_structured(prompt: str, fallback_data: Dict[str, Any]) -> tuple[Dict[str, Any], str, str, str]:
    """
    Calls Google Gemini API if GEMINI_API_KEY is configured.
    Returns (structured_dict, provider, model_id, mode_note).
    Never claims live Gemini output when falling back.
    """
    if not settings.GEMINI_API_KEY:
        return (
            fallback_data,
            "medora-deterministic-fallback",
            "clinical-nlp-extractor-v1",
            "Demonstration / Fallback Mode: Deterministic clinical extraction used because GEMINI_API_KEY is not configured.",
        )

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        full_prompt = (
            "You are MEDORA, a clinical information organizer (NOT a doctor). "
            "Rules: Never diagnose independently, never prescribe medicines, never invent values, units, or reference ranges, "
            "preserve exact dates/numbers/units, distinguish patient-reported vs doctor-confirmed vs historical vs current, "
            "and explicitly list missing or uncertain details.\n"
            "Return ONLY valid JSON matching the exact keys of the provided draft structure.\n\n"
            f"DRAFT STRUCTURE AND SOURCE DATA:\n{json.dumps({'prompt': prompt, 'source_draft': fallback_data}, ensure_ascii=False)}"
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=full_prompt,
        )
        raw_text = (response.text or "").strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()
        parsed = json.loads(raw_text)
        return (
            parsed,
            "google-gemini",
            settings.GEMINI_MODEL,
            f"Generated by Google Gemini ({settings.GEMINI_MODEL}) with MEDORA clinical safety guardrails.",
        )
    except Exception as exc:
        return (
            fallback_data,
            "medora-deterministic-fallback",
            "clinical-nlp-extractor-v1",
            f"Fallback Mode used after Gemini request issue ({exc}). Original data preserved.",
        )


def _format_summary_text(title: str, structured: Dict[str, Any], mode_note: str) -> str:
    lines = [f"[{DISCLAIMER_TEXT}]", f"=== {title} ==="]
    for key, val in structured.items():
        label = key.replace("_", " ").upper()
        if isinstance(val, list):
            lines.append(f"\n{label}:")
            if not val:
                lines.append("- None recorded")
            for item in val:
                if isinstance(item, dict):
                    summary_parts = ", ".join(f"{k}: {v}" for k, v in item.items() if v not in (None, "", []))
                    lines.append(f"- {summary_parts}")
                else:
                    lines.append(f"- {item}")
        elif isinstance(val, dict):
            lines.append(f"\n{label}:")
            for k, v in val.items():
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")
        elif val not in (None, ""):
            lines.append(f"\n{label}:\n- {val}")
    lines.append(f"\nSYSTEM NOTE:\n- {mode_note}")
    return "\n".join(lines).strip()


def _save_summary(
    db: Session,
    *,
    patient: Patient,
    visit_id: Optional[int],
    summary_type: str,
    source_reference: str,
    structured_json: Dict[str, Any],
    summary_text: str,
    provider: str,
    model_id: str,
    knowledge_docs: List[MedicalKnowledgeDocument],
    source_records: List[tuple[str, Optional[int], str]],
) -> AISummary:
    summary = AISummary(
        patient_id=patient.id,
        visit_id=visit_id,
        summary_type=summary_type,
        source_reference=source_reference,
        ai_generated_json=structured_json,
        ai_generated_text=summary_text,
        ai_provider=provider,
        model_identifier=model_id,
        disclaimer=DISCLAIMER_TEXT,
        generation_status="completed",
        verification_status="pending_verification",
    )
    db.add(summary)
    db.flush()

    for doc in knowledge_docs:
        db.add(
            AISummarySource(
                summary_id=summary.id,
                knowledge_doc_id=doc.id,
                source_type="knowledge",
                source_record_id=doc.id,
                citation_note=f"{doc.source_name}: {doc.document_title} ({doc.version or 'current'})",
            )
        )
    for stype, sid, note in source_records:
        db.add(
            AISummarySource(
                summary_id=summary.id,
                source_type=stype,
                source_record_id=sid,
                citation_note=note,
            )
        )

    db.commit()
    db.refresh(summary)
    return summary


# --- Type 1: Symptom Summary ---
def generate_symptom_summary(
    db: Session,
    *,
    patient: Patient,
    visit_id: Optional[int],
    symptom: Optional[Symptom] = None,
    raw_text: Optional[str] = None,
    language: str = "en-IN",
    duration: Optional[str] = None,
    severity: Optional[str] = None,
    current_medications: Optional[str] = None,
) -> AISummary:
    text_source = raw_text or (symptom.edited_transcript or symptom.raw_transcript or symptom.description if symptom else "")
    terms = extract_medical_terms(text_source)

    complaints = terms["english_complaints"] or [text_source[:120] if text_source else "Not specified"]
    detected_duration = duration or (symptom.duration if symptom else None) or terms.get("detected_duration") or "Not specified by patient"
    meds = current_medications or (symptom.current_medications if symptom else None) or (
        "No medication reported" if terms.get("no_medication_cue") else "Not specified by patient"
    )
    sev = severity or (symptom.severity if symptom else None) or "Not specified by patient"

    verify_items = []
    if "Fever" in complaints:
        verify_items.extend(["Measured temperature (°F/°C)", "Fever pattern (continuous vs intermittent)"])
    if detected_duration == "Not specified by patient":
        verify_items.append("Exact symptom onset date and duration")
    if sev == "Not specified by patient":
        verify_items.append("Patient-perceived symptom severity")
    if meds == "Not specified by patient":
        verify_items.append("Prior medications or home remedies taken")
    verify_items.append("Associated warning signs (breathlessness, persistent vomiting, chest discomfort)")

    additional_symptoms = list(terms.get("additional_cues", []))
    if symptom and symptom.additional_details:
        additional_symptoms.append(symptom.additional_details)

    draft = SymptomSummarySchema(
        chief_complaints=complaints,
        tamil_original_statement=text_source if (language.startswith("ta") or any("\u0b80" <= c <= "\u0bff" for c in text_source)) else None,
        duration=detected_duration,
        symptom_frequency="Evening/night exacerbation reported" if any("evening" in c.lower() for c in additional_symptoms) else "Frequency not explicitly quantified",
        patient_reported_severity=sev,
        additional_symptoms=additional_symptoms or ["No additional symptoms explicitly reported"],
        medication_information=meds,
        information_to_verify=verify_items,
        uncertainty_flags=(["Duration not explicitly quantified"] if "Not specified" in detected_duration else []),
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(db, f"{text_source} {' '.join(complaints)}", categories=["symptom_assessment", "clinical_documentation"], limit=2)
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Summarize patient-reported symptoms accurately into structured English clinical sections while preserving Tamil statement if present.",
        draft,
    )
    validated = SymptomSummarySchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text("TYPE 1: PATIENT SYMPTOM SUMMARY", validated, mode_note)

    return _save_summary(
        db,
        patient=patient,
        visit_id=visit_id,
        summary_type="symptom",
        source_reference=f"Symptom #{symptom.id}" if symptom else "Direct Symptom Input",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=[("symptom", symptom.id if symptom else None, "Patient-reported symptom statement")],
    )


# --- Type 2: Medical Report Summary ---
def generate_report_summary(db: Session, *, patient: Patient, report: MedicalReport) -> AISummary:
    params = [
        ReportParameterSummary(
            test_name=f.test_name,
            observed_value=f.observed_value,
            unit=f.unit,
            supplied_reference_range=f.reference_range,
            status_relative_to_supplied_range=(
                "Below supplied reference range" if f.status_relative_to_range == "below"
                else "Above supplied reference range" if f.status_relative_to_range == "above"
                else "Within supplied reference range" if f.status_relative_to_range == "within"
                else "Uncertain / Missing reference range"
            ),
            is_uncertain=f.is_uncertain,
        )
        for f in report.findings
    ]
    uncertain = [
        f"{p.test_name}: {p.observed_value} (missing or uncertain reference interval)"
        for p in params
        if p.is_uncertain
    ]
    if not params:
        uncertain.append("No structured parameters could be auto-extracted; manual inspection of original report required.")

    draft = ReportSummarySchema(
        report_category=report.category,
        report_date=str(report.report_date),
        parameters=[p.model_dump() for p in params],
        unreadable_or_uncertain_values=uncertain,
        clinical_note="Values reflect exact extracted report figures compared strictly against supplied reference ranges. Clinical correlation by doctor required.",
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(
        db,
        f"{report.category} {' '.join(p.test_name for p in params)}",
        categories=["laboratory_cbc", "laboratory_metabolic", "laboratory_organ_panels"],
        limit=2,
    )
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Summarize laboratory report parameters verbatim with observed values, units, supplied reference ranges, and range status without inventing numbers.",
        draft,
    )
    validated = ReportSummarySchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text(f"TYPE 2: MEDICAL REPORT SUMMARY ({report.category})", validated, mode_note)

    return _save_summary(
        db,
        patient=patient,
        visit_id=report.visit_id,
        summary_type="report",
        source_reference=f"MedicalReport #{report.id} ({report.file_name})",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=[("report", report.id, f"Original report: {report.file_name} ({report.report_date})")],
    )


# --- Type 3: Previous Medical History Summary ---
def generate_history_summary(db: Session, *, patient: Patient) -> AISummary:
    visits = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.asc()).all()
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id).order_by(MedicalReport.report_date.asc()).all()
    prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient.id).order_by(Prescription.issued_date.asc()).all()
    consultations = db.query(DoctorConsultation).filter(DoctorConsultation.patient_id == patient.id).order_by(DoctorConsultation.created_at.asc()).all()

    visit_items = []
    for v in visits:
        v_symptoms = [s.description for s in v.symptoms]
        v_consults = [c.clinical_assessment for c in v.consultations]
        visit_items.append(
            {
                "visit_code": v.visit_code,
                "visit_date": v.visit_date.strftime("%Y-%m-%d"),
                "visit_type": v.visit_type,
                "chief_complaint": v.chief_complaint or "Not recorded",
                "patient_reported_symptoms": v_symptoms or ["None recorded"],
                "doctor_assessments": v_consults or ["Pending doctor consultation"],
            }
        )

    report_items = [
        {
            "report_id": r.id,
            "date": str(r.report_date),
            "category": r.category,
            "file_name": r.file_name,
            "findings_count": len(r.findings),
            "abnormal_flags": [
                f"{f.test_name}: {f.observed_value} ({f.status_relative_to_range})"
                for f in r.findings
                if f.status_relative_to_range in ("below", "above")
            ],
        }
        for r in reports
    ]

    rx_items = [
        {
            "issued_date": str(p.issued_date),
            "medications": p.medications_json,
            "instructions": p.instructions,
        }
        for p in prescriptions
    ]

    follow_ups = [
        f"Visit #{c.visit_id}: Follow-up recommended on {c.follow_up_date}"
        for c in consultations
        if c.follow_up_date
    ]

    missing = []
    if not patient.known_allergies:
        missing.append("Known drug/food allergies not explicitly recorded (verify with patient)")
    if not visits:
        missing.append("No prior hospital visits recorded yet")

    draft = HistorySummarySchema(
        permanent_patient_id=patient.permanent_patient_id,
        total_visits=len(visits),
        recorded_allergies=patient.known_allergies or "None recorded",
        existing_conditions=patient.existing_conditions or "None recorded",
        chronological_visits=visit_items,
        historical_reports_overview=report_items,
        previous_prescriptions=rx_items,
        follow_up_history=follow_ups or ["No scheduled follow-ups recorded"],
        missing_or_uncertain_information=missing or ["No major historical gaps detected"],
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(db, "longitudinal medical history follow-up", categories=["clinical_documentation"], limit=2)
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Summarize the patient's chronological medical history across visits while keeping each visit separate and distinguishing patient reports from doctor notes.",
        draft,
    )
    validated = HistorySummarySchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text(f"TYPE 3: LONGITUDINAL MEDICAL HISTORY ({patient.permanent_patient_id})", validated, mode_note)

    return _save_summary(
        db,
        patient=patient,
        visit_id=visits[-1].id if visits else None,
        summary_type="history",
        source_reference=f"Patient {patient.permanent_patient_id} ({len(visits)} visits)",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=[("visit", v.id, f"{v.visit_code} ({v.visit_date.strftime('%Y-%m-%d')})") for v in visits],
    )


# --- Type 4: Consultation Summary ---
def generate_consultation_summary(db: Session, *, patient: Patient, consultation: DoctorConsultation) -> AISummary:
    visit = consultation.visit
    doctor_name = consultation.doctor.user.full_name if consultation.doctor and consultation.doctor.user else f"Doctor #{consultation.doctor_id}"
    rx_list = [
        {"issued_date": str(p.issued_date), "medications": p.medications_json, "instructions": p.instructions}
        for p in consultation.prescriptions
    ]

    draft = ConsultationSummarySchema(
        visit_date=visit.visit_date.strftime("%Y-%m-%d") if visit else str(consultation.created_at.date()),
        visit_code=visit.visit_code if visit else f"VIS-{consultation.visit_id}",
        doctor_name=doctor_name,
        chief_complaints=consultation.chief_complaints,
        doctor_assessment=consultation.clinical_assessment,
        doctor_entered_diagnosis=consultation.diagnosis,
        treatment_plan=consultation.treatment_plan,
        prescriptions=rx_list,
        follow_up_recommendations=str(consultation.follow_up_date) if consultation.follow_up_date else "Not specified",
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(db, f"{consultation.chief_complaints} {consultation.clinical_assessment}", categories=["clinical_documentation"], limit=1)
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Organize this doctor-documented consultation faithfully without modifying the doctor's diagnosis or prescriptions.",
        draft,
    )
    validated = ConsultationSummarySchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text(f"TYPE 4: CONSULTATION SUMMARY ({draft['visit_code']})", validated, mode_note)

    return _save_summary(
        db,
        patient=patient,
        visit_id=consultation.visit_id,
        summary_type="consultation",
        source_reference=f"Consultation #{consultation.id}",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=[("consultation", consultation.id, f"Doctor consultation by {doctor_name}")],
    )


# --- Type 5: Complete Patient Overview ---
def generate_patient_overview(db: Session, *, patient: Patient, current_visit_id: Optional[int] = None) -> AISummary:
    visits = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.desc()).all()
    current_visit = (
        next((v for v in visits if v.id == current_visit_id), None)
        if current_visit_id
        else (visits[0] if visits else None)
    )
    previous_visits = [v for v in visits if not current_visit or v.id != current_visit.id]

    current_complaints = []
    if current_visit:
        for s in current_visit.symptoms:
            terms = extract_medical_terms(s.edited_transcript or s.raw_transcript or s.description)
            if terms["english_complaints"]:
                current_complaints.extend(terms["english_complaints"])
            else:
                current_complaints.append(s.description)
    current_complaints = list(dict.fromkeys(current_complaints)) or ["No active current visit symptoms logged"]

    current_report_findings = []
    if current_visit:
        for r in current_visit.reports:
            for f in r.findings:
                current_report_findings.append(
                    {
                        "report_date": str(r.report_date),
                        "category": r.category,
                        "test_name": f.test_name,
                        "observed_value": f.observed_value,
                        "reference_range": f.reference_range,
                        "status": f.status_relative_to_range,
                    }
                )

    prev_report_comparisons = []
    for v in previous_visits:
        for r in v.reports:
            for f in r.findings:
                prev_report_comparisons.append(
                    {
                        "visit_code": v.visit_code,
                        "report_date": str(r.report_date),
                        "test_name": f.test_name,
                        "observed_value": f.observed_value,
                        "reference_range": f.reference_range,
                        "status": f.status_relative_to_range,
                    }
                )

    recorded_meds = []
    for s in (current_visit.symptoms if current_visit else []):
        if s.current_medications:
            recorded_meds.append(f"Current visit patient report: {s.current_medications}")
    for rx in db.query(Prescription).filter(Prescription.patient_id == patient.id).order_by(Prescription.issued_date.desc()).limit(5).all():
        med_names = [m.get("medicine_name", "") for m in (rx.medications_json or [])]
        if med_names:
            recorded_meds.append(f"Prior Rx ({rx.issued_date}): {', '.join(med_names)}")

    missing_items = []
    if not patient.known_allergies:
        missing_items.append("Allergy status not recorded — confirm before prescribing")
    if current_visit and not current_visit.reports:
        missing_items.append("No laboratory report uploaded for the current visit yet")
    if not current_visit:
        missing_items.append("No current visit selected/created")

    draft = PatientOverviewSchema(
        permanent_patient_id=patient.permanent_patient_id,
        patient_name=patient.full_name,
        patient_reported_current_complaints=current_complaints,
        current_visit_details=(
            {
                "visit_code": current_visit.visit_code,
                "visit_date": current_visit.visit_date.strftime("%Y-%m-%d"),
                "visit_type": current_visit.visit_type,
                "status": current_visit.status,
                "chief_complaint": current_visit.chief_complaint,
            }
            if current_visit
            else {"note": "No active visit"}
        ),
        relevant_previous_medical_history={
            "known_allergies": patient.known_allergies or "Not recorded",
            "existing_conditions": patient.existing_conditions or "Not recorded",
            "prior_visits_count": len(previous_visits),
            "prior_visit_summaries": [
                {
                    "visit_code": pv.visit_code,
                    "date": pv.visit_date.strftime("%Y-%m-%d"),
                    "chief_complaint": pv.chief_complaint,
                    "doctor_diagnosis": pv.consultations[0].diagnosis if pv.consultations else None,
                }
                for pv in previous_visits[:5]
            ],
        },
        current_report_findings=current_report_findings,
        relevant_previous_report_comparisons=prev_report_comparisons[:10],
        recorded_medications=recorded_meds or ["No current or prior medications recorded"],
        doctor_confirmed_vs_patient_reported_distinction={
            "patient_reported_current": current_complaints,
            "doctor_confirmed_historical_diagnoses": [
                f"{pv.visit_date.strftime('%Y-%m-%d')}: {c.diagnosis or c.clinical_assessment}"
                for pv in previous_visits
                for c in pv.consultations
            ] or ["None recorded"],
            "unverified_ai_status": DISCLAIMER_TEXT,
        },
        missing_or_uncertain_information=missing_items or ["None identified"],
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(
        db,
        f"{' '.join(current_complaints)} {patient.existing_conditions or ''} history",
        categories=["symptom_assessment", "clinical_documentation", "laboratory_cbc"],
        limit=3,
    )
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Create a concise doctor-facing complete patient overview clearly distinguishing current vs historical records and patient-reported vs doctor-confirmed facts.",
        draft,
    )
    validated = PatientOverviewSchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text(f"TYPE 5: COMPLETE PATIENT OVERVIEW ({patient.permanent_patient_id})", validated, mode_note)

    source_recs = [("visit", v.id, f"Visit {v.visit_code} ({v.visit_date.strftime('%Y-%m-%d')})") for v in visits[:5]]
    return _save_summary(
        db,
        patient=patient,
        visit_id=current_visit.id if current_visit else None,
        summary_type="patient_overview",
        source_reference=f"Complete Overview {patient.permanent_patient_id}",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=source_recs,
    )


# --- Type 6: Report Comparison Summary ---
def generate_report_comparison_summary(
    db: Session,
    *,
    patient: Patient,
    report_ids: Optional[List[int]] = None,
) -> AISummary:
    query = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id)
    if report_ids:
        query = query.filter(MedicalReport.id.in_(report_ids))
    reports = query.order_by(MedicalReport.report_date.asc(), MedicalReport.id.asc()).all()

    by_test: Dict[str, List[Dict[str, Any]]] = {}
    dates = []
    for r in reports:
        d_str = str(r.report_date)
        if d_str not in dates:
            dates.append(d_str)
        for f in r.findings:
            by_test.setdefault(f.test_name, []).append(
                {
                    "report_date": d_str,
                    "report_id": r.id,
                    "observed_value": f.observed_value,
                    "unit": f.unit,
                    "supplied_reference_range": f.reference_range,
                    "status_relative_to_range": f.status_relative_to_range,
                }
            )

    trends = [
        {
            "test_name": test_name,
            "previous_value": entries[0]["observed_value"] if len(entries) > 1 else "No prior comparison",
            "previous_date": entries[0]["report_date"] if len(entries) > 1 else None,
            "current_value": entries[-1]["observed_value"],
            "current_date": entries[-1]["report_date"],
            "supplied_reference_range": entries[-1]["supplied_reference_range"],
            "chronological_values": entries,
        }
        for test_name, entries in by_test.items()
    ]

    draft = ReportComparisonSchema(
        permanent_patient_id=patient.permanent_patient_id,
        compared_report_dates=dates,
        parameter_trends=trends,
        uncertainty_and_context_note=(
            "Values are presented chronologically with exact units and supplied reference intervals. "
            "Changes between dates are not automatically classified as clinically significant without physician review."
        ),
    ).model_dump()

    knowledge_docs = retrieve_relevant_knowledge(db, "laboratory comparison longitudinal reference range", categories=["laboratory_cbc", "laboratory_metabolic"], limit=2)
    structured, provider, model_id, mode_note = _call_gemini_structured(
        "Compare multiple laboratory reports chronologically without altering values or claiming clinical significance autonomously.",
        draft,
    )
    validated = ReportComparisonSchema(**{**draft, **{k: v for k, v in structured.items() if k in draft}}).model_dump()
    text_out = _format_summary_text(f"TYPE 6: LONGITUDINAL REPORT COMPARISON ({patient.permanent_patient_id})", validated, mode_note)

    return _save_summary(
        db,
        patient=patient,
        visit_id=reports[-1].visit_id if reports else None,
        summary_type="report_comparison",
        source_reference=f"Compared {len(reports)} reports",
        structured_json={**validated, "mode_note": mode_note},
        summary_text=text_out,
        provider=provider,
        model_id=model_id,
        knowledge_docs=knowledge_docs,
        source_records=[("report", r.id, f"{r.category} ({r.report_date})") for r in reports],
    )
