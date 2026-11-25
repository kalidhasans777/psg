"""
MEDORA Medical Terminology Layer
Supports Tamil <-> English symptom mapping, colloquial Tamil healthcare expressions,
duration/severity extraction, and laboratory test normalization.
"""

from typing import Dict, List, Tuple
import re

TAMIL_TO_ENGLISH_SYMPTOMS: List[Tuple[List[str], str, str]] = [
    (["காய்ச்சல்", "ஜுரம்", "சுரம்", "kaichal", "fever", "temperature"], "Fever", "காய்ச்சல்"),
    (["தலைவலி", "தலை வலி", "thalaivali", "headache"], "Headache", "தலைவலி"),
    (["வயிற்று வலி", "வயிறு வலி", "vayiru vali", "stomach pain", "abdominal pain", "tummy ache"], "Abdominal / Stomach pain", "வயிற்று வலி"),
    (["நெஞ்சு வலி", "மார்பு வலி", "nenju vali", "chest pain"], "Chest pain", "நெஞ்சு வலி"),
    (["இருமல்", "irumal", "cough"], "Cough", "இருமல்"),
    (["சளி", "மூக்கொழுகுதல்", "sali", "cold", "phlegm", "runny nose"], "Cold / Phlegm", "சளி"),
    (["வாந்தி", "குமட்டல்", "vanthi", "vomiting", "nausea"], "Vomiting / Nausea", "வாந்தி"),
    (["வயிற்றுப்போக்கு", "பேதி", "diarrhoea", "diarrhea", "loose motion"], "Diarrhoea", "வயிற்றுப்போக்கு"),
    (["மூச்சுத்திணறல்", "மூச்சு விட சிரமம்", "moochu thinaral", "breathing difficulty", "shortness of breath", "breathlessness"], "Breathing difficulty", "மூச்சுத்திணறல்"),
    (["உடல் வலி", "உடம்பு வலி", "உடம்பு வலிக்கிறது", "udambu vali", "body pain", "body ache"], "Body pain", "உடல் வலி"),
    (["சோர்வு", "அசதி", "களைப்பு", "sorvu", "fatigue", "tired", "weakness"], "Fatigue / Weakness", "சோர்வு"),
    (["தலைச்சுற்றல்", "மயக்கம்", "thalaichutral", "dizziness", "giddiness", "vertigo"], "Dizziness", "தலைச்சுற்றல்"),
    (["பசியின்மை", "பசி இல்லை", "pasi illai", "loss of appetite", "poor appetite"], "Loss of appetite", "பசியின்மை"),
    (["தூக்கமின்மை", "தூக்கம் வரவில்லை", "தூங்க முடியவில்லை", "difficulty sleeping", "insomnia", "sleep problem"], "Difficulty sleeping", "தூக்கமின்மை"),
    (["மூட்டு வலி", "கால் வலி", "கை வலி", "moottu vali", "joint pain"], "Joint pain", "மூட்டு வலி"),
    (["தொண்டை வலி", "thondai vali", "sore throat", "throat pain"], "Sore throat", "தொண்டை வலி"),
    (["முதுகு வலி", "muthugu vali", "back pain"], "Back pain", "முதுகு வலி"),
    (["தோல் அரிப்பு", "தடிப்பு", "skin rash", "itching"], "Skin rash / Itching", "தோல் அரிப்பு"),
]

TAMIL_DURATION_PATTERNS: List[Tuple[str, str]] = [
    (r"ஒரு\s*நாள்|1\s*நாள்", "1 day"),
    (r"இரண்டு\s*நாள்|இரண்டு\s*நாட்களாக|2\s*நாள்", "2 days"),
    (r"மூன்று\s*நாள்|மூன்று\s*நாட்களாக|மூனு\s*நாள்|3\s*நாள்", "3 days"),
    (r"நான்கு\s*நாள்|நான்கு\s*நாட்களாக|4\s*நாள்", "4 days"),
    (r"ஐந்து\s*நாள்|ஐந்து\s*நாட்களாக|5\s*நாள்", "5 days"),
    (r"ஒரு\s*வாரம்|1\s*வாரம்", "1 week"),
    (r"இரண்டு\s*வாரம்|2\s*வாரம்", "2 weeks"),
    (r"ஒரு\s*மாதம்|1\s*மாதம்", "1 month"),
    (r"(\d+)\s*(?:day|days|நாள்|நாட்களாக|நாட்கள்)", r"\1 days"),
    (r"(\d+)\s*(?:week|weeks|வாரம்|வாரங்களாக)", r"\1 weeks"),
    (r"(\d+)\s*(?:month|months|மாதம்|மாதங்களாக)", r"\1 months"),
    (r"(one|two|three|four|five|six|seven)\s*(day|days|week|weeks|month|months)", r"\1 \2"),
]

