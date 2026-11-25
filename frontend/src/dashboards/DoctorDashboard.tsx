import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  Calendar,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  History,
  LayoutDashboard,
  Pill,
  Plus,
  Search,
  Sparkles,
  Stethoscope,
  User,
  Users,
} from "lucide-react";
import { DashboardShell, NavTab } from "../components/DashboardShell";
import { VisitTimeline } from "../components/VisitTimeline";
import { AISummaryCard } from "../components/AISummaryCard";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";
import { AISummary, AppointmentRecord, NotificationItem, PatientHistoryResponse } from "../types";

export const DoctorDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [dashboard, setDashboard] = useState<any>(null);
  const [patientsList, setPatientsList] = useState<any[]>([]);
  const [aiSummaries, setAiSummaries] = useState<AISummary[]>([]);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Patient search & selected clinical workspace
  const [searchQuery, setSearchQuery] = useState("MED-2026-00125");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<PatientHistoryResponse | null>(null);
  const [generatingAI, setGeneratingAI] = useState<string | null>(null);
  const [generatedOverview, setGeneratedOverview] = useState<AISummary | null>(null);
  const [generatedComparison, setGeneratedComparison] = useState<AISummary | null>(null);
  const [generatedHistSummary, setGeneratedHistSummary] = useState<AISummary | null>(null);

  // Returning patient new visit form
  const [newVisitComplaint, setNewVisitComplaint] = useState("");
  const [newVisitType, setNewVisitType] = useState("follow_up");

  // Consultation form
  const [consultForm, setConsultForm] = useState({
    visit_id: "",
    chief_complaints: "",
    observations: "",
    clinical_assessment: "",
    diagnosis: "",
    treatment_plan: "",
    follow_up_date: "",
    consultation_notes: "",
    medicine_name: "",
    dosage: "",
    frequency: "",
    duration: "",
    prescription_instructions: "",
  });

  const showToast = (type: "ok" | "err", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 5000);
  };

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [dash, pts, sums, appts, notifs] = await Promise.all([
        api.get<any>("/doctor/dashboard"),
        api.get<any[]>("/doctor/patients"),
        api.get<AISummary[]>("/doctor/ai-summaries"),
        api.get<AppointmentRecord[]>("/appointments"),
        api.get<NotificationItem[]>("/patients/notifications/me"),
      ]);
      setDashboard(dash);
      setPatientsList(pts);
      setAiSummaries(sums);
      setAppointments(appts);
      setNotifications(notifs);
    } catch (err: any) {
      showToast("err", err.message || "Failed to load doctor workspace");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    loadPatientHistory("MED-2026-00125");
  }, []);

  const loadPatientHistory = async (identifier: string) => {
    try {
      const hist = await api.get<PatientHistoryResponse>(`/patients/${encodeURIComponent(identifier)}/history`);
      setSelectedHistory(hist);
      if (hist.visits.length > 0) {
        setConsultForm((p) => ({
          ...p,
          visit_id: String(hist.visits[0].id),
          chief_complaints: hist.visits[0].chief_complaint || p.chief_complaints,
        }));
      }
    } catch (err: any) {
      showToast("err", err.message || "Failed to retrieve patient history");
    }
  };

  const handleSearchPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const res = await api.get<any[]>(`/patients/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchResults(res);
      if (res.length === 1) {
        await loadPatientHistory(res[0].permanent_patient_id);
      }
      if (res.length === 0) {
        showToast("err", `No patient found matching "${searchQuery}"`);
      }
    } catch (err: any) {
      showToast("err", err.message || "Search failed");
    }
  };

  const handleCreateReturningVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHistory) return;
    try {
      const created = await api.post<any>("/visits", {
        patient_identifier: selectedHistory.patient.permanent_patient_id,
        visit_type: newVisitType,
        chief_complaint: newVisitComplaint || "Returning patient follow-up visit",
      });
      setNewVisitComplaint("");
      showToast("ok", `Created separate visit ${created.visit_code} under ${selectedHistory.patient.permanent_patient_id}. Prior records preserved.`);
      await loadPatientHistory(selectedHistory.patient.permanent_patient_id);
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to create visit");
    }
  };

  const handleGenerateOverview = async () => {
    if (!selectedHistory) return;
    setGeneratingAI("overview");
    try {
      const res = await api.post<AISummary>("/ai/patient-overview", {
        patient_identifier: selectedHistory.patient.permanent_patient_id,
        current_visit_id: selectedHistory.visits[0]?.id || null,
      });
      setGeneratedOverview(res);
      showToast("ok", "Complete Patient Overview generated (Pending Doctor Verification).");
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to generate patient overview");
    } finally {
      setGeneratingAI(null);
    }
  };

  const handleGenerateHistorySummary = async () => {
    if (!selectedHistory) return;
    setGeneratingAI("history");
    try {
      const res = await api.post<AISummary>("/ai/summarize-history", {
        patient_identifier: selectedHistory.patient.permanent_patient_id,
      });
      setGeneratedHistSummary(res);
      showToast("ok", "Longitudinal History Summary generated.");
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to generate history summary");
    } finally {
      setGeneratingAI(null);
    }
  };

  const handleCompareReports = async () => {
    if (!selectedHistory) return;
    setGeneratingAI("compare");
    try {
      const res = await api.post<AISummary>("/ai/compare-reports", {
        patient_identifier: selectedHistory.patient.permanent_patient_id,
      });
      setGeneratedComparison(res);
      showToast("ok", "Chronological Report Comparison Summary generated.");
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to compare reports");
    } finally {
      setGeneratingAI(null);
    }
  };

  const handleVerifyReport = async (reportId: number) => {
    try {
      await api.put(`/reports/${reportId}/verify`, { verification_status: "verified" });
      showToast("ok", `Report #${reportId} marked verified by doctor.`);
      if (selectedHistory) await loadPatientHistory(selectedHistory.patient.permanent_patient_id);
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to verify report");
    }
  };

  const handleSaveConsultation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consultForm.visit_id) {
      showToast("err", "Please select a patient and visit first.");
      return;
    }
    try {
      const meds =
        consultForm.medicine_name.trim()
          ? [
              {
                medicine_name: consultForm.medicine_name,
                dosage: consultForm.dosage || "1 tablet",
                frequency: consultForm.frequency || "Twice daily",
                duration: consultForm.duration || "5 days",
              },
            ]
          : undefined;
      await api.post("/doctor/consultations", {
        visit_id: Number(consultForm.visit_id),
        chief_complaints: consultForm.chief_complaints,
        observations: consultForm.observations || null,
        clinical_assessment: consultForm.clinical_assessment,
        diagnosis: consultForm.diagnosis || null,
        treatment_plan: consultForm.treatment_plan || null,
        follow_up_date: consultForm.follow_up_date || null,
        consultation_notes: consultForm.consultation_notes || null,
        medications: meds,
        prescription_instructions: consultForm.prescription_instructions || null,
      });
      showToast("ok", "Doctor consultation & prescription saved cleanly.");
      if (selectedHistory) await loadPatientHistory(selectedHistory.patient.permanent_patient_id);
      await loadDashboard();
    } catch (err: any) {
      showToast("err", err.message || "Failed to save consultation");
    }
  };

  const tabs: NavTab[] = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" /> },
    { id: "appointments", label: "Today's Appointments", icon: <Calendar className="h-4 w-4" /> },
    { id: "queue", label: "Patient Queue", icon: <Users className="h-4 w-4" /> },
    { id: "search", label: "Search Patient", icon: <Search className="h-4 w-4" /> },
    { id: "history", label: "Medical History", icon: <History className="h-4 w-4" /> },
    { id: "ai_summaries", label: "AI Summaries", icon: <Sparkles className="h-4 w-4" /> },
    { id: "reports", label: "Medical Reports", icon: <FileText className="h-4 w-4" /> },
    { id: "consultations", label: "Consultations", icon: <Stethoscope className="h-4 w-4" /> },
    { id: "prescriptions", label: "Prescriptions", icon: <Pill className="h-4 w-4" /> },
    { id: "followups", label: "Follow-ups", icon: <CalendarClock className="h-4 w-4" /> },
    { id: "profile", label: "Profile", icon: <User className="h-4 w-4" /> },
  ];

  const selectedReports = selectedHistory?.visits.flatMap((v) => v.reports.map((r) => ({ ...r, visit_code: v.visit_code }))) || [];
  const selectedPrescriptions = selectedHistory?.visits.flatMap((v) => v.prescriptions.map((p) => ({ ...p, visit_code: v.visit_code }))) || [];
  const selectedFollowups = selectedHistory?.visits.flatMap((v) =>
    v.consultations.filter((c) => c.follow_up_date).map((c) => ({ ...c, visit_code: v.visit_code }))
  ) || [];

  return (
    <DashboardShell
      roleLabel="Doctor Clinical Workspace"
      userName={dashboard?.doctor?.full_name || user?.full_name || "Doctor"}
      subtitle={`${dashboard?.doctor?.department || "General Medicine"} · ${dashboard?.doctor?.license_number || ""}`}
      bannerImage="/images/clinical-workspace.jpg"
      bannerTitle={`Clinical Workspace — ${dashboard?.doctor?.full_name || user?.full_name || "Doctor"}`}
      bannerSubtitle="Retrieve longitudinal patient records via Permanent Patient ID, verify AI-generated clinical summaries, review lab reports, and document consultations."
      tabs={tabs}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      onLogout={logout}
      notifications={notifications}
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

      {/* Active Selected Patient Ribbon */}
      {selectedHistory && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-200 bg-gradient-to-r from-[#EFF6FF] to-teal-50/70 px-5 py-3.5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-teal-800">Active Patient Context</span>
            <p className="font-bold text-[#0B1F3A]">
              {selectedHistory.patient.full_name} ·{" "}
              <span className="font-mono text-[#0B4F6C]">{selectedHistory.patient.permanent_patient_id}</span> ·{" "}
              {selectedHistory.patient.age} yrs · {selectedHistory.total_visits} Visits
            </p>
            {selectedHistory.patient.known_allergies && (
              <p className="text-xs font-semibold text-rose-700">
                Allergies: {selectedHistory.patient.known_allergies}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={generatingAI !== null}
              onClick={() => {
                handleGenerateOverview();
                setActiveTab("history");
              }}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[#0B4F6C] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#083b52] cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5" />
              {generatingAI === "overview" ? "Generating..." : "AI Complete Patient Overview"}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("search")}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              Switch Patient
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl bg-white p-10 text-center text-sm text-slate-500">Loading clinical workspace...</div>
      ) : (
        <>
          {activeTab === "overview" && dashboard && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Today's Appointments</p>
                  <p className="mt-2 text-2xl font-extrabold text-[#0B4F6C]">{dashboard.stats.todays_appointments}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Waiting Patients</p>
                  <p className="mt-2 text-2xl font-extrabold text-teal-700">{dashboard.stats.waiting_patients}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Completed Consultations</p>
                  <p className="mt-2 text-2xl font-extrabold text-emerald-700">{dashboard.stats.completed_consultations}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Pending AI Verification</p>
                  <p className="mt-2 text-2xl font-extrabold text-amber-600">{dashboard.stats.pending_ai_verification}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A]">Active Patient Queue</h3>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-xs uppercase text-slate-500">
                        <th className="py-2 pr-3">Patient ID</th>
                        <th className="py-2 pr-3">Name</th>
                        <th className="py-2 pr-3">Visit Code</th>
                        <th className="py-2 pr-3">Chief Complaint</th>
                        <th className="py-2 pr-3">Pending AI</th>
                        <th className="py-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.waiting_queue.map((q: any) => (
                        <tr key={q.visit_id} className="border-b border-slate-50">
                          <td className="py-2.5 pr-3 font-mono text-xs font-bold text-[#0B4F6C]">{q.permanent_patient_id}</td>
                          <td className="py-2.5 pr-3 font-medium">{q.patient_name} ({q.age}y)</td>
                          <td className="py-2.5 pr-3 font-mono text-xs">{q.visit_code}</td>
                          <td className="py-2.5 pr-3 text-slate-600 max-w-xs truncate">{q.chief_complaint || "N/A"}</td>
                          <td className="py-2.5 pr-3">
                            <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-800">
                              {q.pending_ai_count}
                            </span>
                          </td>
                          <td className="py-2.5">
                            <button
                              type="button"
                              onClick={() => {
                                loadPatientHistory(q.permanent_patient_id);
                                setActiveTab("history");
                              }}
                              className="rounded-lg bg-[#0B4F6C] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#083b52] cursor-pointer"
                            >
                              Open Chart
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === "appointments" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
              <h3 className="text-base font-bold text-[#0B1F3A]">Scheduled & Today's Appointments</h3>
              {appointments.map((a) => (
                <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
                  <div>
                    <p className="font-mono text-xs font-bold text-[#0B4F6C]">{a.appointment_code} · {a.permanent_patient_id}</p>
                    <p className="font-bold text-slate-900">{a.patient_name}</p>
                    <p className="text-xs text-slate-500">{new Date(a.scheduled_at).toLocaleString()} — {a.reason}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (a.permanent_patient_id) loadPatientHistory(a.permanent_patient_id);
                        setActiveTab("history");
                      }}
                      className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white cursor-pointer"
                    >
                      Open Patient
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "queue" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-base font-bold text-[#0B1F3A] mb-4">Authorized Patient Directory ({patientsList.length})</h3>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {patientsList.map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
                    <div>
                      <p className="font-mono text-xs font-bold text-[#0B4F6C]">{p.permanent_patient_id}</p>
                      <p className="font-bold text-slate-900">{p.full_name} ({p.age}y, {p.gender})</p>
                      <p className="text-xs text-slate-500">{p.total_visits} visits · Allergies: {p.known_allergies || "None"}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        loadPatientHistory(p.permanent_patient_id);
                        setActiveTab("history");
                      }}
                      className="rounded-xl bg-[#0B4F6C] px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
                    >
                      Open History
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "search" && (
            <div className="space-y-6">
              <form onSubmit={handleSearchPatient} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-lg font-bold text-[#0B1F3A]">Search Patient by Permanent Patient ID</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Example: Try <code className="font-mono font-bold text-[#0B4F6C]">MED-2026-00125</code> to retrieve multi-year 2026, 2027, and 2029 visits.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter MED-2026-00125, name, or phone..."
                    className="flex-1 min-w-[240px] rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                  />
                  <button
                    type="submit"
                    className="inline-flex items-center gap-2 rounded-xl bg-[#0B4F6C] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] cursor-pointer"
                  >
                    <Search className="h-4 w-4" />
                    Search Database
                  </button>
                </div>

                {searchResults.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {searchResults.map((p) => (
                      <div key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3.5">
                        <div>
                          <span className="font-mono text-xs font-bold text-[#0B4F6C]">{p.permanent_patient_id}</span>
                          <p className="font-bold text-sm text-slate-900">{p.full_name} · {p.age} yrs · {p.phone}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            loadPatientHistory(p.permanent_patient_id);
                            setActiveTab("history");
                          }}
                          className="rounded-xl bg-teal-600 px-4 py-2 text-xs font-semibold text-white cursor-pointer"
                        >
                          Retrieve Full History
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </form>

              {selectedHistory && (
                <form onSubmit={handleCreateReturningVisit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                  <h3 className="text-base font-bold text-[#0B1F3A] flex items-center gap-2">
                    <Plus className="h-4 w-4 text-teal-600" />
                    Create New Returning-Patient Visit under {selectedHistory.patient.permanent_patient_id}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Creating a new visit adds a separate chronological record without modifying or overwriting 2026/2027/2029 history.
                  </p>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <select
                      value={newVisitType}
                      onChange={(e) => setNewVisitType(e.target.value)}
                      className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="follow_up">Follow-up Visit</option>
                      <option value="outpatient">Outpatient Visit</option>
                      <option value="emergency">Emergency Triage</option>
                    </select>
                    <input
                      type="text"
                      required
                      value={newVisitComplaint}
                      onChange={(e) => setNewVisitComplaint(e.target.value)}
                      placeholder="New visit chief complaint..."
                      className="sm:col-span-2 rounded-xl border border-slate-300 px-3.5 py-2 text-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    className="rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-700 cursor-pointer"
                  >
                    Create Separate Visit Record
                  </button>
                </form>
              )}
            </div>
          )}

          {activeTab === "history" && selectedHistory && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-lg font-bold text-[#0B1F3A]">
                    Longitudinal History — {selectedHistory.patient.full_name} ({selectedHistory.patient.permanent_patient_id})
                  </h3>
                  <p className="text-xs text-slate-500">
                    Conditions: {selectedHistory.patient.existing_conditions || "None"} · Allergies: {selectedHistory.patient.known_allergies || "None"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={generatingAI !== null}
                    onClick={handleGenerateOverview}
                    className="rounded-xl bg-[#0B4F6C] px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
                  >
                    {generatingAI === "overview" ? "Summarizing..." : "Generate Patient Overview (Type 5)"}
                  </button>
                  <button
                    type="button"
                    disabled={generatingAI !== null}
                    onClick={handleGenerateHistorySummary}
                    className="rounded-xl bg-teal-600 px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
                  >
                    {generatingAI === "history" ? "Summarizing..." : "Summarize History (Type 3)"}
                  </button>
                  <button
                    type="button"
                    disabled={generatingAI !== null}
                    onClick={handleCompareReports}
                    className="rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 cursor-pointer"
                  >
                    {generatingAI === "compare" ? "Comparing..." : "Compare Reports (Type 6)"}
                  </button>
                </div>
              </div>

              {generatedOverview && (
                <AISummaryCard
                  summary={generatedOverview}
                  canReview
                  onReviewed={(u) => {
                    setGeneratedOverview(u);
                    loadDashboard();
                  }}
                />
              )}
              {generatedHistSummary && (
                <AISummaryCard
                  summary={generatedHistSummary}
                  canReview
                  onReviewed={(u) => {
                    setGeneratedHistSummary(u);
                    loadDashboard();
                  }}
                />
              )}
              {generatedComparison && (
                <AISummaryCard
                  summary={generatedComparison}
                  canReview
                  onReviewed={(u) => {
                    setGeneratedComparison(u);
                    loadDashboard();
                  }}
                />
              )}

              <VisitTimeline
                visits={selectedHistory.visits}
                canReviewAI
                onSummaryReviewed={() => {
                  loadPatientHistory(selectedHistory.patient.permanent_patient_id);
                  loadDashboard();
                }}
              />
            </div>
          )}

          {activeTab === "ai_summaries" && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-lg font-bold text-[#0B1F3A]">AI Medical Summary Verification Queue</h3>
                <p className="text-xs text-slate-500">
                  Approve, edit, or reject AI-generated summaries. Original AI outputs are preserved separately for auditability.
                </p>
              </div>
              {aiSummaries.map((s) => (
                <AISummaryCard key={s.id} summary={s} canReview onReviewed={() => loadDashboard()} />
              ))}
            </div>
          )}

          {activeTab === "reports" && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-lg font-bold text-[#0B1F3A]">
                  Uploaded Medical Reports ({selectedReports.length})
                </h3>
              </div>
              {selectedReports.map((rep) => (
                <div key={rep.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-bold text-slate-900">{rep.category} — {rep.file_name}</p>
                      <p className="text-xs text-slate-500">
                        Visit: {rep.visit_code} · Date: {rep.report_date} · Status: <strong>{rep.verification_status}</strong>
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => api.downloadBlob(`/reports/${rep.id}/download`, rep.file_name)}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-[#0B4F6C] cursor-pointer"
                      >
                        <Download className="h-3.5 w-3.5" /> Original File
                      </button>
                      {rep.verification_status !== "verified" && (
                        <button
                          type="button"
                          onClick={() => handleVerifyReport(rep.id)}
                          className="rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white cursor-pointer"
                        >
                          Verify Findings
                        </button>
                      )}
                    </div>
                  </div>
                  {rep.findings.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-100 text-slate-500">
                            <th className="py-1.5 pr-3">Parameter</th>
                            <th className="py-1.5 pr-3">Observed</th>
                            <th className="py-1.5 pr-3">Reference Range</th>
                            <th className="py-1.5">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rep.findings.map((f) => (
                            <tr key={f.id} className="border-b border-slate-50">
                              <td className="py-1.5 pr-3 font-medium">{f.test_name}</td>
                              <td className="py-1.5 pr-3 font-semibold">{f.observed_value}</td>
                              <td className="py-1.5 pr-3">{f.reference_range || "Not supplied"}</td>
                              <td className="py-1.5 capitalize font-semibold">{f.status_relative_to_range}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === "consultations" && (
            <form onSubmit={handleSaveConsultation} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold text-[#0B1F3A]">Record Clinical Consultation & Prescription</h3>
              <p className="text-xs text-slate-500">
                Doctor decisions are saved separately from AI-generated summaries.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Visit Record</label>
                <select
                  value={consultForm.visit_id}
                  onChange={(e) => setConsultForm({ ...consultForm, visit_id: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                >
                  {selectedHistory?.visits.map((v) => (
                    <option key={v.id} value={String(v.id)}>
                      {v.visit_code} ({new Date(v.visit_date).toLocaleDateString()}) — {v.chief_complaint}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Chief Complaints *</label>
                  <input
                    type="text"
                    required
                    value={consultForm.chief_complaints}
                    onChange={(e) => setConsultForm({ ...consultForm, chief_complaints: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Doctor-Entered Diagnosis</label>
                  <input
                    type="text"
                    value={consultForm.diagnosis}
                    onChange={(e) => setConsultForm({ ...consultForm, diagnosis: e.target.value })}
                    placeholder="e.g., Acute Viral Febrile Illness"
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Clinical Observations</label>
                <textarea
                  rows={2}
                  value={consultForm.observations}
                  onChange={(e) => setConsultForm({ ...consultForm, observations: e.target.value })}
                  placeholder="Vitals, physical exam findings..."
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Clinical Assessment *</label>
                <textarea
                  rows={2}
                  required
                  value={consultForm.clinical_assessment}
                  onChange={(e) => setConsultForm({ ...consultForm, clinical_assessment: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5 text-sm"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Treatment Plan</label>
                  <input
                    type="text"
                    value={consultForm.treatment_plan}
                    onChange={(e) => setConsultForm({ ...consultForm, treatment_plan: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Follow-up Date</label>
                  <input
                    type="date"
                    value={consultForm.follow_up_date}
                    onChange={(e) => setConsultForm({ ...consultForm, follow_up_date: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="rounded-xl bg-slate-50 p-4 space-y-3 border border-slate-200">
                <p className="text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">Optional Prescription Item</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                  <input
                    type="text"
                    placeholder="Medicine name"
                    value={consultForm.medicine_name}
                    onChange={(e) => setConsultForm({ ...consultForm, medicine_name: e.target.value })}
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Dosage (e.g., 500mg)"
                    value={consultForm.dosage}
                    onChange={(e) => setConsultForm({ ...consultForm, dosage: e.target.value })}
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Frequency"
                    value={consultForm.frequency}
                    onChange={(e) => setConsultForm({ ...consultForm, frequency: e.target.value })}
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Duration"
                    value={consultForm.duration}
                    onChange={(e) => setConsultForm({ ...consultForm, duration: e.target.value })}
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="rounded-xl bg-[#0B4F6C] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#083b52] cursor-pointer"
              >
                Save Consultation & Issue Prescription
              </button>
            </form>
          )}

          {activeTab === "prescriptions" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
              <h3 className="text-base font-bold text-[#0B1F3A]">Issued Prescriptions</h3>
              {selectedPrescriptions.map((rx) => (
                <div key={rx.id} className="rounded-xl border border-slate-200 p-4 text-sm">
                  <p className="font-mono text-xs font-bold text-[#0B4F6C]">{rx.visit_code} · Issued {rx.issued_date}</p>
                  <ul className="mt-2 space-y-1">
                    {rx.medications.map((m, i) => (
                      <li key={i}><strong>{m.medicine_name}</strong> — {m.dosage} · {m.frequency} · {m.duration}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {activeTab === "followups" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
              <h3 className="text-base font-bold text-[#0B1F3A]">Scheduled Clinical Follow-ups</h3>
              {selectedFollowups.length === 0 ? (
                <p className="text-sm text-slate-500">No follow-up dates recorded for active patient.</p>
              ) : (
                selectedFollowups.map((f) => (
                  <div key={f.id} className="rounded-xl border border-slate-200 p-4 text-sm">
                    <p className="font-mono text-xs font-bold text-teal-700">Follow-up: {f.follow_up_date} ({f.visit_code})</p>
                    <p className="mt-1">{f.clinical_assessment}</p>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "profile" && dashboard?.doctor && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-2 text-sm">
              <h3 className="text-lg font-bold text-[#0B1F3A]">Doctor Profile</h3>
              <p><strong>Name:</strong> {dashboard.doctor.full_name}</p>
              <p><strong>Department:</strong> {dashboard.doctor.department}</p>
              <p><strong>Specialization:</strong> {dashboard.doctor.specialization}</p>
              <p><strong>Qualification:</strong> {dashboard.doctor.qualification}</p>
              <p><strong>Medical Registration / License:</strong> {dashboard.doctor.license_number}</p>
            </div>
          )}
        </>
      )}
    </DashboardShell>
  );
};
