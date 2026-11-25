"""
MEDORA Synthetic Demonstration Data Seeder
Clearly labels all seeded patients and clinical records as synthetic demonstration data.
Creates real synthetic PDF medical reports via ReportLab so PDF viewing, downloading,
and extraction work end-to-end.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.ai.knowledge_base import seed_knowledge_documents
from app.config import get_settings
from app.models.ai_knowledge import AISummary, AuditLog
from app.models.clinical import (
    Appointment,
    DoctorConsultation,
    MedicalReport,
    Prescription,
    ReportFinding,
    Symptom,
    Visit,
)
from app.models.patient import Notification, Patient, PatientConsent, PatientIdSequence
from app.models.user import Department, Doctor, User
from app.reports.processor import process_report_file
from app.security.auth import hash_password
from app.summarization.engine import generate_history_summary, generate_report_summary, generate_symptom_summary

settings = get_settings()


def _create_synthetic_lab_pdf(
    output_path: Path,
    *,
    patient_name: str,
    permanent_id: str,
    report_title: str,
    report_date_str: str,
    rows: List[Tuple[str, str, str, str]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 55, "MEDORA CLINICAL DIAGNOSTICS (SYNTHETIC DEMO LAB)")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 75, f"Report Type: {report_title}   |   Report Date: {report_date_str}")
    c.drawString(50, height - 92, f"Patient Name: {patient_name}   |   Permanent Patient ID: {permanent_id}")
    c.line(50, height - 105, width - 50, height - 105)

    y = height - 135
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Test Parameters & Observed Values (Synthetic Demo Data):")
    y -= 24

    c.setFont("Helvetica", 10)
    for test_name, observed_val, unit, ref_range in rows:
        line_text = f"{test_name}: {observed_val} {unit} (Reference Range: {ref_range})"
        c.drawString(55, y, line_text)
        y -= 20

    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Notice: Synthetic demonstration report generated for MEDORA hackathon evaluation.")
    c.save()


def ensure_sample_cbc_pdf() -> Path:
    sample_path = Path(__file__).resolve().parent.parent / "sample_reports" / "sample_cbc_demo_patient.pdf"
    if not sample_path.exists():
        _create_synthetic_lab_pdf(
            sample_path,
            patient_name="Demo Patient",
            permanent_id="MED-2026-00125",
            report_title="Complete Blood Count (CBC)",
            report_date_str="2026-11-24",
            rows=[
                ("Hemoglobin", "10", "g/dL", "13-17 g/dL"),
                ("WBC", "7000", "cells/uL", "4000-11000 cells/uL"),
                ("Platelets", "2.5", "lakh/uL", "1.5-4.5 lakh/uL"),
                ("RBC", "4.4", "million/uL", "4.5-5.9 million/uL"),
            ],
        )
    return sample_path


def seed_database(db: Session) -> None:
    ensure_sample_cbc_pdf()
    seed_knowledge_documents(db)

    if db.query(User).count() > 0:
        return

    # 1. Departments (8 hospital departments)
    departments_data = [
        ("General Medicine", "GEN", "Primary adult medical evaluation, fever, chronic care & longitudinal follow-up", "Dr. Kavitha Sundaram"),
        ("Cardiology", "CARD", "Heart health, blood pressure, lipid & ECG evaluation", "Dr. Rajesh Nair"),
        ("Neurology", "NEUR", "Headache, dizziness, migraine & neurological care", "Dr. Senthil Kumar"),
        ("Orthopaedics", "ORTH", "Joint pain, spine & musculoskeletal care", "Dr. Deepak Verma"),
        ("Dermatology", "DERM", "Skin, allergy & dermatological care", "Dr. Priya Menon"),
        ("Paediatrics", "PAED", "Child and adolescent healthcare", "Dr. Meenakshi Iyer"),
        ("ENT", "ENT", "Ear, nose, throat & respiratory allergy care", "Dr. Arvind Raj"),
        ("Emergency Medicine", "EMER", "Acute triage & urgent stabilization", "Dr. Vikram Rao"),
    ]
    dept_map = {}
    for name, code, desc, head in departments_data:
        d = Department(name=name, code=code, description=desc, head_doctor_name=head, is_active=True)
        db.add(d)
        db.flush()
        dept_map[code] = d

    # 2. Hospital Admin
    admin_user = User(
        email="admin@medora.health",
        phone="9000000001",
        password_hash=hash_password("Admin@1234"),
        role="admin",
        full_name="Hospital Administrator (Demo)",
        is_active=True,
    )
    db.add(admin_user)

    # 3. Doctors (4 doctors)
    doctors_seed = [
        ("Dr. Kavitha Sundaram", "doctor@medora.health", "9000000101", "GEN", "TNMC-2015-44102", "Internal & General Medicine", "MBBS, MD (General Medicine)"),
        ("Dr. Rajesh Nair", "cardio@medora.health", "9000000102", "CARD", "TNMC-2012-31890", "Interventional & Preventive Cardiology", "MBBS, MD, DM (Cardiology)"),
        ("Dr. Meenakshi Iyer", "paediatrics@medora.health", "9000000103", "PAED", "TNMC-2017-52014", "Paediatrics & Adolescent Care", "MBBS, MD (Paediatrics)"),
        ("Dr. Arvind Raj", "ent@medora.health", "9000000104", "ENT", "TNMC-2016-48901", "ENT & Airway Care", "MBBS, MS (ENT)"),
    ]
    doc_objs = []
    for full_name, email, phone, dept_code, lic, spec, qual in doctors_seed:
        u = User(
            email=email,
            phone=phone,
            password_hash=hash_password("Doctor@1234"),
            role="doctor",
            full_name=full_name,
            is_active=True,
        )
        db.add(u)
        db.flush()
        doc = Doctor(
            user_id=u.id,
            department_id=dept_map[dept_code].id,
            license_number=lic,
            specialization=spec,
            qualification=qual,
            phone=phone,
            is_available=True,
            is_active=True,
        )
        db.add(doc)
        db.flush()
        doc_objs.append(doc)

    # 4. Synthetic Patients (5 patients, starting with MED-2026-00125 Demo Patient)
    patients_seed = [
        {
            "pid": "MED-2026-00125",
            "full_name": "Demo Patient",
            "email": "patient@medora.health",
            "phone": "9876543210",
            "password": "Patient@1234",
            "dob": date(1988, 5, 14),
            "gender": "Male",
            "address": "42 Anna Salai, Teynampet, Chennai, Tamil Nadu 600018",
            "emergency_contact": "Priya Krishnan (Spouse) - 9876543299",
            "known_allergies": "Penicillin (mild skin rash reported in 2024)",
            "existing_conditions": "Mild Iron Deficiency Tendency; Borderline Fasting Glucose (2027)",
            "relevant_medical_history": "Synthetic multi-year longitudinal demonstration patient across 2026, 2027, and 2029 visits.",
            "blood_group": "O+",
        },
        {
            "pid": "MED-2026-00126",
            "full_name": "Patient A (Ananya Ramesh)",
            "email": "patienta@medora.health",
            "phone": "9876500001",
            "password": "PatientA@123",
            "dob": date(1995, 8, 22),
            "gender": "Female",
            "address": "18 Race Course Road, Coimbatore, Tamil Nadu 641018",
            "emergency_contact": "Ramesh K - 9876500091",
            "known_allergies": "Sulfa drugs",
            "existing_conditions": "Seasonal Allergic Rhinitis",
            "relevant_medical_history": "Synthetic Patient A for privacy isolation & RBAC verification.",
            "blood_group": "A+",
        },
        {
            "pid": "MED-2026-00127",
            "full_name": "Patient B (Suresh Babu)",
            "email": "patientb@medora.health",
            "phone": "9876500002",
            "password": "PatientB@123",
            "dob": date(1979, 11, 3),
            "gender": "Male",
            "address": "77 Avinashi Road, Peelamedu, Coimbatore, Tamil Nadu 641004",
            "emergency_contact": "Kala S - 9876500092",
            "known_allergies": "None known",
            "existing_conditions": "Hypertension (controlled)",
            "relevant_medical_history": "Synthetic Patient B for privacy isolation & RBAC verification.",
            "blood_group": "B+",
        },
        {
            "pid": "MED-2026-00128",
            "full_name": "Lakshmi Narayanan",
            "email": "lakshmi@medora.health",
            "phone": "9876500003",
            "password": "Patient@1234",
            "dob": date(1962, 2, 19),
            "gender": "Female",
            "address": "14 West Masi Street, Madurai, Tamil Nadu 625001",
            "emergency_contact": "Srinivasan N (Son) - 9876500093",
            "known_allergies": "Aspirin sensitivity",
            "existing_conditions": "Type 2 Diabetes Mellitus, Osteoarthritis",
            "relevant_medical_history": "Prefers Tamil voice intake for reporting symptoms.",
            "blood_group": "AB+",
        },
        {
            "pid": "MED-2026-00129",
            "full_name": "Karthik Subramanian",
            "email": "karthik@medora.health",
            "phone": "9876500004",
            "password": "Patient@1234",
            "dob": date(2001, 7, 9),
            "gender": "Male",
            "address": "9 Thillai Nagar, Tiruchirappalli, Tamil Nadu 620018",
            "emergency_contact": "Subramanian V - 9876500094",
            "known_allergies": "None recorded",
            "existing_conditions": "None recorded",
            "relevant_medical_history": "Occasional migraine episodes.",
            "blood_group": "O-",
        },
    ]

    patient_map = {}
    for pdata in patients_seed:
        u = User(
            email=pdata["email"],
            phone=pdata["phone"],
            password_hash=hash_password(pdata["password"]),
            role="patient",
            full_name=pdata["full_name"],
            is_active=True,
        )
        db.add(u)
        db.flush()
        p = Patient(
            user_id=u.id,
            permanent_patient_id=pdata["pid"],
            full_name=pdata["full_name"],
            date_of_birth=pdata["dob"],
            gender=pdata["gender"],
            phone=pdata["phone"],
            email=pdata["email"],
            address=pdata["address"],
            emergency_contact=pdata["emergency_contact"],
            known_allergies=pdata["known_allergies"],
            existing_conditions=pdata["existing_conditions"],
            relevant_medical_history=pdata["relevant_medical_history"],
            blood_group=pdata["blood_group"],
            registration_date=date(2026, 3, 12) if pdata["pid"] == "MED-2026-00125" else date.today(),
            account_status="active",
            consent_status=True,
            is_synthetic_demo=True,
        )
        db.add(p)
        db.flush()
        db.add(PatientConsent(patient_id=p.id, consent_type="privacy_policy", consented=True))
        db.add(PatientConsent(patient_id=p.id, consent_type="data_storage", consented=True))
        db.add(PatientConsent(patient_id=p.id, consent_type="ai_summarization", consented=True))
        patient_map[pdata["pid"]] = p

    # Set sequence for current year (2026) past 00129 so next registration gets MED-2026-00130
    db.add(PatientIdSequence(year=2026, last_value=129))
    db.flush()

    # 5. Multi-year Visits for Demo Patient MED-2026-00125 (2026, 2027, 2029)
    demo_p = patient_map["MED-2026-00125"]
    primary_doc = doc_objs[0]
    cardio_doc = doc_objs[1]

    # --- 2026 First Visit ---
    v_2026 = Visit(
        visit_code="VIS-2026-00001",
        patient_id=demo_p.id,
        doctor_id=primary_doc.id,
        department_id=dept_map["GEN"].id,
        visit_date=datetime(2026, 3, 12, 10, 30, tzinfo=timezone.utc),
        visit_type="initial",
        chief_complaint="Fever and headache for 3 days (Tamil voice report)",
        status="completed",
    )
    db.add(v_2026)
    db.flush()

    sym_2026 = Symptom(
        visit_id=v_2026.id,
        patient_id=demo_p.id,
        source_channel="voice_ta",
        language="ta-IN",
        raw_transcript="எனக்கு மூன்று நாட்களாக காய்ச்சல் இருக்கு. தலைவலியும் உடம்பு வலியும் இருக்கு.",
        edited_transcript="எனக்கு மூன்று நாட்களாக காய்ச்சல் இருக்கு. தலைவலியும் உடம்பு வலியும் இருக்கு.",
        description="Fever, headache, and body pain for three days with evening tiredness.",
        duration="3 days",
        severity="moderate",
        current_medications="No medication reported",
        patient_confirmed=True,
        confirmed_at=datetime(2026, 3, 12, 10, 20, tzinfo=timezone.utc),
    )
    db.add(sym_2026)

    pdf_2026 = Path(settings.UPLOAD_DIR) / demo_p.permanent_patient_id / "2026_cbc_report.pdf"
    _create_synthetic_lab_pdf(
        pdf_2026,
        patient_name=demo_p.full_name,
        permanent_id=demo_p.permanent_patient_id,
        report_title="Complete Blood Count (CBC) - 2026 First Visit",
        report_date_str="2026-03-12",
        rows=[
            ("Hemoglobin", "10.8", "g/dL", "13-17 g/dL"),
            ("WBC", "12400", "cells/uL", "4000-11000 cells/uL"),
            ("Platelets", "2.1", "lakh/uL", "1.5-4.5 lakh/uL"),
        ],
    )
    ext_2026 = process_report_file(pdf_2026, "application/pdf")
    rep_2026 = MedicalReport(
        visit_id=v_2026.id,
        patient_id=demo_p.id,
        category="CBC",
        file_name="2026_cbc_report.pdf",
        stored_path=str(pdf_2026),
        mime_type="application/pdf",
        file_size_bytes=pdf_2026.stat().st_size,
        report_date=date(2026, 3, 12),
        processing_status="completed",
        extracted_text=ext_2026["extracted_text"],
        ocr_confidence_note=ext_2026["ocr_confidence_note"],
        verification_status="verified",
        verified_by_doctor_id=primary_doc.id,
        verified_at=datetime(2026, 3, 12, 11, 15, tzinfo=timezone.utc),
    )
    db.add(rep_2026)
    db.flush()
    for f in ext_2026["findings"]:
        db.add(ReportFinding(report_id=rep_2026.id, **{k: v for k, v in f.items()}))

    con_2026 = DoctorConsultation(
        visit_id=v_2026.id,
        patient_id=demo_p.id,
        doctor_id=primary_doc.id,
        chief_complaints="3-day fever, headache, and generalized body ache",
        observations="Temp 100.8°F, mild pallor noted, throat clear, hydration adequate.",
        clinical_assessment="Acute viral febrile syndrome with mild anemia noted on CBC.",
        diagnosis="Acute Viral Fever; Mild Anemia",
        treatment_plan="Antipyretic symptomatic care, oral hydration, iron-rich diet and hematinic supplement.",
        follow_up_date=date(2026, 3, 26),
        consultation_notes="Penicillin allergy noted in profile; avoided beta-lactams.",
    )
    db.add(con_2026)
    db.flush()
    db.add(
        Prescription(
            consultation_id=con_2026.id,
            visit_id=v_2026.id,
            patient_id=demo_p.id,
            doctor_id=primary_doc.id,
            medications_json=[
                {"medicine_name": "Paracetamol 500mg", "dosage": "1 tablet", "frequency": "SOS (max 3/day)", "duration": "3 days"},
                {"medicine_name": "Ferrous Ascorbate + Folic Acid", "dosage": "1 tablet", "frequency": "Once daily after lunch", "duration": "30 days"},
            ],
            instructions="Drink plenty of fluids; return if fever persists beyond 48 hours.",
            issued_date=date(2026, 3, 12),
        )
    )

    # --- 2027 Second Visit ---
    v_2027 = Visit(
        visit_code="VIS-2027-00002",
        patient_id=demo_p.id,
        doctor_id=primary_doc.id,
        department_id=dept_map["GEN"].id,
        visit_date=datetime(2027, 7, 19, 11, 0, tzinfo=timezone.utc),
        visit_type="follow_up",
        chief_complaint="Persistent dry cough, fatigue, and routine metabolic screening",
        status="completed",
    )
    db.add(v_2027)
    db.flush()

    db.add(
        Symptom(
            visit_id=v_2027.id,
            patient_id=demo_p.id,
            source_channel="text",
            language="en-IN",
            description="Dry cough for 1 week and persistent fatigue in the afternoons.",
            duration="1 week",
            severity="mild",
            current_medications="Occasional warm salt water gargles",
            patient_confirmed=True,
        )
    )

    pdf_2027 = Path(settings.UPLOAD_DIR) / demo_p.permanent_patient_id / "2027_cbc_glucose_report.pdf"
    _create_synthetic_lab_pdf(
        pdf_2027,
        patient_name=demo_p.full_name,
        permanent_id=demo_p.permanent_patient_id,
        report_title="CBC & Fasting Blood Glucose - 2027 Second Visit",
        report_date_str="2027-07-19",
        rows=[
            ("Hemoglobin", "11.6", "g/dL", "13-17 g/dL"),
            ("WBC", "8200", "cells/uL", "4000-11000 cells/uL"),
            ("Platelets", "2.4", "lakh/uL", "1.5-4.5 lakh/uL"),
            ("Fasting Blood Sugar", "118", "mg/dL", "70-100 mg/dL"),
        ],
    )
    ext_2027 = process_report_file(pdf_2027, "application/pdf")
    rep_2027 = MedicalReport(
        visit_id=v_2027.id,
        patient_id=demo_p.id,
        category="Blood Sugar",
        file_name="2027_cbc_glucose_report.pdf",
        stored_path=str(pdf_2027),
        mime_type="application/pdf",
        file_size_bytes=pdf_2027.stat().st_size,
        report_date=date(2027, 7, 19),
        processing_status="completed",
        extracted_text=ext_2027["extracted_text"],
        ocr_confidence_note=ext_2027["ocr_confidence_note"],
        verification_status="verified",
        verified_by_doctor_id=primary_doc.id,
    )
    db.add(rep_2027)
    db.flush()
    for f in ext_2027["findings"]:
        db.add(ReportFinding(report_id=rep_2027.id, **{k: v for k, v in f.items()}))

    con_2027 = DoctorConsultation(
        visit_id=v_2027.id,
        patient_id=demo_p.id,
        doctor_id=primary_doc.id,
        chief_complaints="Dry cough for 1 week; afternoon tiredness",
        observations="Afebrile, lungs clear on auscultation, BP 122/78 mmHg.",
        clinical_assessment="Post-infectious airway sensitivity; borderline impaired fasting glucose (118 mg/dL).",
        diagnosis="Subacute Cough; Impaired Fasting Glucose (Borderline)",
        treatment_plan="Dietary sugar moderation, regular brisk walking, steam inhalation, follow-up HbA1c.",
        follow_up_date=date(2027, 10, 19),
        consultation_notes="Hemoglobin improved from 10.8 (2026) to 11.6 g/dL.",
    )
    db.add(con_2027)

    # --- 2029 Third Visit ---
    v_2029 = Visit(
        visit_code="VIS-2029-00003",
        patient_id=demo_p.id,
        doctor_id=cardio_doc.id,
        department_id=dept_map["CARD"].id,
        visit_date=datetime(2029, 2, 10, 9, 45, tzinfo=timezone.utc),
        visit_type="outpatient",
        chief_complaint="Joint pain, occasional dizziness, and lipid/thyroid checkup",
        status="in_progress",
    )
    db.add(v_2029)
    db.flush()

    sym_2029 = Symptom(
        visit_id=v_2029.id,
        patient_id=demo_p.id,
        source_channel="voice_ta",
        language="ta-IN",
        raw_transcript="சில நாட்களாக மூட்டு வலியும் லேசான தலைச்சுற்றலும் இருக்கிறது.",
        edited_transcript="சில நாட்களாக மூட்டு வலியும் லேசான தலைச்சுற்றலும் இருக்கிறது.",
        description="Joint pain and mild dizziness for a few days.",
        duration="5 days",
        severity="moderate",
        current_medications="None currently",
        patient_confirmed=True,
    )
    db.add(sym_2029)

    pdf_2029 = Path(settings.UPLOAD_DIR) / demo_p.permanent_patient_id / "2029_lipid_thyroid_report.pdf"
    _create_synthetic_lab_pdf(
        pdf_2029,
        patient_name=demo_p.full_name,
        permanent_id=demo_p.permanent_patient_id,
        report_title="Lipid Profile & Thyroid Function - 2029 Third Visit",
        report_date_str="2029-02-10",
        rows=[
            ("Hemoglobin", "12.9", "g/dL", "13-17 g/dL"),
            ("Total Cholesterol", "214", "mg/dL", "125-200 mg/dL"),
            ("LDL", "138", "mg/dL", "50-100 mg/dL"),
            ("HDL", "44", "mg/dL", "40-60 mg/dL"),
            ("TSH", "3.4", "mIU/L", "0.4-4.5 mIU/L"),
        ],
    )
    ext_2029 = process_report_file(pdf_2029, "application/pdf")
    rep_2029 = MedicalReport(
        visit_id=v_2029.id,
        patient_id=demo_p.id,
        category="Lipid Profile",
        file_name="2029_lipid_thyroid_report.pdf",
        stored_path=str(pdf_2029),
        mime_type="application/pdf",
        file_size_bytes=pdf_2029.stat().st_size,
        report_date=date(2029, 2, 10),
        processing_status="completed",
        extracted_text=ext_2029["extracted_text"],
        ocr_confidence_note=ext_2029["ocr_confidence_note"],
        verification_status="pending",
    )
    db.add(rep_2029)
    db.flush()
    for f in ext_2029["findings"]:
        db.add(ReportFinding(report_id=rep_2029.id, **{k: v for k, v in f.items()}))

    db.commit()

    # Generate initial AI summaries for Demo Patient (pending doctor review on 2029 visit)
    generate_symptom_summary(db, patient=demo_p, visit_id=v_2029.id, symptom=sym_2029, language="ta-IN")
    generate_report_summary(db, patient=demo_p, report=rep_2029)
    generate_history_summary(db, patient=demo_p)

    # Seed visits & reports for Patient A, Patient B, Lakshmi, Karthik
    pa = patient_map["MED-2026-00126"]
    pb = patient_map["MED-2026-00127"]
    pl = patient_map["MED-2026-00128"]
    pk = patient_map["MED-2026-00129"]

    v_pa = Visit(visit_code="VIS-2026-00010", patient_id=pa.id, doctor_id=doc_objs[3].id, department_id=dept_map["ENT"].id, visit_type="outpatient", chief_complaint="Seasonal sneezing and nasal congestion", status="registered")
    v_pb = Visit(visit_code="VIS-2026-00011", patient_id=pb.id, doctor_id=cardio_doc.id, department_id=dept_map["CARD"].id, visit_type="follow_up", chief_complaint="Routine blood pressure review", status="registered")
    v_pl = Visit(visit_code="VIS-2026-00012", patient_id=pl.id, doctor_id=primary_doc.id, department_id=dept_map["GEN"].id, visit_type="outpatient", chief_complaint="இருமல் மற்றும் மூட்டு வலி (Cough & joint pain)", status="registered")
    v_pk = Visit(visit_code="VIS-2026-00013", patient_id=pk.id, doctor_id=primary_doc.id, department_id=dept_map["GEN"].id, visit_type="outpatient", chief_complaint="Headache for 2 days", status="registered")
    db.add_all([v_pa, v_pb, v_pl, v_pk])
    db.flush()

    db.add(Symptom(visit_id=v_pa.id, patient_id=pa.id, source_channel="text", language="en-IN", description="Patient A private clinical record: allergic rhinitis and sinus headache for 4 days.", duration="4 days", severity="mild"))
    db.add(Symptom(visit_id=v_pb.id, patient_id=pb.id, source_channel="text", language="en-IN", description="Patient B private clinical record: mild morning dizziness and hypertension follow-up.", duration="2 days", severity="moderate"))
    db.add(Symptom(visit_id=v_pl.id, patient_id=pl.id, source_channel="voice_ta", language="ta-IN", raw_transcript="எனக்கு இரண்டு நாட்களாக இருமலும் மூட்டு வலியும் இருக்கிறது.", edited_transcript="எனக்கு இரண்டு நாட்களாக இருமலும் மூட்டு வலியும் இருக்கிறது.", description="Cough and joint pain for 2 days.", duration="2 days", severity="moderate"))
    db.add(Symptom(visit_id=v_pk.id, patient_id=pk.id, source_channel="text", language="en-IN", description="Throbbing headache since yesterday evening.", duration="2 days", severity="moderate"))

    # Appointments for Today & Upcoming
    now = datetime.now(timezone.utc)
    db.add_all([
        Appointment(appointment_code="APT-2026-00001", patient_id=demo_p.id, doctor_id=primary_doc.id, department_id=dept_map["GEN"].id, scheduled_at=now + timedelta(hours=2), reason="Follow-up review of 2029 Lipid & Thyroid report", status="confirmed"),
        Appointment(appointment_code="APT-2026-00002", patient_id=pl.id, doctor_id=primary_doc.id, department_id=dept_map["GEN"].id, scheduled_at=now + timedelta(hours=3), reason="Tamil voice symptom consultation", status="scheduled"),
        Appointment(appointment_code="APT-2026-00003", patient_id=pb.id, doctor_id=cardio_doc.id, department_id=dept_map["CARD"].id, scheduled_at=now + timedelta(days=1), reason="Hypertension checkup", status="confirmed"),
    ])

    db.add_all([
        Notification(user_id=demo_p.user_id, title="Upcoming Appointment", message="Appointment APT-2026-00001 with Dr. Kavitha Sundaram is confirmed.", category="appointment"),
        Notification(user_id=demo_p.user_id, title="AI Overview Ready for Doctor Review", message="Your longitudinal medical overview across 2026, 2027, and 2029 visits is awaiting doctor verification.", category="ai_summary"),
    ])

    db.add(AuditLog(user_id=admin_user.id, user_role="admin", action="system_seeded_synthetic_data", resource_type="system", resource_id="seed", details_json={"patients": 5, "doctors": 4, "departments": 8}, status="success"))
    db.commit()
