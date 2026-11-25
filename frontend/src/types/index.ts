export type UserRole = "patient" | "doctor" | "admin";

export interface User {
  id: number;
  email?: string | null;
  phone?: string | null;
  role: UserRole;
  full_name: string;
  is_active: boolean;
  permanent_patient_id?: string | null;
  patient_id?: number | null;
  doctor_id?: number | null;
}

export interface Patient {
  id: number;
  user_id: number;
  permanent_patient_id: string;
  full_name: string;
  date_of_birth: string;
  age: number;
  gender?: string | null;
  phone: string;
  email?: string | null;
  address: string;
  emergency_contact?: string | null;
  known_allergies?: string | null;
  existing_conditions?: string | null;
  relevant_medical_history?: string | null;
  blood_group?: string | null;
  registration_date: string;
  account_status: string;
  consent_status: boolean;
  is_synthetic_demo: boolean;
  created_at: string;
}

export interface ReportFinding {
  id: number;
  test_name: string;
  observed_value: string;
  numeric_value?: string | null;
  unit?: string | null;
  reference_range?: string | null;
  status_relative_to_range: "below" | "within" | "above" | "uncertain";
  is_uncertain: boolean;
  doctor_corrected: boolean;
  original_extracted_value?: string | null;
}

export interface MedicalReport {
  id: number;
  visit_id: number;
  patient_id?: number;
  category: string;
  file_name: string;
  mime_type: string;
  report_date: string;
  upload_date: string;
  processing_status: string;
  verification_status: string;
  ocr_confidence_note?: string | null;
  extracted_text?: string | null;
  findings: ReportFinding[];
}

export interface AISummarySource {
  source_type: string;
  source_record_id?: number | null;
  citation_note?: string | null;
}

export interface AISummary {
  id: number;
  patient_id?: number;
  visit_id?: number | null;
  permanent_patient_id?: string | null;
  patient_name?: string | null;
  summary_type: string;
  source_reference?: string | null;
  ai_generated_json: Record<string, any>;
  ai_generated_text: string;
  ai_provider: string;
  model_identifier: string;
  disclaimer: string;
  verification_status: "pending_verification" | "approved" | "edited" | "rejected";
  doctor_edited_text?: string | null;
  review_notes?: string | null;
  review_timestamp?: string | null;
  created_at: string;
  sources?: AISummarySource[];
}

export interface SymptomRecord {
  id: number;
  source_channel: string;
  language: string;
  raw_transcript?: string | null;
  edited_transcript?: string | null;
  description: string;
  duration?: string | null;
  severity?: string | null;
  additional_details?: string | null;
  current_medications?: string | null;
  patient_confirmed: boolean;
  created_at: string;
}

export interface ConsultationRecord {
  id: number;
  doctor_name?: string | null;
  chief_complaints: string;
  observations?: string | null;
  clinical_assessment: string;
  diagnosis?: string | null;
  treatment_plan?: string | null;
  follow_up_date?: string | null;
  consultation_notes?: string | null;
  created_at: string;
}

export interface PrescriptionRecord {
  id: number;
  doctor_name?: string | null;
  medications: Array<{
    medicine_name: string;
    dosage: string;
    frequency: string;
    duration: string;
    instructions?: string;
  }>;
  instructions?: string | null;
  issued_date: string;
}

export interface VisitRecord {
  id: number;
  visit_code: string;
  visit_date: string;
  visit_year: number;
  visit_type: string;
  chief_complaint?: string | null;
  status: string;
  department_name?: string | null;
  doctor_name?: string | null;
  symptoms: SymptomRecord[];
  reports: MedicalReport[];
  ai_summaries: AISummary[];
  consultations: ConsultationRecord[];
  prescriptions: PrescriptionRecord[];
}

export interface PatientHistoryResponse {
  patient: Patient;
  total_visits: number;
  visits: VisitRecord[];
  all_ai_summaries: AISummary[];
}

export interface AppointmentRecord {
  id: number;
  appointment_code: string;
  patient_id: number;
  permanent_patient_id?: string | null;
  patient_name?: string | null;
  doctor_id: number;
  doctor_name?: string | null;
  department_id: number;
  department_name?: string | null;
  scheduled_at: string;
  reason?: string | null;
  status: string;
  notes?: string | null;
  created_at: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  category: string;
  is_read: boolean;
  created_at: string;
}
