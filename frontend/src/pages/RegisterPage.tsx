import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, UserPlus } from "lucide-react";
import { MedoraLogo } from "../components/MedoraLogo";
import { PatientIdCard } from "../components/PatientIdCard";
import { useAuth } from "../contexts/AuthContext";

export const RegisterPage: React.FC = () => {
  const { registerPatient } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    date_of_birth: "",
    gender: "Female",
    phone: "",
    email: "",
    address: "",
    emergency_contact: "",
    blood_group: "",
    known_allergies: "",
    existing_conditions: "",
    relevant_medical_history: "",
    password: "",
    consent_accepted: false,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [registeredCard, setRegisteredCard] = useState<any>(null);

  const computedAge = useMemo(() => {
    if (!form.date_of_birth) return null;
    const dob = new Date(form.date_of_birth);
    if (isNaN(dob.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    return age >= 0 ? age : null;
  }, [form.date_of_birth]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.consent_accepted) {
      setError("You must accept the Privacy Policy and consent acknowledgement to register.");
      return;
    }
    setLoading(true);
    try {
      const res = await registerPatient({
        ...form,
        email: form.email.trim() || null,
        emergency_contact: form.emergency_contact.trim() || null,
        blood_group: form.blood_group.trim() || null,
        known_allergies: form.known_allergies.trim() || null,
        existing_conditions: form.existing_conditions.trim() || null,
        relevant_medical_history: form.relevant_medical_history.trim() || null,
      });
      setRegisteredCard(res.patient_card);
    } catch (err: any) {
      setError(err.message || "Registration failed. Please verify your details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen py-10 px-4">
      <img
        src="/images/hospital-interior.jpg"
        alt="Modern hospital background"
        className="fixed inset-0 h-full w-full object-cover"
      />
      <div className="fixed inset-0 bg-gradient-to-br from-[#0B1F3A]/90 via-[#0B4F6C]/85 to-[#0D9488]/75" />

      <div className="relative z-10 mx-auto max-w-3xl rounded-3xl bg-white p-6 sm:p-10 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <MedoraLogo />
          <Link to="/" className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0B4F6C] hover:underline">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Home
          </Link>
        </div>

        {registeredCard ? (
          <div className="mt-6 space-y-6">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <h1 className="font-display text-xl font-extrabold text-emerald-950">
                  PATIENT REGISTRATION SUCCESSFUL
                </h1>
                <p className="mt-1 text-sm text-emerald-900">
                  Your Permanent Patient ID has been generated and saved in the centralized database. Use this same ID for every future hospital visit.
                </p>
              </div>
            </div>

            <PatientIdCard
              patientName={registeredCard.patient_name}
              permanentPatientId={registeredCard.permanent_patient_id}
              registrationDate={registeredCard.registration_date}
              age={registeredCard.age}
              phone={registeredCard.phone}
            />

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => navigate("/patient")}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#0B4F6C] to-[#0D9488] px-6 py-3 text-sm font-bold text-white shadow-md hover:opacity-95 cursor-pointer"
              >
                Go to Patient Dashboard
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <div>
              <h1 className="font-display text-2xl font-extrabold text-[#0B1F3A]">
                Patient Registration & Permanent ID Generation
              </h1>
              <p className="mt-1 text-sm text-slate-600">
                Register once to receive your lifelong MEDORA Permanent Patient ID. Already registered?{" "}
                <Link to="/login" className="font-semibold text-teal-700 hover:underline">
                  Sign in here
                </Link>
              </p>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Full Name *</label>
                <input
                  type="text"
                  required
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Enter patient full name"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Date of Birth * {computedAge !== null && <span className="text-teal-700">(Age: {computedAge} yrs)</span>}
                </label>
                <input
                  type="date"
                  required
                  value={form.date_of_birth}
                  onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Gender</label>
                <select
                  value={form.gender}
                  onChange={(e) => setForm({ ...form, gender: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                  <option value="Prefer not to say">Prefer not to say</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Phone Number *</label>
                <input
                  type="tel"
                  required
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="e.g., 9876543210"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Email Address (Optional)</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="name@example.com"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Blood Group (Optional)</label>
                <input
                  type="text"
                  value={form.blood_group}
                  onChange={(e) => setForm({ ...form, blood_group: e.target.value })}
                  placeholder="e.g., O+, A+, B+"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700">Residential Address *</label>
                <input
                  type="text"
                  required
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                  placeholder="Street, City, State, PIN"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Emergency Contact (Optional)</label>
                <input
                  type="text"
                  value={form.emergency_contact}
                  onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })}
                  placeholder="Name & phone number"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Password *</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Minimum 6 characters"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Known Allergies (Optional)</label>
                <input
                  type="text"
                  value={form.known_allergies}
                  onChange={(e) => setForm({ ...form, known_allergies: e.target.value })}
                  placeholder="e.g., Penicillin, Sulfa, Dust"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Existing Medical Conditions (Optional)</label>
                <input
                  type="text"
                  value={form.existing_conditions}
                  onChange={(e) => setForm({ ...form, existing_conditions: e.target.value })}
                  placeholder="e.g., Diabetes, Hypertension"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700">Relevant Medical History (Optional)</label>
                <textarea
                  rows={2}
                  value={form.relevant_medical_history}
                  onChange={(e) => setForm({ ...form, relevant_medical_history: e.target.value })}
                  placeholder="Prior surgeries, hospitalizations, or family history"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm focus:border-teal-600 focus:outline-none"
                />
              </div>
            </div>

            <label className="flex items-start gap-2.5 rounded-xl bg-slate-50 p-3.5 text-xs text-slate-700 cursor-pointer border border-slate-200">
              <input
                type="checkbox"
                checked={form.consent_accepted}
                onChange={(e) => setForm({ ...form, consent_accepted: e.target.checked })}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600"
              />
              <span>
                I acknowledge MEDORA's Privacy Policy and consent to generating a Permanent Patient ID, securely storing my longitudinal medical records, and generating AI-assisted clinical summaries pending doctor verification.
              </span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#0B4F6C] to-[#0D9488] py-3.5 text-sm font-bold text-white shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
            >
              <UserPlus className="h-4 w-4" />
              {loading ? "Generating Permanent Patient ID..." : "Complete Registration & Generate Patient ID"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
