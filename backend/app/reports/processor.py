"""
MEDORA Medical Report Upload & Processing Engine
Handles PDF text extraction, optional OCR / Gemini Vision, and structured lab finding extraction.
Never modifies the original uploaded document.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
from pypdf import PdfReader
from PIL import Image

from app.ai.terminology import LAB_TEST_ALIASES
from app.config import get_settings

settings = get_settings()

# Regex patterns to extract "<Test Name> : <value> <unit> (Ref / Reference Range: <low>-<high> <unit>)"
LAB_LINE_PATTERNS = [
    re.compile(
        r"^(?P<name>[A-Za-z0-9\s\(\)/\-]+?)\s*[:\-]\s*(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%µu]+(?:/[A-Za-zµ]+)?)\s*(?:.*?(?:ref(?:erence)?(?:\s*range)?|normal)\s*[:\-]?\s*(?P<range>\d+(?:\.\d+)?\s*[\-–to]+\s*\d+(?:\.\d+)?(?:\s*[A-Za-z/%µu]+(?:/[A-Za-zµ]+)?)?))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<name>Hemoglobin|Haemoglobin|Hb|WBC|Total\s*WBC|Platelets|Platelet\s*Count|RBC|Fasting\s*Blood\s*(?:Glucose|Sugar)|FBS|HbA1c|TSH|Total\s*Cholesterol|LDL|HDL|Triglycerides|SGPT|SGOT|Creatinine|Bilirubin|Urea)\s+(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%µu]+(?:/[A-Za-zµ]+)?)?\s+(?P<range>\d+(?:\.\d+)?\s*[\-–]\s*\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
]


def _normalize_test_name(raw_name: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw_name).strip(" :-.")
    lower = cleaned.lower()
    for alias, standard in LAB_TEST_ALIASES.items():
        if lower == alias or alias in lower:
            return standard
    return cleaned


def _compare_with_range(val_str: str, ref_range: Optional[str]) -> Tuple[str, bool]:
    if not ref_range:
        return "uncertain", True
    nums = re.findall(r"\d+(?:\.\d+)?", ref_range)
    try:
        val = float(val_str)
        if len(nums) >= 2:
            low, high = float(nums[0]), float(nums[1])
            if val < low:
                return "below", False
            if val > high:
                return "above", False
            return "within", False
    except ValueError:
        pass
    return "uncertain", True


def extract_structured_findings(raw_text: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    seen_tests = set()
    if not raw_text:
        return findings

    for line in raw_text.splitlines():
        line_clean = line.strip()
        if len(line_clean) < 4:
            continue
        # Skip header/metadata lines
        if any(h in line_clean.lower() for h in ["patient name", "patient id", "med-", "date:", "doctor:", "laboratory", "page ", "report id"]):
            continue

        matched = None
        for pat in LAB_LINE_PATTERNS:
            m = pat.match(line_clean)
            if m:
                matched = m
                break
        if not matched:
            continue

        raw_name = matched.group("name").strip()
        val_str = matched.group("val").strip()
        unit = (matched.groupdict().get("unit") or "").strip() or None
        ref_range = (matched.groupdict().get("range") or "").strip() or None

        # Only accept recognized lab test lines or lines that have a unit or reference range
        std_name = _normalize_test_name(raw_name)
        is_known = std_name != raw_name.strip(" :-.") or any(
            k in raw_name.lower() for k in ["hemoglobin", "wbc", "platelet", "rbc", "glucose", "sugar", "cholesterol", "tsh", "creatinine", "sgpt", "sgot", "bilirubin", "urea", "hba1c", "ldl", "hdl", "triglyceride", "sodium", "potassium"]
        )
        if not is_known and not (unit and ref_range):
            continue

        # Handle "lakh/uL" multi-word units if present in line
        if "lakh" in line_clean.lower() and (not unit or "lakh" not in unit.lower()):
            unit_match = re.search(r"(lakh\s*/\s*[µu]?L)", line_clean, re.IGNORECASE)
            if unit_match:
                unit = unit_match.group(1)

        if ref_range and "lakh" in line_clean.lower() and "lakh" not in ref_range.lower():
            ref_range = f"{ref_range} lakh/µL"

        status_rel, is_uncertain = _compare_with_range(val_str, ref_range)
        if std_name in seen_tests:
            continue
        seen_tests.add(std_name)

        findings.append(
            {
                "test_name": std_name,
                "observed_value": f"{val_str} {unit}".strip() if unit else val_str,
                "numeric_value": val_str,
                "unit": unit,
                "reference_range": ref_range,
                "status_relative_to_range": status_rel,
                "is_uncertain": is_uncertain,
                "original_extracted_value": line_clean,
            }
        )

    return findings


def extract_text_from_pdf(file_path: Path) -> Tuple[str, str]:
    """Extract text from PDF using pdfplumber with pypdf fallback."""
    texts: List[str] = []
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    texts.append(txt)
    except Exception:
        pass

    if not texts:
        try:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    texts.append(txt)
        except Exception as exc:
            return "", f"PDF text extraction encountered an error: {exc}"

    combined = "\n".join(texts).strip()
    if combined:
        return combined, "Extracted cleanly from PDF text layer."
    return "", "No embedded text layer detected in PDF (likely scanned image PDF). Manual OCR verification or GEMINI_API_KEY Vision OCR recommended."


def extract_text_from_image(file_path: Path) -> Tuple[str, str]:
    """Extract text from JPG/PNG using pytesseract if installed, else Gemini Vision if configured, else safe fallback."""
    # Validate image readable
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            img_format = img.format
    except Exception as exc:
        return "", f"Image file could not be read: {exc}"

    # 1. Try local pytesseract if installed
    try:
        import pytesseract  # type: ignore

        text = pytesseract.image_to_string(Image.open(file_path))
        if text and text.strip():
            return text.strip(), f"Extracted via local Tesseract OCR ({img_format} {width}x{height}). Verify uncertain digits."
    except Exception:
        pass

    # 2. Try Gemini Vision if GEMINI_API_KEY is configured
    if settings.GEMINI_API_KEY:
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            img = Image.open(file_path)
            prompt = (
                "Transcribe all visible laboratory test names, observed numeric values, measurement units, "
                "dates, and supplied reference ranges from this medical report image verbatim. "
                "Do not guess or invent unreadable numbers; mark unreadable text as [UNCERTAIN]."
            )
            resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=[prompt, img])
            if resp and resp.text:
                return resp.text.strip(), f"Extracted via Gemini Vision OCR ({settings.GEMINI_MODEL}). Doctor verification required."
        except Exception as exc:
            return "", f"Gemini Vision OCR failed ({exc}). Image stored safely ({img_format} {width}x{height}); manual finding entry available."

    return (
        "",
        f"Image stored securely ({img_format} {width}x{height}). Local Tesseract OCR binary and GEMINI_API_KEY are not configured; please review the original image and enter or verify findings manually.",
    )


def process_report_file(file_path: Path, mime_type: str) -> Dict[str, Any]:
    if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        extracted_text, note = extract_text_from_pdf(file_path)
    else:
        extracted_text, note = extract_text_from_image(file_path)

    findings = extract_structured_findings(extracted_text)
    if extracted_text and not findings:
        note = f"{note} No standard structured numeric lab rows auto-parsed; manual review recommended."

    return {
        "extracted_text": extracted_text,
        "ocr_confidence_note": note,
        "findings": findings,
        "processing_status": "completed" if (extracted_text or findings) else "completed",
    }
