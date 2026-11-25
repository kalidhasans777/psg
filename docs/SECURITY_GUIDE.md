# MEDORA — Security & Privacy Guide

## 1. Authentication & Role-Based Access Control (RBAC)
- **Password Hashing**: `bcrypt` (cost factor 12).
- **Tokens**: Signed HS256 JWT access & refresh tokens.
- **Public Registration**: Strictly creates `patient` accounts only. Doctor and Admin accounts are created only by authenticated Hospital Administrators.
- **Backend Ownership Enforcement** (`app/security/auth.py`):
  - `authorize_patient_clinical_access()` verifies that `patient` users can ONLY access records where `patient.user_id == current_user.id`.
  - Knowing another patient's Permanent Patient ID (`MED-2026-00127`) NEVER grants access—requests by Patient A (`MED-2026-00126`) for Patient B return `403 Forbidden` and write a `status="denied"` entry to `audit_logs`.
  - Hospital Administrators manage operations (`doctors`, `departments`, `appointments`, `audit_logs`, account status) and do NOT have unrestricted access to confidential clinical consultation notes or patient histories.

## 2. File & Secret Security
- Original uploaded medical reports are stored outside public static directories (`backend/uploads/<MED-ID>/`) and downloaded exclusively via authenticated & authorized `/api/reports/{report_id}/download`.
- File extension, MIME type, size limit (`15 MB`), and PDF header checks (`%PDF`) are enforced.
- All secrets (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, speech credentials) stay strictly on the backend via environment variables.
- Security response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`) and `slowapi` rate limiting are enabled.
