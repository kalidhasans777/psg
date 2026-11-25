import React, { useEffect, useState } from "react";
import {
  Activity,
  Calendar,
  ClipboardList,
  CreditCard,
  Download,
  FileText,
  History,
  LayoutDashboard,
  Mic,
  PlusCircle,
  Settings,
  Stethoscope,
  Upload,
  User,
  Bell,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { DashboardShell, NavTab } from "../components/DashboardShell";
import { PatientIdCard } from "../components/PatientIdCard";
import { TamilVoiceAssistant } from "../components/TamilVoiceAssistant";
import { VisitTimeline } from "../components/VisitTimeline";
import { AISummaryCard } from "../components/AISummaryCard";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";
import {
  AISummary,
  AppointmentRecord,
  NotificationItem,
  Patient,
  PatientHistoryResponse,
} from "../types";

export const PatientDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [profile, setProfile] = useState<Patient | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<PatientHistoryResponse | null>(null);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [deptDoctors, setDeptDoctors] = useState<{ departments: any[]; doctors: any[] }>({
    departments: [],
    doctors: [],
  });
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Profile edit state
  const [profileForm, setProfileForm] = useState({
    phone: "",
    email: "",
    address: "",
    emergency_contact: "",
    known_allergies: "",
    existing_conditions: "",
    blood_group: "",
  });

  // Symptom report state
  const [symptomForm, setSymptomForm] = useState({
    visit_id: "",
    description: "",
    duration: "",
    severity: "moderate",
    onset_date: "",
    additional_details: "",
    current_medications: "",
  });
  const [latestSymptomSummary, setLatestSymptomSummary] = useState<AISummary | null>(null);
  const [submittingSymptom, setSubmittingSymptom] = useState(false);

  // Report upload state
  const [uploadForm, setUploadForm] = useState<{
    visit_id: string;
    category: string;
    report_date: string;
    file: File | null;
  }>({
    visit_id: "",
    category: "CBC",
    report_date: new Date().toISOString().slice(0, 10),
    file: null,
  });
  const [uploadingReport, setUploadingReport] = useState(false);
  const [uploadedReportResult, setUploadedReportResult] = useState<any>(null);

  // Appointment booking state
  const [apptForm, setApptForm] = useState({
    department_id: "",
    doctor_id: "",
    scheduled_at: "",
    reason: "",
  });

  const showToast = (type: "ok" | "err", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 5000);
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const meData = await api.get<any>("/patients/me");
      setProfile(meData.patient);
      setStats(meData.stats);
      setProfileForm({
        phone: meData.patient.phone || "",
        email: meData.patient.email || "",
        address: meData.patient.address || "",
        emergency_contact: meData.patient.emergency_contact || "",
        known_allergies: meData.patient.known_allergies || "",
        existing_conditions: meData.patient.existing_conditions || "",
        blood_group: meData.patient.blood_group || "",
      });

      const [histData, apptsData, notifsData, ddData] = await Promise.all([
        api.get<PatientHistoryResponse>(`/patients/${meData.patient.permanent_patient_id}/history`),
        api.get<AppointmentRecord[]>("/appointments"),
        api.get<NotificationItem[]>("/patients/notifications/me"),
        api.get<any>("/appointments/departments-doctors"),
      ]);
      setHistory(histData);
      setAppointments(apptsData);
      setNotifications(notifsData);
      setDeptDoctors(ddData);

      if (histData.visits.length > 0) {
        const latestId = String(histData.visits[0].id);
        setSymptomForm((p) => ({ ...p, visit_id: p.visit_id || latestId }));
        setUploadForm((p) => ({ ...p, visit_id: p.visit_id || latestId }));
      }
      if (ddData.departments.length > 0 && !apptForm.department_id) {
        const firstDept = ddData.departments[0].id;
        const firstDoc = ddData.doctors.find((d: any) => d.department_id === firstDept) || ddData.doctors[0];
        setApptForm((p) => ({
          ...p,
          department_id: String(firstDept),
          doctor_id: firstDoc ? String(firstDoc.id) : "",
        }));
      }
    } catch (err: any) {
      showToast("err", err.message || "Failed to load patient dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const ensureVisitId = async (selectedId: string, chiefComplaint?: string): Promise<number> => {
    if (selectedId && selectedId !== "new") return Number(selectedId);
    const created = await api.post<any>("/visits", {
      visit_type: "outpatient",
      chief_complaint: chiefComplaint || "Patient self-reported visit",
    });
    return created.id;
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await api.put<Patient>("/patients/me", {
        ...profileForm,
        email: profileForm.email || null,
      });
      setProfile(updated);
      showToast("ok", "Profile updated and logged to audit trail.");
    } catch (err: any) {
      showToast("err", err.message || "Profile update failed");
    }
  };

  const handleSymptomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingSymptom(true);
    try {
      const vid = await ensureVisitId(symptomForm.visit_id, symptomForm.description.slice(0, 120));
      const res = await api.post<any>(`/visits/${vid}/symptoms`, {
        source_channel: "text",
        language: "en-IN",
        description: symptomForm.description,
        duration: symptomForm.duration || null,
        severity: symptomForm.severity,
        onset_date: symptomForm.onset_date || null,
        additional_details: symptomForm.additional_details || null,
        current_medications: symptomForm.current_medications || null,
        patient_confirmed: true,
      });
      setLatestSymptomSummary(res.ai_summary);
      setSymptomForm((p) => ({ ...p, description: "", duration: "", additional_details: "", current_medications: "" }));
      showToast("ok", "Symptoms saved and AI Symptom Summary generated for doctor review.");
      await loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to submit symptoms");
    } finally {
      setSubmittingSymptom(false);
    }
  };

  const handleReportUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadForm.file) {
      showToast("err", "Please select a PDF, JPG, or PNG file to upload.");
      return;
    }
    setUploadingReport(true);
    try {
      const vid = await ensureVisitId(uploadForm.visit_id, `${uploadForm.category} report upload`);
      const fd = new FormData();
      fd.append("file", uploadForm.file);
      fd.append("category", uploadForm.category);
      fd.append("report_date", uploadForm.report_date);
      fd.append("process_sync", "true");
      const rep = await api.post<any>(`/visits/${vid}/reports`, fd);
      setUploadedReportResult(rep);
      showToast("ok", "Medical report uploaded, extracted, and summarized!");
      await loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Report upload failed");
    } finally {
      setUploadingReport(false);
    }
  };

  const handleBookAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/appointments", {
        department_id: Number(apptForm.department_id),
        doctor_id: Number(apptForm.doctor_id),
        scheduled_at: new Date(apptForm.scheduled_at).toISOString(),
        reason: apptForm.reason,
      });
      setApptForm((p) => ({ ...p, reason: "", scheduled_at: "" }));
      showToast("ok", "Appointment scheduled successfully!");
      await loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to book appointment");
    }
  };

  const handleMarkNotifRead = async (id: number) => {
    await api.put(`/patients/notifications/${id}/read`, {});
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  };

  const tabs: NavTab[] = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" /> },
    { id: "profile", label: "My Profile", icon: <User className="h-4 w-4" /> },
    { id: "patient_id", label: "My Patient ID", icon: <CreditCard className="h-4 w-4" /> },
    { id: "symptoms", label: "Report Symptoms", icon: <Activity className="h-4 w-4" /> },
    { id: "voice", label: "Tamil Voice Assistant", icon: <Mic className="h-4 w-4" /> },
    { id: "reports", label: "Upload Medical Reports", icon: <Upload className="h-4 w-4" /> },
    { id: "history", label: "My Medical History", icon: <History className="h-4 w-4" /> },
    { id: "appointments", label: "Appointments", icon: <Calendar className="h-4 w-4" /> },
    { id: "consultations", label: "My Consultations", icon: <Stethoscope className="h-4 w-4" /> },
    { id: "notifications", label: "Notifications", icon: <Bell className="h-4 w-4" /> },
    { id: "settings", label: "Settings", icon: <Settings className="h-4 w-4" /> },
  ];

  const allReports = history?.visits.flatMap((v) => v.reports.map((r) => ({ ...r, visit_code: v.visit_code }))) || [];
  const allConsults = history?.visits.flatMap((v) =>
    v.consultations.map((c) => ({ ...c, visit_code: v.visit_code, visit_date: v.visit_date, prescriptions: v.prescriptions }))
  ) || [];

  return (
    <DashboardShell
      roleLabel="Patient Portal"
      userName={profile?.full_name || user?.full_name || "Patient"}
      subtitle={profile?.permanent_patient_id || user?.permanent_patient_id || ""}
      bannerImage="/images/patient-care.jpg"
      bannerTitle={`Welcome, ${profile?.full_name || user?.full_name || "Patient"}`}
      bannerSubtitle="Manage your Permanent Patient ID, explain symptoms in Tamil or English, upload medical reports, and review your lifelong visit history."
      tabs={tabs}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      onLogout={logout}
      notifications={notifications}
      onMarkNotificationRead={handleMarkNotifRead}
    >
      {toast && (
        <div
          className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium ${
            toast.type === "ok"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-rose-200 bg-rose-50 text-rose-800"
          }`}
        >
          {toast.type === "ok" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertCircle className="h-4 w-4 text-rose-600" />}
          {toast.text}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl bg-white p-10 text-center text-sm text-slate-500 shadow-sm">
          Loading your centralized medical records...
        </div>
      ) : (
        <>
          {activeTab === "overview" && profile && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Permanent Patient ID</p>
                  <p className="mt-2 font-mono text-xl font-extrabold text-[#0B4F6C]">{profile.permanent_patient_id}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Visits</p>
                  <p className="mt-2 text-2xl font-extrabold text-[#0B1F3A]">{stats?.total_visits ?? 0}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Uploaded Reports</p>
                  <p className="mt-2 text-2xl font-extrabold text-teal-700">{stats?.uploaded_reports ?? 0}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Last Visit Date</p>
                  <p className="mt-2 text-lg font-bold text-[#0B1F3A]">
                    {stats?.previous_visit_date ? new Date(stats.previous_visit_date).toLocaleDateString() : "No visits yet"}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h3 className="text-base font-bold text-[#0B1F3A]">Quick Actions</h3>
                  <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab("voice")}
                      className="flex items-center gap-3 rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-left hover:bg-teal-100/70 transition cursor-pointer"
                    >
                      <Mic className="h-6 w-6 text-teal-700" />
                      <div>
                        <p className="font-bold text-sm text-[#0B1F3A]">Speak Symptoms in Tamil</p>
                        <p className="text-xs text-slate-600">Tamil-first voice intake assistant</p>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("reports")}
                      className="flex items-center gap-3 rounded-xl border border-sky-200 bg-sky-50/70 p-4 text-left hover:bg-sky-100/70 transition cursor-pointer"
                    >
                      <Upload className="h-6 w-6 text-[#0B4F6C]" />
                      <div>
                        <p className="font-bold text-sm text-[#0B1F3A]">Upload Lab Report</p>
                        <p className="text-xs text-slate-600">PDF, JPG, PNG extraction & AI summary</p>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("history")}
                      className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left hover:bg-slate-100 transition cursor-pointer"
                    >
                      <History className="h-6 w-6 text-[#0B4F6C]" />
                      <div>
                        <p className="font-bold text-sm text-[#0B1F3A]">View Full Timeline</p>
                        <p className="text-xs text-slate-600">Access all prior year visits & reports</p>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("appointments")}
                      className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left hover:bg-slate-100 transition cursor-pointer"
                    >
                      <Calendar className="h-6 w-6 text-teal-700" />
                      <div>
                        <p className="font-bold text-sm text-[#0B1F3A]">Book Appointment</p>
                        <p className="text-xs text-slate-600">Schedule consultation with specialist</p>
                      </div>
                    </button>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h3 className="text-base font-bold text-[#0B1F3A]">Upcoming Appointment</h3>
                  {stats?.upcoming_appointment ? (
                    <div className="mt-4 rounded-xl bg-[#EFF6FF] p-4 space-y-1.5 text-sm">
                      <p className="font-mono text-xs font-bold text-[#0B4F6C]">{stats.upcoming_appointment.appointment_code}</p>
                      <p className="font-bold text-[#0B1F3A]">{stats.upcoming_appointment.doctor_name}</p>
                      <p className="text-xs text-slate-600">{stats.upcoming_appointment.department}</p>
                      <p className="text-xs font-semibold text-teal-700">
                        {new Date(stats.upcoming_appointment.scheduled_at).toLocaleString()}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">No upcoming appointments scheduled.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "profile" && profile && (
            <form onSubmit={handleProfileSave} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-lg font-bold text-[#0B1F3A]">My Profile ({profile.permanent_patient_id})</h3>
                <p className="text-xs text-slate-500">
                  Registered: {profile.registration_date} · Age: {profile.age} yrs · Gender: {profile.gender}
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Phone</label>
                  <input
                    type="text"
                    value={profileForm.phone}
                    onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Email</label>
                  <input
                    type="email"
                    value={profileForm.email}
                    onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700">Address</label>
                  <input
                    type="text"
                    value={profileForm.address}
                    onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Emergency Contact</label>
                  <input
                    type="text"
                    value={profileForm.emergency_contact}
                    onChange={(e) => setProfileForm({ ...profileForm, emergency_contact: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Blood Group</label>
                  <input
                    type="text"
                    value={profileForm.blood_group}
                    onChange={(e) => setProfileForm({ ...profileForm, blood_group: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Known Allergies</label>
                  <input
                    type="text"
                    value={profileForm.known_allergies}
                    onChange={(e) => setProfileForm({ ...profileForm, known_allergies: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Existing Conditions</label>
                  <input
                    type="text"
                    value={profileForm.existing_conditions}
                    onChange={(e) => setProfileForm({ ...profileForm, existing_conditions: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                type="submit"
                className="rounded-xl bg-[#0B4F6C] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] cursor-pointer"
              >
                Save Permitted Details
              </button>
            </form>
          )}

          {activeTab === "patient_id" && profile && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-bold text-[#0B1F3A]">Permanent Patient Identification Card</h3>
              <PatientIdCard
                patientName={profile.full_name}
                permanentPatientId={profile.permanent_patient_id}
                registrationDate={profile.registration_date}
                age={profile.age}
                phone={profile.phone}
                bloodGroup={profile.blood_group}
                allergies={profile.known_allergies}
              />
            </div>
          )}

          {activeTab === "symptoms" && (
            <div className="space-y-6">
              <form onSubmit={handleSymptomSubmit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-[#0B1F3A]">Report Symptoms (Text Intake)</h3>
                    <p className="text-xs text-slate-500">Prefer speaking in Tamil? Switch to the Tamil Voice Assistant anytime.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveTab("voice")}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-teal-50 px-3 py-2 text-xs font-semibold text-teal-800 hover:bg-teal-100 cursor-pointer"
                  >
                    <Mic className="h-4 w-4" /> Speak Symptoms Instead
                  </button>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Select Visit</label>
                  <select
                    value={symptomForm.visit_id}
                    onChange={(e) => setSymptomForm({ ...symptomForm, visit_id: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="new">+ Create New Visit Record Today</option>
                    {history?.visits.map((v) => (
                      <option key={v.id} value={String(v.id)}>
                        {v.visit_code} ({new Date(v.visit_date).toLocaleDateString()}) — {v.chief_complaint || v.visit_type}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Symptom Description *</label>
                  <textarea
                    required
                    rows={4}
                    value={symptomForm.description}
                    onChange={(e) => setSymptomForm({ ...symptomForm, description: e.target.value })}
                    placeholder="Describe your symptoms clearly (e.g., For the past four days, I have been experiencing fever, headache and body pain...)"
                    className="mt-1 w-full rounded-xl border border-slate-300 p-3 text-sm"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Duration</label>
                    <input
                      type="text"
                      value={symptomForm.duration}
                      onChange={(e) => setSymptomForm({ ...symptomForm, duration: e.target.value })}
                      placeholder="e.g., 4 days"
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Severity</label>
                    <select
                      value={symptomForm.severity}
                      onChange={(e) => setSymptomForm({ ...symptomForm, severity: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="mild">Mild</option>
                      <option value="moderate">Moderate</option>
                      <option value="severe">Severe</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">When Symptoms Started</label>
                    <input
                      type="text"
                      value={symptomForm.onset_date}
                      onChange={(e) => setSymptomForm({ ...symptomForm, onset_date: e.target.value })}
                      placeholder="e.g., 4 days ago"
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Additional Details</label>
                    <input
                      type="text"
                      value={symptomForm.additional_details}
                      onChange={(e) => setSymptomForm({ ...symptomForm, additional_details: e.target.value })}
                      placeholder="e.g., Very tired in evening, difficulty sleeping"
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Current Medication Information</label>
                    <input
                      type="text"
                      value={symptomForm.current_medications}
                      onChange={(e) => setSymptomForm({ ...symptomForm, current_medications: e.target.value })}
                      placeholder="e.g., No medication taken yet"
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submittingSymptom}
                  className="rounded-xl bg-[#0B4F6C] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] disabled:opacity-50 cursor-pointer"
                >
                  {submittingSymptom ? "Generating AI Summary..." : "Confirm & Submit Symptoms"}
                </button>
              </form>

              {latestSymptomSummary && <AISummaryCard summary={latestSymptomSummary} />}
            </div>
          )}

          {activeTab === "voice" && (
            <TamilVoiceAssistant
              visitId={symptomForm.visit_id && symptomForm.visit_id !== "new" ? Number(symptomForm.visit_id) : undefined}
              onConfirmed={() => loadAll()}
            />
          )}

          {activeTab === "reports" && (
            <div className="space-y-6">
              <form onSubmit={handleReportUpload} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-[#0B1F3A]">Upload Medical Reports (PDF / JPG / PNG)</h3>
                    <p className="text-xs text-slate-500">Original documents are preserved untouched; structured lab findings & AI summary are extracted.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => api.downloadBlob("/reports/sample/cbc-demo", "sample_cbc_demo_patient.pdf")}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-teal-200 bg-teal-50 px-3.5 py-2 text-xs font-semibold text-teal-800 hover:bg-teal-100 cursor-pointer"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Sample CBC PDF (For Testing)
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Visit Record</label>
                    <select
                      value={uploadForm.visit_id}
                      onChange={(e) => setUploadForm({ ...uploadForm, visit_id: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="new">+ Create New Visit Record</option>
                      {history?.visits.map((v) => (
                        <option key={v.id} value={String(v.id)}>
                          {v.visit_code} ({new Date(v.visit_date).toLocaleDateString()})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Report Category</label>
                    <select
                      value={uploadForm.category}
                      onChange={(e) => setUploadForm({ ...uploadForm, category: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="CBC">Complete Blood Count (CBC)</option>
                      <option value="Blood Sugar">Blood Sugar</option>
                      <option value="Lipid Profile">Lipid Profile</option>
                      <option value="Thyroid Function">Thyroid Function</option>
                      <option value="Liver Function">Liver Function</option>
                      <option value="Kidney Function">Kidney Function</option>
                      <option value="Urine Analysis">Urine Analysis</option>
                      <option value="Other">Other Laboratory Report</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700">Report Date</label>
                    <input
                      type="date"
                      value={uploadForm.report_date}
                      onChange={(e) => setUploadForm({ ...uploadForm, report_date: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Select Report File (PDF, JPG, PNG)</label>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => setUploadForm({ ...uploadForm, file: e.target.files?.[0] || null })}
                    className="mt-1 block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl file:border-0 file:bg-[#EFF6FF] file:px-4 file:py-2 file:text-xs file:font-bold file:text-[#0B4F6C] hover:file:bg-sky-100"
                  />
                </div>

                <button
                  type="submit"
                  disabled={uploadingReport}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#0B4F6C] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] disabled:opacity-50 cursor-pointer"
                >
                  <Upload className="h-4 w-4" />
                  {uploadingReport ? "Extracting & Summarizing..." : "Upload & Process Report"}
                </button>
              </form>

              {uploadedReportResult && (
                <div className="rounded-2xl border border-emerald-200 bg-white p-5 shadow-sm">
                  <h4 className="font-bold text-[#0B1F3A]">
                    Latest Extracted Report: {uploadedReportResult.file_name}
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">{uploadedReportResult.ocr_confidence_note}</p>
                  {uploadedReportResult.findings?.length > 0 && (
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-100 text-slate-500">
                            <th className="py-1.5 pr-3">Test</th>
                            <th className="py-1.5 pr-3">Observed</th>
                            <th className="py-1.5 pr-3">Supplied Range</th>
                            <th className="py-1.5">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {uploadedReportResult.findings.map((f: any) => (
                            <tr key={f.id} className="border-b border-slate-50">
                              <td className="py-1.5 pr-3 font-medium">{f.test_name}</td>
                              <td className="py-1.5 pr-3 font-semibold">{f.observed_value}</td>
                              <td className="py-1.5 pr-3">{f.reference_range || "N/A"}</td>
                              <td className="py-1.5 capitalize font-semibold">{f.status_relative_to_range}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A]">All Uploaded Reports ({allReports.length})</h3>
                <div className="mt-4 space-y-3">
                  {allReports.map((r) => (
                    <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
                      <div>
                        <p className="font-semibold text-sm text-slate-900">
                          {r.category} — {r.file_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          Visit: {r.visit_code} · Report Date: {r.report_date} · Processing: {r.processing_status} · Doctor Status:{" "}
                          <span className="font-semibold text-teal-700">{r.verification_status}</span>
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => api.downloadBlob(`/reports/${r.id}/download`, r.file_name)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-[#0B4F6C] hover:bg-slate-50 cursor-pointer"
                      >
                        <Download className="h-3.5 w-3.5" /> Download
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "history" && history && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                  <h3 className="text-base font-bold text-[#0B1F3A]">Chronological Medical History</h3>
                  <p className="text-xs text-slate-500">
                    All visits under Permanent ID {history.patient.permanent_patient_id} are preserved separately without overwriting.
                  </p>
                </div>
                <span className="rounded-full bg-[#EFF6FF] px-3 py-1 text-xs font-bold text-[#0B4F6C]">
                  {history.total_visits} Total Visits
                </span>
              </div>
              <VisitTimeline visits={history.visits} />
            </div>
          )}

          {activeTab === "appointments" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <form onSubmit={handleBookAppointment} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                <h3 className="text-base font-bold text-[#0B1F3A] flex items-center gap-2">
                  <PlusCircle className="h-4 w-4 text-teal-600" /> Schedule Appointment
                </h3>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Department</label>
                  <select
                    value={apptForm.department_id}
                    onChange={(e) => {
                      const dId = e.target.value;
                      const matchDoc = deptDoctors.doctors.find((d) => String(d.department_id) === dId);
                      setApptForm({ ...apptForm, department_id: dId, doctor_id: matchDoc ? String(matchDoc.id) : "" });
                    }}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  >
                    {deptDoctors.departments.map((d) => (
                      <option key={d.id} value={String(d.id)}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Doctor</label>
                  <select
                    value={apptForm.doctor_id}
                    onChange={(e) => setApptForm({ ...apptForm, doctor_id: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  >
                    {deptDoctors.doctors
                      .filter((d) => !apptForm.department_id || String(d.department_id) === apptForm.department_id)
                      .map((doc) => (
                        <option key={doc.id} value={String(doc.id)}>
                          {doc.full_name} ({doc.specialization})
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Preferred Date & Time</label>
                  <input
                    type="datetime-local"
                    required
                    value={apptForm.scheduled_at}
                    onChange={(e) => setApptForm({ ...apptForm, scheduled_at: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Reason</label>
                  <textarea
                    rows={2}
                    value={apptForm.reason}
                    onChange={(e) => setApptForm({ ...apptForm, reason: e.target.value })}
                    placeholder="Consultation reason"
                    className="mt-1 w-full rounded-xl border border-slate-300 p-2.5 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full rounded-xl bg-[#0B4F6C] py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] cursor-pointer"
                >
                  Book Appointment
                </button>
              </form>

              <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A]">My Appointments</h3>
                <div className="mt-4 space-y-3">
                  {appointments.length === 0 ? (
                    <p className="text-sm text-slate-500">No appointments yet.</p>
                  ) : (
                    appointments.map((a) => (
                      <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
                        <div>
                          <p className="font-mono text-xs font-bold text-[#0B4F6C]">{a.appointment_code}</p>
                          <p className="font-bold text-sm text-slate-900">{a.doctor_name} · {a.department_name}</p>
                          <p className="text-xs text-slate-500">{new Date(a.scheduled_at).toLocaleString()} — {a.reason || "Routine visit"}</p>
                        </div>
                        <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-bold capitalize text-teal-800">
                          {a.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "consultations" && (
            <div className="space-y-4">
              {allConsults.length === 0 ? (
                <div className="rounded-2xl bg-white p-8 text-center text-sm text-slate-500">
                  No completed doctor consultations recorded yet.
                </div>
              ) : (
                allConsults.map((c) => (
                  <div key={c.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                      <div>
                        <span className="font-mono text-xs font-bold text-[#0B4F6C]">{c.visit_code}</span>
                        <h4 className="font-bold text-slate-900">{c.doctor_name || "Attending Physician"}</h4>
                      </div>
                      <span className="text-xs text-slate-500">{new Date(c.visit_date).toLocaleDateString()}</span>
                    </div>
                    <p className="text-sm"><strong>Chief Complaints:</strong> {c.chief_complaints}</p>
                    <p className="text-sm"><strong>Clinical Assessment:</strong> {c.clinical_assessment}</p>
                    {c.diagnosis && <p className="text-sm"><strong>Diagnosis:</strong> {c.diagnosis}</p>}
                    {c.treatment_plan && <p className="text-sm"><strong>Treatment Plan:</strong> {c.treatment_plan}</p>}
                    {c.follow_up_date && <p className="text-sm text-teal-700 font-semibold">Follow-up Date: {c.follow_up_date}</p>}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
              <h3 className="text-base font-bold text-[#0B1F3A]">Notifications & Reminders</h3>
              {notifications.length === 0 ? (
                <p className="text-sm text-slate-500">No notifications.</p>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleMarkNotifRead(n.id)}
                    className={`rounded-xl border p-4 cursor-pointer ${
                      n.is_read ? "border-slate-200 bg-slate-50" : "border-teal-200 bg-teal-50/70"
                    }`}
                  >
                    <div className="flex justify-between text-xs text-slate-500">
                      <span className="font-bold text-[#0B4F6C] uppercase">{n.category}</span>
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                    <p className="mt-1 font-bold text-sm text-slate-900">{n.title}</p>
                    <p className="mt-0.5 text-sm text-slate-700">{n.message}</p>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "settings" && profile && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold text-[#0B1F3A]">Privacy, Consent & Account Settings</h3>
              <p className="text-sm text-slate-600">
                Your medical records are strictly isolated to Permanent Patient ID <strong>{profile.permanent_patient_id}</strong>. Other patients cannot access your records even if they know your Patient ID.
              </p>
              <div className="rounded-xl bg-slate-50 p-4 text-xs text-slate-700 space-y-1">
                <p><strong>Consent Status:</strong> {profile.consent_status ? "Active & Recorded" : "Pending"}</p>
                <p><strong>Account Status:</strong> {profile.account_status}</p>
                <p><strong>Record Retention:</strong> Long-term multi-year medical continuity enabled</p>
              </div>
            </div>
          )}
        </>
      )}
    </DashboardShell>
  );
};
