# MEDORA — AI & Voice Architecture

## 1. AI Medical Summarization Pipeline
```
PATIENT INPUT / REPORTS
        ↓
PDF EXTRACTION / OCR + STRUCTURED PARSING
        ↓
BILINGUAL TERMINOLOGY LAYER (Tamil ↔ English + Lab Aliases)
        ↓
PATIENT-ISOLATED HISTORY RETRIEVAL
        ↓
TRUSTED KNOWLEDGE RETRIEVAL (WHO / ICMR / NHM / MoHFW / MedlinePlus)
        ↓
AI SUMMARIZATION ENGINE (Gemini API or Clearly Labelled Deterministic Fallback)
        ↓
PYDANTIC SCHEMA VALIDATION + UNCERTAINTY CHECK
        ↓
DOCTOR VERIFICATION QUEUE (Approve / Edit / Reject)
```

### Six Specialized Summary Functions
1. **Type 1 — Symptom Summary**: Chief complaints, Tamil original statement, duration, frequency, patient-reported severity, additional cues, medication info, information to verify.
2. **Type 2 — Medical Report Summary**: Exact observed values, units, supplied reference ranges, status relative to supplied range, uncertain/unreadable values.
3. **Type 3 — Previous Medical History Summary**: Chronological visits, allergies, existing conditions, historical abnormal report flags, prior prescriptions, follow-ups.
4. **Type 4 — Consultation Summary**: Faithfully organizes doctor-entered assessment, diagnosis, treatment plan, prescriptions, and follow-up without altering doctor notes.
5. **Type 5 — Complete Patient Overview**: Distinguishes current complaints vs historical records and patient-reported info vs doctor-confirmed diagnoses.
6. **Type 6 — Report Comparison Summary**: Chronological parameter comparison across dates without autonomously asserting clinical significance.

### Clinical Safety & Honesty
- Every summary carries `"AI-Generated Summary – Pending Doctor Verification"`.
- Original AI output (`ai_generated_text` / `ai_generated_json`) is preserved separately from `doctor_edited_text`.
- When `GEMINI_API_KEY` is not configured, MEDORA uses its deterministic clinical NLP extractor (`medora-deterministic-fallback`) and explicitly labels the mode in both the API response and UI.

## 2. Tamil-First Voice Architecture
- **Provider Abstraction** (`backend/app/voice/provider.py`):
  - `GoogleCloudSpeechProvider` (`GOOGLE_CLOUD_SPEECH_API_KEY`, `ta-IN` / `en-IN`)
  - `AzureSpeechProvider` (`AZURE_SPEECH_KEY` & `AZURE_SPEECH_REGION`, `ta-IN` / `en-IN`)
  - Browser Web Speech API (`SpeechRecognition` `ta-IN` / `en-IN` + `speechSynthesis` Tamil TTS) with editable transcript correction and manual typing fallback.
- Raw audio is never saved unnecessarily; explicit consent is logged upon transcript confirmation.
