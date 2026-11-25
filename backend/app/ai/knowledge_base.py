"""
MEDORA Medical Knowledge Layer
Stores and retrieves trusted medical reference metadata (WHO, ICMR, NHM, MoHFW, MedlinePlus, LabRef).
Strictly separated from patient-specific records.
"""

from typing import List
from sqlalchemy.orm import Session

from app.models.ai_knowledge import MedicalKnowledgeDocument


DEFAULT_KNOWLEDGE_DOCUMENTS = [
    {
        "source_name": "WHO",
        "document_title": "Integrated Management of Adolescent and Adult Illness (IMAI) - Acute Febrile Illness Triage",
        "publication_date": "2023-05-01",
        "last_updated_date": "2024-11-15",
        "category": "symptom_assessment",
        "source_url": "https://www.who.int/publications/i/item/9789241548298",
        "version": "v2.1",
        "retrieval_date": "2026-10-01",
        "content_snippet": "When summarizing acute fever presentations, document measured temperature if recorded, fever duration, diurnal pattern, associated warning signs (breathing difficulty, persistent vomiting, chest pain, altered consciousness), and prior antipyretic or antibiotic use.",
        "keywords_json": ["fever", "headache", "body pain", "fatigue", "காய்ச்சல்", "தலைவலி", "temperature", "acute"],
    },
    {
        "source_name": "ICMR",
        "document_title": "ICMR Standard Treatment Workflows - Common Outpatient Presentations & CBC Interpretation",
        "publication_date": "2024-01-10",
        "last_updated_date": "2025-06-20",
        "category": "laboratory_cbc",
        "source_url": "https://stw.icmr.org.in/",
        "version": "2024.2",
        "retrieval_date": "2026-10-01",
        "content_snippet": "Complete Blood Count (CBC) interpretation requires comparing observed Hemoglobin, Total WBC, Differential, and Platelet values strictly against the laboratory's supplied age- and sex-specific reference intervals alongside clinical context.",
        "keywords_json": ["cbc", "hemoglobin", "wbc", "platelets", "rbc", "blood count", "anemia"],
    },
    {
        "source_name": "MoHFW India",
        "document_title": "National Programme for Prevention and Control of Non-Communicable Diseases - Diabetes & Lipid Screening",
        "publication_date": "2023-08-12",
        "last_updated_date": "2025-03-01",
        "category": "laboratory_metabolic",
        "source_url": "https://mohfw.gov.in/",
        "version": "3.0",
        "retrieval_date": "2026-10-01",
        "content_snippet": "Longitudinal glycemic and lipid tracking should preserve exact fasting/postprandial status, measurement units (mg/dL, %), and specimen collection dates without equating single borderline shifts to confirmed clinical diagnoses.",
        "keywords_json": ["blood sugar", "glucose", "fbs", "hba1c", "lipid", "cholesterol", "ldl", "hdl", "triglycerides"],
    },
    {
        "source_name": "MedlinePlus",
        "document_title": "Medical Encyclopedia & Laboratory Test Information - Thyroid, Liver, and Kidney Panels",
        "publication_date": "2024-04-18",
        "last_updated_date": "2026-01-15",
        "category": "laboratory_organ_panels",
        "source_url": "https://medlineplus.gov/lab-tests/",
        "version": "2026.1",
        "retrieval_date": "2026-10-01",
        "content_snippet": "Organ function tests (TSH/T3/T4, SGPT/SGOT/Bilirubin, Serum Creatinine/Urea) vary across assay methodologies; always retain the performing laboratory's supplied reference range and flag missing assay units.",
        "keywords_json": ["thyroid", "tsh", "t3", "t4", "liver", "lft", "sgpt", "sgot", "kidney", "kft", "creatinine", "urea"],
    },
    {
        "source_name": "NHM India",
        "document_title": "National Health Mission - Multilingual Patient Intake & Longitudinal Record Continuity Guidelines",
        "publication_date": "2024-02-05",
        "last_updated_date": "2025-09-10",
        "category": "clinical_documentation",
        "source_url": "https://nhm.gov.in/",
        "version": "1.4",
        "retrieval_date": "2026-10-01",
        "content_snippet": "Patient-reported symptoms collected in regional languages such as Tamil must retain the original verbatim statement alongside structured clinical translation, clearly separating patient self-reports from physician examination findings.",
        "keywords_json": ["tamil", "history", "consultation", "longitudinal", "follow-up", "symptoms", "cough", "dizziness", "joint pain"],
    },
]


def seed_knowledge_documents(db: Session) -> None:
    if db.query(MedicalKnowledgeDocument).count() > 0:
        return
    for doc in DEFAULT_KNOWLEDGE_DOCUMENTS:
        db.add(MedicalKnowledgeDocument(**doc))
    db.commit()


def retrieve_relevant_knowledge(db: Session, query_text: str, categories: List[str] = None, limit: int = 3) -> List[MedicalKnowledgeDocument]:
    """Retrieve only relevant knowledge documents based on keywords and optional categories."""
    docs = db.query(MedicalKnowledgeDocument).all()
    q_lower = (query_text or "").lower()
    scored = []
    for doc in docs:
        score = 0
        if categories and doc.category in categories:
            score += 3
        for kw in (doc.keywords_json or []):
            if kw.lower() in q_lower:
                score += 2
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]
