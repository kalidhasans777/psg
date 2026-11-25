# MEDORA – One Patient. One Permanent ID. A Complete Medical Journey.

**MEDORA** is an AI-powered centralized healthcare management, longitudinal patient medical history, Tamil-first voice intake, and clinical summarization platform built with **React + TypeScript + Tailwind CSS**, **Python + FastAPI + SQLAlchemy + Alembic**, and **PostgreSQL**.

---

## Key Features
- **Permanent Patient ID System (`MED-YYYY-XXXXX`)**: Concurrency-safe, non-reusable atomic Patient ID generation stored in the centralized database (`MED-2026-00125`).
- **Longitudinal Visit & History Storage**: Every hospital visit creates an immutable separate visit record (`2026 → 2027 → 2029 → future`), never overwriting prior consultations, symptoms, or reports.
- **Returning-Patient Retrieval**: Authorized doctors search by Permanent Patient ID to retrieve full multi-year history, compare reports chronologically, and create new visits.
- **Advanced AI Medical Summarizer (6 Specialized Types)**:
  1. Symptom Summary (bilingual Tamil ↔ English clinical structuring)
  2. Medical Report Summary (observed values, units, supplied reference ranges, status)
  3. Previous Medical History Summary
  4. Consultation Summary
  5. Complete Patient Overview (distinguishes patient-reported vs doctor-confirmed, current vs historical)
  6. Chronological Report Comparison Summary
  - Every AI summary carries `"AI-Generated Summary – Pending Doctor Verification"` and supports Doctor **Approve / Edit / Reject** while preserving original AI output.
- **Tamil-First Voice Assistant**: Supports `ta-IN`, `en-IN`, and Tamil-English mixed speech via provider abstraction (Google Cloud Speech / Azure AI Speech / Browser Web Speech API) + Tamil TTS, guided 4-step prompts, editable transcript correction, and manual typing fallback.
- **Medical Report Upload & Extraction**: Secure PDF, JPG, and PNG upload (`pdfplumber`/`pypdf` + optional Tesseract OCR / Gemini Vision) with structured lab finding parsing and doctor verification.
- **Three Role-Based Dashboards**: Patient Dashboard, Doctor Dashboard, and Hospital Administration Dashboard connected to one centralized backend and database.
- **Strict Security & Privacy Isolation**: `bcrypt` password hashing, JWT authentication, RBAC, patient ownership verification (Patient A cannot access Patient B even with Patient B's ID), private report downloads, rate limiting, and audit logs.

---

## Project Structure
```text
├── frontend/                  # React + TypeScript + Vite + Tailwind CSS
│   ├── public/images/         # Custom healthcare visuals
│   └── src/
│       ├── components/        # MedoraLogo, PatientIdCard, TamilVoiceAssistant, AISummaryCard, VisitTimeline, DashboardShell
│       ├── contexts/          # AuthContext
│       ├── dashboards/        # PatientDashboard, DoctorDashboard, AdminDashboard
│       ├── pages/             # LandingPage, LoginPage, RegisterPage
│       ├── services/          # Typed API client
│       └── types/             # TypeScript interfaces
├── backend/                   # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── ai/                # Tamil-English terminology & WHO/ICMR/NHM/MedlinePlus knowledge RAG
│   │   ├── models/            # 18 relational tables
│   │   ├── reports/           # PDF extraction, OCR, structured lab parsing
│   │   ├── routers/           # auth, patients, visits, voice, reports, ai, doctor, admin, appointments
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── security/          # bcrypt, JWT, strict RBAC & ownership checks
│   │   ├── services/          # Concurrency-safe Patient ID generator & audit logger
│   │   ├── summarization/     # 6-type AI medical summarizer (Gemini + Fallback NLP)
│   │   └── voice/             # Speech provider abstraction & Tamil-first assistant
│   ├── migrations/            # Alembic migrations config
│   ├── sample_reports/        # Synthetic CBC PDF for testing
│   └── tests/                 # Automated pytest suite
├── docs/                      # API, Schema, AI Architecture, Security, Setup guides
├── docker-compose.yml         # PostgreSQL 16 + Backend + Frontend
└── .env.example
```

---

## Quick Start

### 1. Using Docker Compose (PostgreSQL 16 + Backend + Frontend)
```bash
cp .env.example .env
docker compose up --build
```

### 2. Local Development (Backend + Frontend)
**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*(By default, if `DATABASE_URL` is not set to PostgreSQL, local dev uses `sqlite:///backend/medora_dev.db`. For PostgreSQL, set `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/medora` in `backend/.env`.)*

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Access the app at `http://localhost:5173` and Swagger API docs at `http://localhost:8000/docs`.

---

## Synthetic Demo Accounts (Clearly Labelled Demonstration Data)
| Role | Email / Phone | Password | Notes |
|---|---|---|---|
| **Demo Patient** | `patient@medora.health` / `9876543210` | `Patient@1234` | `MED-2026-00125` with 2026, 2027 & 2029 visits |
| **Patient A (Privacy Test)** | `patienta@medora.health` / `9876500001` | `PatientA@123` | `MED-2026-00126` |
| **Patient B (Privacy Test)** | `patientb@medora.health` / `9876500002` | `PatientB@123` | `MED-2026-00127` |
| **Doctor (General Medicine)** | `doctor@medora.health` / `9000000101` | `Doctor@1234` | Dr. Kavitha Sundaram |
| **Hospital Administrator** | `admin@medora.health` / `9000000001` | `Admin@1234` | Operations & Audit Governance |

---

## External Service Configuration
- **Google Gemini API (`GEMINI_API_KEY`)**: When set in `backend/.env`, AI summarization uses live Google Gemini (`gemini-2.5-flash` default) and image OCR uses Gemini Vision. When unset, MEDORA runs its clearly labelled **Deterministic Clinical NLP Fallback Mode** (`medora-deterministic-fallback`).
- **Cloud Speech Recognition (`GOOGLE_CLOUD_SPEECH_API_KEY` or `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`)**: Optional server-side STT for `ta-IN` and `en-IN`. When unset, live microphone recognition uses the browser Web Speech API (`ta-IN` / `en-IN`) with editable transcript correction and manual typing fallback.
- **Local Image OCR**: Install Tesseract OCR (`pytesseract`) or configure `GEMINI_API_KEY` for Vision OCR on JPG/PNG images; PDF text extraction works out of the box via `pdfplumber` and `pypdf`.

---

## Testing
```bash
cd backend
pytest -v
```
Tests verify Permanent Patient ID generation, concurrent registration uniqueness, multi-year returning-patient history (`2026`, `2027`, `2029`), strict Patient A vs Patient B privacy isolation (`403 Forbidden`), Tamil voice confirmation + AI summary generation, CBC PDF upload & extraction, doctor review, and admin clinical isolation.
