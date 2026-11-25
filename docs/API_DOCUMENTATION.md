# MEDORA — API Documentation

Base URL: `http://localhost:8000/api` (Interactive Swagger UI available at `http://localhost:8000/docs`)

## Authentication
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Registers a new patient, generates unique `MED-YYYY-XXXXX`, records consent, returns JWT |
| POST | `/auth/login` | Public | Authenticates via email or phone + password, returns access & refresh tokens |
| POST | `/auth/refresh` | Public | Exchanges refresh token for new access token |
| POST | `/auth/logout` | Authenticated | Logs user logout in `audit_logs` |
| GET | `/auth/me` | Authenticated | Returns current user & role identifiers |
| POST | `/auth/forgot-password` | Public | Generates password reset token |
| POST | `/auth/reset-password` | Public | Completes password reset |

## Patients & Longitudinal History
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/patients` | Doctor, Admin | Staff-assisted patient registration with duplicate phone+DOB guard |
| GET | `/patients/me` | Patient | Own profile, visit count, report count, upcoming appointment |
| PUT | `/patients/me` | Patient | Updates permitted demographic/contact fields (audited) |
| GET | `/patients/search?q=` | Doctor, Admin | Search by Permanent Patient ID, name, or phone (Admin receives non-clinical metadata only) |
| GET | `/patients/{patient_identifier}` | Patient (own), Doctor | Retrieves patient profile; rejects cross-patient access with `403` |
| GET | `/patients/{patient_identifier}/history` | Patient (own), Doctor | Full chronological timeline of visits, symptoms, reports, AI summaries, consultations, prescriptions |
| GET | `/patients/{patient_identifier}/visits` | Patient (own), Doctor | Lists visits for patient |
| GET | `/patients/notifications/me` | Authenticated | Lists user's in-app notifications |

## Visits & Symptoms
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/visits` | Authenticated | Creates a new separate visit under existing permanent Patient ID |
| GET | `/visits/{visit_id}` | Authorized Patient/Doctor | Fetches visit details |
| POST | `/visits/{visit_id}/symptoms` | Authorized Patient/Doctor | Logs symptom record and automatically generates Type 1 AI Symptom Summary |

## Tamil-First Voice Assistant
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/voice/capabilities` | Public | Reports configured cloud STT (Google Cloud / Azure) vs Browser Web Speech (`ta-IN`/`en-IN`) |
| POST | `/voice/transcribe` | Authenticated | Transcribes uploaded audio via configured cloud provider |
| POST | `/voice/assistant` | Authenticated | Guided 4-step Tamil/English healthcare interview state machine |
| POST | `/voice/confirm-transcript` | Patient | Saves patient-confirmed transcript (with consent) and generates AI summary |

## Medical Reports & Extraction
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/visits/{visit_id}/reports` | Authorized Patient/Doctor | Uploads PDF/JPG/PNG, stores original immutable file, extracts text & lab findings, generates Type 2 AI Report Summary |
| GET | `/reports/{report_id}` | Authorized Patient/Doctor | Retrieves report metadata, extracted text, and findings |
| GET | `/reports/{report_id}/download` | Authorized Patient/Doctor | Authenticated download of original uploaded report |
| PUT | `/reports/{report_id}/verify` | Doctor | Marks findings verified or manually corrected (preserving original extracted values) |
| GET | `/reports/sample/cbc-demo` | Public | Downloads synthetic demo CBC PDF for testing |

## Advanced AI Medical Summarizer
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/ai/summarize-symptoms` | Authorized Patient/Doctor | Type 1: Symptom Summary |
| POST | `/ai/summarize-report` | Authorized Patient/Doctor | Type 2: Medical Report Summary |
| POST | `/ai/summarize-history` | Authorized Patient/Doctor | Type 3: Longitudinal History Summary |
| POST | `/ai/summarize-consultation` | Authorized Patient/Doctor | Type 4: Consultation Summary |
| POST | `/ai/patient-overview` | Doctor, Patient | Type 5: Complete Patient Overview |
| POST | `/ai/compare-reports` | Doctor, Patient | Type 6: Chronological Report Comparison Summary |
| GET | `/ai/summaries/{summary_id}` | Authorized Patient/Doctor | Retrieves summary & source citations |
| PUT | `/ai/summaries/{summary_id}/review` | Doctor | Approve, Edit, or Reject AI summary (preserves original AI output separately) |
| GET | `/ai/knowledge-sources` | Authenticated | Lists WHO, ICMR, NHM, MoHFW, MedlinePlus reference metadata |

## Doctor, Admin & Appointments
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/doctor/dashboard` | Doctor | Today's appointments, waiting queue, pending AI verifications |
| GET | `/doctor/patients` | Doctor | Patient directory |
| GET | `/doctor/ai-summaries` | Doctor | AI summary review queue |
| POST | `/doctor/consultations` | Doctor | Records clinical consultation, optional prescription, and Type 4 summary |
| POST | `/doctor/prescriptions` | Doctor | Issues standalone prescription |
| GET | `/admin/dashboard` | Admin | Operational KPIs & AI/OCR monitor counts |
| GET/PUT | `/admin/patients`, `/admin/patients/{id}/status` | Admin | Administrative directory & status toggle |
| GET/POST/PUT | `/admin/doctors`, `/admin/doctors/{id}` | Admin | Doctor provisioning & department assignment |
| GET/POST | `/admin/departments` | Admin | Department management |
| GET | `/admin/ai-monitor`, `/admin/audit-logs` | Admin | Operational AI status & security audit trail |
| GET/POST/PUT | `/appointments` | Authenticated | Role-scoped appointment scheduling and status updates |
