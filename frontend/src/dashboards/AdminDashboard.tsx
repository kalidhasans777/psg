import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Building2,
  Calendar,
  CheckCircle2,
  Cpu,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Stethoscope,
  UserCog,
  Users,
} from "lucide-react";
import { DashboardShell, NavTab } from "../components/DashboardShell";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";
import { AppointmentRecord } from "../types";

export const AdminDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [dash, setDash] = useState<any>(null);
  const [patients, setPatients] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([]);
  const [aiMonitor, setAiMonitor] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Forms
  const [docForm, setDocForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "Doctor@1234",
    department_id: "",
    license_number: "",
    specialization: "",
    qualification: "MBBS, MD",
  });
  const [deptForm, setDeptForm] = useState({ name: "", code: "", description: "", head_doctor_name: "" });
  const [apptForm, setApptForm] = useState({
    patient_identifier: "MED-2026-00125",
    doctor_id: "",
    department_id: "",
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
      const [d, pts, docs, depts, appts, aim, logs] = await Promise.all([
        api.get<any>("/admin/dashboard"),
        api.get<any[]>("/admin/patients"),
        api.get<any[]>("/admin/doctors"),
        api.get<any[]>("/admin/departments"),
        api.get<AppointmentRecord[]>("/appointments"),
        api.get<any>("/admin/ai-monitor"),
        api.get<any[]>("/admin/audit-logs"),
      ]);
      setDash(d);
      setPatients(pts);
      setDoctors(docs);
      setDepartments(depts);
      setAppointments(appts);
      setAiMonitor(aim);
      setAuditLogs(logs);

      if (depts.length > 0 && !docForm.department_id) {
        setDocForm((p) => ({ ...p, department_id: String(depts[0].id) }));
        setApptForm((p) => ({ ...p, department_id: String(depts[0].id) }));
      }
      if (docs.length > 0 && !apptForm.doctor_id) {
        setApptForm((p) => ({ ...p, doctor_id: String(docs[0].id) }));
      }
    } catch (err: any) {
      showToast("err", err.message || "Failed to load admin dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleTogglePatientStatus = async (id: number, status: string) => {
    try {
      await api.put(`/admin/patients/${id}/status`, { account_status: status });
      showToast("ok", `Patient status updated to ${status}`);
      loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to update status");
    }
  };

  const handleCreateDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/doctors", {
        ...docForm,
        department_id: Number(docForm.department_id),
      });
      setDocForm((p) => ({ ...p, full_name: "", email: "", phone: "", license_number: "", specialization: "" }));
      showToast("ok", "Doctor account created & assigned to department.");
      loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to create doctor");
    }
  };

  const handleToggleDoctorAvail = async (doc: any) => {
    await api.put(`/admin/doctors/${doc.id}`, { is_available: !doc.is_available });
    loadAll();
  };

  const handleCreateDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/departments", deptForm);
      setDeptForm({ name: "", code: "", description: "", head_doctor_name: "" });
      showToast("ok", "Department created.");
      loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to create department");
    }
  };

  const handleCreateAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/appointments", {
        patient_identifier: apptForm.patient_identifier,
        doctor_id: Number(apptForm.doctor_id),
        department_id: Number(apptForm.department_id),
        scheduled_at: new Date(apptForm.scheduled_at).toISOString(),
        reason: apptForm.reason,
      });
      showToast("ok", "Appointment created and assigned.");
      loadAll();
    } catch (err: any) {
      showToast("err", err.message || "Failed to create appointment");
    }
  };

  const handleApptStatus = async (id: number, status: string) => {
    await api.put(`/appointments/${id}`, { status });
    loadAll();
  };

  const tabs: NavTab[] = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" /> },
    { id: "patients", label: "Patient Management", icon: <Users className="h-4 w-4" /> },
    { id: "doctors", label: "Doctor Management", icon: <Stethoscope className="h-4 w-4" /> },
    { id: "departments", label: "Departments", icon: <Building2 className="h-4 w-4" /> },
    { id: "appointments", label: "Appointments", icon: <Calendar className="h-4 w-4" /> },
    { id: "ai_monitor", label: "AI Processing Monitor", icon: <Cpu className="h-4 w-4" /> },
    { id: "users", label: "User Management", icon: <UserCog className="h-4 w-4" /> },
    { id: "audit", label: "Security & Audit Logs", icon: <ShieldCheck className="h-4 w-4" /> },
    { id: "analytics", label: "Reports & Analytics", icon: <BarChart3 className="h-4 w-4" /> },
    { id: "settings", label: "Settings", icon: <Settings className="h-4 w-4" /> },
  ];

  return (
    <DashboardShell
      roleLabel="Hospital Administration"
      userName={user?.full_name || "Administrator"}
      subtitle="Centralized Operations & Security Governance"
      bannerImage="/images/hospital-tech-admin.jpg"
      bannerTitle="Hospital Administration & Governance"
      bannerSubtitle="Manage doctors, departments, appointments, AI processing health, and security audit logs while preserving patient clinical privacy."
      tabs={tabs}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      onLogout={logout}
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
        <div className="rounded-2xl bg-white p-10 text-center text-sm text-slate-500">Loading administration metrics...</div>
      ) : (
        <>
          {activeTab === "overview" && dash && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Total Registered Patients</p>
                  <p className="mt-2 text-2xl font-extrabold text-[#0B4F6C]">{dash.stats.total_patients}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Total Doctors / Departments</p>
                  <p className="mt-2 text-2xl font-extrabold text-teal-700">
                    {dash.stats.total_doctors} / {dash.stats.total_departments}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase text-slate-500">Total Visits / Upcoming Appts</p>
                  <p className="mt-2 text-2xl font-extrabold text-[#0B1F3A]">
                    {dash.stats.total_visits} / {dash.stats.upcoming_appointments}
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A]">AI & OCR Processing Health</h3>
                <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4 text-center">
                  <div className="rounded-xl bg-emerald-50 p-4">
                    <p className="text-2xl font-bold text-emerald-700">{dash.ai_monitor.completed_summaries}</p>
                    <p className="text-xs text-slate-600">Completed AI Summaries</p>
                  </div>
                  <div className="rounded-xl bg-amber-50 p-4">
                    <p className="text-2xl font-bold text-amber-700">{dash.ai_monitor.pending_doctor_verification}</p>
                    <p className="text-xs text-slate-600">Pending Doctor Review</p>
                  </div>
                  <div className="rounded-xl bg-sky-50 p-4">
                    <p className="text-2xl font-bold text-[#0B4F6C]">{dash.ai_monitor.approved_summaries}</p>
                    <p className="text-xs text-slate-600">Doctor Verified</p>
                  </div>
                  <div className="rounded-xl bg-rose-50 p-4">
                    <p className="text-2xl font-bold text-rose-700">
                      {dash.ai_monitor.failed_ai_requests + dash.ai_monitor.failed_ocr_jobs}
                    </p>
                    <p className="text-xs text-slate-600">Failed AI / OCR Jobs</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "patients" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <div>
                <h3 className="text-lg font-bold text-[#0B1F3A]">Administrative Patient Directory</h3>
                <p className="text-xs text-slate-500">
                  Privacy Notice: Clinical symptoms, reports, and consultation notes are hidden from administrators.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs uppercase text-slate-500">
                      <th className="py-2 pr-3">Permanent ID</th>
                      <th className="py-2 pr-3">Name</th>
                      <th className="py-2 pr-3">Phone</th>
                      <th className="py-2 pr-3">Visits</th>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2">Control</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patients.map((p) => (
                      <tr key={p.id} className="border-b border-slate-50">
                        <td className="py-2.5 pr-3 font-mono text-xs font-bold text-[#0B4F6C]">{p.permanent_patient_id}</td>
                        <td className="py-2.5 pr-3 font-medium">
                          {p.full_name} {p.is_synthetic_demo && <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px]">DEMO</span>}
                        </td>
                        <td className="py-2.5 pr-3 text-slate-600">{p.phone}</td>
                        <td className="py-2.5 pr-3">{p.total_visits}</td>
                        <td className="py-2.5 pr-3 capitalize font-semibold">{p.account_status}</td>
                        <td className="py-2.5">
                          <select
                            value={p.account_status}
                            onChange={(e) => handleTogglePatientStatus(p.id, e.target.value)}
                            className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
                          >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                            <option value="archived">Archived</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "doctors" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <form onSubmit={handleCreateDoctor} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
                <h3 className="text-base font-bold text-[#0B1F3A]">Create Doctor Account</h3>
                <input required placeholder="Full Name (e.g., Dr. Priya)" value={docForm.full_name} onChange={(e) => setDocForm({ ...docForm, full_name: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input required type="email" placeholder="Email" value={docForm.email} onChange={(e) => setDocForm({ ...docForm, email: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input required placeholder="Phone" value={docForm.phone} onChange={(e) => setDocForm({ ...docForm, phone: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input required placeholder="License Number" value={docForm.license_number} onChange={(e) => setDocForm({ ...docForm, license_number: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input required placeholder="Specialization" value={docForm.specialization} onChange={(e) => setDocForm({ ...docForm, specialization: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <select value={docForm.department_id} onChange={(e) => setDocForm({ ...docForm, department_id: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm">
                  {departments.map((d) => <option key={d.id} value={String(d.id)}>{d.name}</option>)}
                </select>
                <button type="submit" className="w-full rounded-xl bg-[#0B4F6C] py-2.5 text-sm font-semibold text-white cursor-pointer">
                  Create Doctor Account
                </button>
              </form>

              <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
                <h3 className="text-base font-bold text-[#0B1F3A]">Doctors Directory ({doctors.length})</h3>
                {doctors.map((d) => (
                  <div key={d.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
                    <div>
                      <p className="font-bold text-slate-900">{d.full_name}</p>
                      <p className="text-xs text-slate-500">{d.department_name} · {d.specialization} · {d.license_number}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleToggleDoctorAvail(d)}
                      className={`rounded-xl px-3 py-1.5 text-xs font-semibold cursor-pointer ${
                        d.is_available ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {d.is_available ? "Available" : "Unavailable"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "departments" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <form onSubmit={handleCreateDepartment} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
                <h3 className="text-base font-bold text-[#0B1F3A]">Add Hospital Department</h3>
                <input required placeholder="Department Name" value={deptForm.name} onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input required placeholder="Code (e.g., ONCO)" value={deptForm.code} onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input placeholder="Head Doctor" value={deptForm.head_doctor_name} onChange={(e) => setDeptForm({ ...deptForm, head_doctor_name: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <textarea rows={2} placeholder="Description" value={deptForm.description} onChange={(e) => setDeptForm({ ...deptForm, description: e.target.value })} className="w-full rounded-xl border border-slate-300 p-2.5 text-sm" />
                <button type="submit" className="w-full rounded-xl bg-[#0B4F6C] py-2.5 text-sm font-semibold text-white cursor-pointer">
                  Create Department
                </button>
              </form>
              <div className="lg:col-span-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {departments.map((d) => (
                  <div key={d.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <span className="font-mono text-xs font-bold text-teal-700">{d.code}</span>
                    <h4 className="font-bold text-[#0B1F3A]">{d.name}</h4>
                    <p className="mt-1 text-xs text-slate-600">{d.description}</p>
                    <p className="mt-2 text-xs text-slate-500">Doctors: {d.doctor_count} · Head: {d.head_doctor_name || "TBD"}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "appointments" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <form onSubmit={handleCreateAppointment} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
                <h3 className="text-base font-bold text-[#0B1F3A]">Create & Assign Appointment</h3>
                <input required placeholder="Patient ID (MED-2026-00125)" value={apptForm.patient_identifier} onChange={(e) => setApptForm({ ...apptForm, patient_identifier: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <select value={apptForm.department_id} onChange={(e) => setApptForm({ ...apptForm, department_id: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm">
                  {departments.map((d) => <option key={d.id} value={String(d.id)}>{d.name}</option>)}
                </select>
                <select value={apptForm.doctor_id} onChange={(e) => setApptForm({ ...apptForm, doctor_id: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm">
                  {doctors.map((d) => <option key={d.id} value={String(d.id)}>{d.full_name}</option>)}
                </select>
                <input required type="datetime-local" value={apptForm.scheduled_at} onChange={(e) => setApptForm({ ...apptForm, scheduled_at: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <input placeholder="Reason" value={apptForm.reason} onChange={(e) => setApptForm({ ...apptForm, reason: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <button type="submit" className="w-full rounded-xl bg-[#0B4F6C] py-2.5 text-sm font-semibold text-white cursor-pointer">
                  Assign Appointment
                </button>
              </form>
              <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
                <h3 className="text-base font-bold text-[#0B1F3A]">All Appointments</h3>
                {appointments.map((a) => (
                  <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 p-3.5 text-sm">
                    <div>
                      <p className="font-mono text-xs font-bold text-[#0B4F6C]">{a.appointment_code} · {a.permanent_patient_id}</p>
                      <p className="font-semibold">{a.patient_name} → {a.doctor_name} ({a.department_name})</p>
                      <p className="text-xs text-slate-500">{new Date(a.scheduled_at).toLocaleString()}</p>
                    </div>
                    <select
                      value={a.status}
                      onChange={(e) => handleApptStatus(a.id, e.target.value)}
                      className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-semibold"
                    >
                      <option value="scheduled">Scheduled</option>
                      <option value="confirmed">Confirmed</option>
                      <option value="checked_in">Checked In</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "ai_monitor" && aiMonitor && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A] mb-3">AI Summarization Jobs (Operational Status Only)</h3>
                <div className="space-y-2 text-xs">
                  {aiMonitor.ai_jobs.map((j: any) => (
                    <div key={j.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                      <div>
                        <span className="font-bold uppercase text-[#0B4F6C]">{j.summary_type}</span> · {j.ai_provider}
                      </div>
                      <span className="rounded-full bg-white border border-slate-200 px-2.5 py-0.5 font-semibold">{j.verification_status}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-bold text-[#0B1F3A] mb-3">Report Extraction & OCR Jobs</h3>
                <div className="space-y-2 text-xs">
                  {aiMonitor.report_jobs.map((r: any) => (
                    <div key={r.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                      <span>Report #{r.id} ({r.category})</span>
                      <span className="font-semibold text-teal-700">{r.processing_status} / {r.verification_status}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "users" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold text-[#0B1F3A]">Role & Account Governance</h3>
              <p className="text-sm text-slate-600">
                Public registration only creates <strong>Patient</strong> accounts. Doctor and Hospital Administrator accounts are provisioned strictly through authorized administrative endpoints.
              </p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <p className="font-bold text-[#0B4F6C]">Patients</p>
                  <p className="text-2xl font-extrabold mt-1">{patients.length}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <p className="font-bold text-teal-700">Doctors</p>
                  <p className="text-2xl font-extrabold mt-1">{doctors.length}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <p className="font-bold text-[#0B1F3A]">Administrators</p>
                  <p className="text-2xl font-extrabold mt-1">1</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "audit" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#0B1F3A] mb-4">Security & Access Audit Logs</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 uppercase text-slate-500">
                      <th className="py-2 pr-3">Timestamp</th>
                      <th className="py-2 pr-3">Action</th>
                      <th className="py-2 pr-3">Role</th>
                      <th className="py-2 pr-3">Resource</th>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2">IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((l) => (
                      <tr key={l.id} className="border-b border-slate-50">
                        <td className="py-2 pr-3 text-slate-500">{new Date(l.created_at).toLocaleString()}</td>
                        <td className="py-2 pr-3 font-semibold text-slate-900">{l.action}</td>
                        <td className="py-2 pr-3 capitalize">{l.user_role || "system"}</td>
                        <td className="py-2 pr-3 font-mono">{l.resource_type}:{l.resource_id}</td>
                        <td className="py-2 pr-3">
                          <span
                            className={`rounded-full px-2 py-0.5 font-semibold ${
                              l.status === "success"
                                ? "bg-emerald-50 text-emerald-700"
                                : l.status === "denied"
                                ? "bg-rose-50 text-rose-700"
                                : "bg-amber-50 text-amber-800"
                            }`}
                          >
                            {l.status}
                          </span>
                        </td>
                        <td className="py-2 text-slate-500">{l.ip_address || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "analytics" && dash && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <h3 className="text-lg font-bold text-[#0B1F3A]">Hospital Operations Analytics</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-bold uppercase text-slate-500">Department Coverage</p>
                  <ul className="mt-2 space-y-1.5 text-sm">
                    {departments.map((d) => (
                      <li key={d.id} className="flex justify-between">
                        <span>{d.name}</span>
                        <span className="font-bold text-[#0B4F6C]">{d.doctor_count} doctors</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-bold uppercase text-slate-500">Security Events Summary</p>
                  <p className="mt-2 text-sm">Total Audited Events: <strong>{auditLogs.length}</strong></p>
                  <p className="mt-1 text-sm text-rose-700">
                    Access Denied Events Blocked: <strong>{auditLogs.filter((l) => l.status === "denied").length}</strong>
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "settings" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-2 text-sm">
              <h3 className="text-lg font-bold text-[#0B1F3A]">System Security & Retention Configuration</h3>
              <p><strong>Database:</strong> Centralized SQLAlchemy + PostgreSQL/Dev SQLite backend</p>
              <p><strong>AI Safety Policy:</strong> Mandatory Doctor Verification on all summaries</p>
              <p><strong>Patient ID Format:</strong> MED-YYYY-XXXXX (Atomic non-reusable sequence)</p>
            </div>
          )}
        </>
      )}
    </DashboardShell>
  );
};
