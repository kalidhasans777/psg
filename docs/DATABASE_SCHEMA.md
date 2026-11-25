# MEDORA — Database Schema

MEDORA uses a normalized relational schema built with SQLAlchemy ORM and Alembic migrations, targeting **PostgreSQL** as the centralized database (with SQLite dev fallback when no PostgreSQL instance is configured locally).

## Core Tables (18 Tables)
1. **`users`**: `id`, `email` (unique), `phone` (unique), `password_hash`, `role` (`patient|doctor|admin`), `full_name`, `is_active`, `reset_token`, `reset_token_expires`, timestamps.
2. **`patients`**: `id`, `user_id` (FK `users.id`), `permanent_patient_id` (unique, immutable `MED-YYYY-XXXXX`), `full_name`, `date_of_birth`, `gender`, `phone`, `email`, `address`, `emergency_contact`, `known_allergies`, `existing_conditions`, `relevant_medical_history`, `blood_group`, `registration_date`, `account_status`, `consent_status`, `is_synthetic_demo`, timestamps.
3. **`patient_id_sequences`**: `year` (PK), `last_value` — row-locked (`SELECT ... FOR UPDATE` on PostgreSQL) atomic sequence ensuring concurrent registrations never collide and IDs are never reused.
4. **`departments`**: `id`, `name` (unique), `code` (unique), `description`, `head_doctor_name`, `is_active`, `created_at`.
5. **`doctors`**: `id`, `user_id` (FK), `department_id` (FK), `license_number` (unique), `specialization`, `qualification`, `phone`, `is_available`, `is_active`, timestamps.
6. **`visits`**: `id`, `visit_code` (unique `VIS-YYYY-XXXXX`), `patient_id` (FK `RESTRICT`), `doctor_id` (FK), `department_id` (FK), `visit_date`, `visit_type`, `chief_complaint`, `status`, timestamps. Every visit creates a separate row; historical visits are never overwritten.
7. **`symptoms`**: `id`, `visit_id` (FK), `patient_id` (FK), `source_channel` (`text|voice_ta|voice_en|voice_mixed`), `language`, `raw_transcript`, `edited_transcript`, `symptom_list_json`, `description`, `duration`, `severity`, `onset_date`, `additional_details`, `current_medications`, `patient_confirmed`, `confirmed_at`, `created_at`.
8. **`medical_reports`**: `id`, `visit_id` (FK), `patient_id` (FK), `category`, `file_name`, `stored_path`, `mime_type`, `file_size_bytes`, `report_date`, `processing_status`, `extracted_text`, `ocr_confidence_note`, `verification_status`, `verified_by_doctor_id`, `verified_at`, `upload_date`, `created_at`.
9. **`report_findings`**: `id`, `report_id` (FK), `test_name`, `observed_value`, `numeric_value`, `unit`, `reference_range`, `status_relative_to_range` (`below|within|above|uncertain`), `is_uncertain`, `doctor_corrected`, `original_extracted_value`, `created_at`.
10. **`ai_summaries`**: `id`, `patient_id` (FK), `visit_id` (FK), `summary_type`, `source_reference`, `ai_generated_json`, `ai_generated_text`, `ai_provider`, `model_identifier`, `disclaimer`, `generation_status`, `verification_status` (`pending_verification|approved|edited|rejected`), `doctor_edited_text`, `doctor_edited_json`, `reviewing_doctor_id`, `review_notes`, `review_timestamp`, `created_at`.
11. **`medical_knowledge_documents`**: `id`, `source_name`, `document_title`, `publication_date`, `last_updated_date`, `category`, `source_url`, `version`, `retrieval_date`, `content_snippet`, `keywords_json`.
12. **`ai_summary_sources`**: `id`, `summary_id` (FK), `knowledge_doc_id` (FK), `source_type`, `source_record_id`, `citation_note`.
13. **`doctor_consultations`**: `id`, `visit_id` (FK), `patient_id` (FK), `doctor_id` (FK), `chief_complaints`, `observations`, `clinical_assessment`, `diagnosis`, `treatment_plan`, `follow_up_date`, `consultation_notes`, timestamps.
14. **`prescriptions`**: `id`, `consultation_id` (FK), `visit_id` (FK), `patient_id` (FK), `doctor_id` (FK), `medications_json`, `instructions`, `issued_date`, `created_at`.
15. **`appointments`**: `id`, `appointment_code` (unique), `patient_id` (FK), `doctor_id` (FK), `department_id` (FK), `visit_id` (FK), `scheduled_at`, `reason`, `status`, `notes`, timestamps.
16. **`audit_logs`**: `id`, `user_id`, `user_role`, `action`, `resource_type`, `resource_id`, `patient_id`, `details_json`, `ip_address`, `status`, `created_at`.
17. **`patient_consents`**: `id`, `patient_id` (FK), `consent_type`, `consented`, `consent_version`, `ip_address`, `consented_at`.
18. **`notifications`**: `id`, `user_id`, `title`, `message`, `category`, `is_read`, `related_resource_type`, `related_resource_id`, `created_at`.