TAMIL_NO_MEDICATION_PHRASES = [
    "இல்லை", "எதுவும் இல்லை", "மாத்திரை எடுக்கவில்லை", "மருந்து எடுக்கவில்லை",
    "no medicine", "no medication", "haven't taken any medicine", "not taking any", "none"
]

LAB_TEST_ALIASES: Dict[str, str] = {
    "hb": "Hemoglobin",
    "haemoglobin": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "wbc": "WBC (Total Leukocyte Count)",
    "tlc": "WBC (Total Leukocyte Count)",
    "total wbc": "WBC (Total Leukocyte Count)",
    "white blood cell": "WBC (Total Leukocyte Count)",
    "rbc": "RBC Count",
    "platelets": "Platelet Count",
    "platelet count": "Platelet Count",
    "plt": "Platelet Count",
    "fbs": "Fasting Blood Glucose",
    "fasting blood sugar": "Fasting Blood Glucose",
    "ppbs": "Postprandial Blood Glucose",
    "rbs": "Random Blood Glucose",
    "hba1c": "HbA1c (Glycated Hemoglobin)",
    "tsh": "Thyroid Stimulating Hormone (TSH)",
    "t3": "Triiodothyronine (T3)",
    "t4": "Thyroxine (T4)",
    "total cholesterol": "Total Cholesterol",
    "ldl": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "triglycerides": "Triglycerides",
    "sgpt": "SGPT / ALT",
    "alt": "SGPT / ALT",
    "sgot": "SGOT / AST",
    "ast": "SGOT / AST",
    "bilirubin": "Total Bilirubin",
    "creatinine": "Serum Creatinine",
    "serum creatinine": "Serum Creatinine",
    "urea": "Blood Urea",
    "bun": "Blood Urea Nitrogen (BUN)",
}


def extract_medical_terms(text: str) -> Dict[str, object]:
    """Extracts standardized English symptoms, matched Tamil terms, duration, and timing cues."""
    lower = (text or "").lower()
    matched_symptoms: List[Dict[str, str]] = []
    seen_en = set()

    for aliases, en_label, ta_label in TAMIL_TO_ENGLISH_SYMPTOMS:
        for alias in aliases:
            if alias.lower() in lower:
                if en_label not in seen_en:
                    seen_en.add(en_label)
                    matched_symptoms.append({"english": en_label, "tamil": ta_label, "matched_phrase": alias})
                break

    duration = None
    for pattern, replacement in TAMIL_DURATION_PATTERNS:
        m = re.search(pattern, lower, flags=re.IGNORECASE)
        if m:
            if "\\" in replacement:
                duration = m.expand(replacement).strip()
            else:
                duration = replacement
            break

    additional_cues: List[str] = []
    if any(k in lower for k in ["இரவில்", "இரவு", "evening", "night"]):
        additional_cues.append("Worse or more noticeable in the evening/night")
    if any(k in lower for k in ["காலை", "morning"]):
        additional_cues.append("Noticed in the morning")
    if any(k in lower for k in ["அதிகமாக", "severe", "very"]):
        additional_cues.append("Patient reports marked intensity")

    no_meds = any(phrase in lower for phrase in TAMIL_NO_MEDICATION_PHRASES)

    return {
        "matched_symptoms": matched_symptoms,
        "english_complaints": [s["english"] for s in matched_symptoms],
        "tamil_complaints": [s["tamil"] for s in matched_symptoms],
        "detected_duration": duration,
        "additional_cues": additional_cues,
        "no_medication_cue": no_meds,
    }
