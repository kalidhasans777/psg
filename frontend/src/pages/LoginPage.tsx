import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowLeft, Eye, EyeOff, KeyRound, LogIn, ShieldCheck } from "lucide-react";
import { MedoraLogo } from "../components/MedoraLogo";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";

const DEMO_ACCOUNTS = [
  { label: "Demo Patient (MED-2026-00125)", id: "patient@medora.health", pw: "Patient@1234", role: "Patient" },
  { label: "Doctor (Dr. Kavitha)", id: "doctor@medora.health", pw: "Doctor@1234", role: "Doctor" },
  { label: "Hospital Admin", id: "admin@medora.health", pw: "Admin@1234", role: "Admin" },
  { label: "Patient A (Privacy Test)", id: "patienta@medora.health", pw: "PatientA@123", role: "Patient A" },
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Forgot password modal state
  const [forgotOpen, setForgotOpen] = useState(false);
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetMessage, setResetMessage] = useState("");

  const redirectByRole = (role: string) => {
    if (role === "doctor") navigate("/doctor");
    else if (role === "admin") navigate("/admin");
    else navigate("/patient");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(identifier, password);
      redirectByRole(user.role);
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleRequestReset = async () => {
    setResetMessage("");
    try {
      const res = await api.post<any>("/auth/forgot-password", { identifier: resetIdentifier });
      setResetMessage(
        res.demo_reset_token
          ? `Reset token generated: ${res.demo_reset_token} (auto-filled below)`
          : res.message
      );
      if (res.demo_reset_token) setResetToken(res.demo_reset_token);
    } catch (err: any) {
      setResetMessage(err.message || "Reset request failed");
    }
  };

  const handleCompleteReset = async () => {
    try {
      const res = await api.post<any>("/auth/reset-password", {
        token: resetToken,
        new_password: newPassword,
      });
      setResetMessage(res.message);
    } catch (err: any) {
      setResetMessage(err.message || "Failed to reset password");
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4">
      <img
        src="/images/hospital-interior.jpg"
        alt="Modern hospital interior"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[#0B1F3A]/90 via-[#0B4F6C]/80 to-[#0D9488]/75" />

      <div className="relative z-10 w-full max-w-4xl grid grid-cols-1 overflow-hidden rounded-3xl bg-white shadow-2xl md:grid-cols-5">
        {/* Left Info Panel */}
        <div className="bg-gradient-to-br from-[#0B1F3A] via-[#0B4F6C] to-[#0D9488] p-7 text-white md:col-span-2 flex flex-col justify-between">
          <div>
            <Link to="/" className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-200 hover:text-white">
              <ArrowLeft className="h-3.5 w-3.5" /> Back to Home
            </Link>
            <div className="mt-5">
              <MedoraLogo dark />
            </div>
            <p className="mt-4 text-sm text-sky-100 leading-relaxed">
              Sign in with your registered email or phone number to access your Patient, Doctor, or Hospital Administration dashboard.
            </p>
          </div>

          <div className="mt-6 rounded-2xl bg-white/10 p-4 backdrop-blur border border-white/15">
            <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-200">
              <ShieldCheck className="h-4 w-4" />
              Synthetic Demo Quick-Fill
            </p>
            <div className="mt-2.5 space-y-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.id}
                  type="button"
                  onClick={() => {
                    setIdentifier(acc.id);
                    setPassword(acc.pw);
                    setError("");
                  }}
                  className="w-full rounded-xl bg-white/10 px-3 py-2 text-left text-xs hover:bg-white/20 transition cursor-pointer"
                >
                  <span className="font-bold text-white block">{acc.label}</span>
                  <span className="text-[11px] text-sky-200">{acc.id}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="p-7 sm:p-9 md:col-span-3">
          <h1 className="font-display text-2xl font-extrabold text-[#0B1F3A]">Welcome Back</h1>
          <p className="mt-1 text-sm text-slate-600">
            Secure role-based sign in for MEDORA healthcare portals.
          </p>

          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700">
                Email or Registered Phone Number
              </label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g., patient@medora.health or 9876543210"
                className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700">Password</label>
              <div className="relative mt-1.5">
                <input
                  type={showPw ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 pr-11 text-sm focus:border-teal-600 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((p) => !p)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                  aria-label="Toggle password visibility"
                >
                  {showPw ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <button
                type="button"
                onClick={() => setForgotOpen((p) => !p)}
                className="font-semibold text-[#0B4F6C] hover:underline cursor-pointer"
              >
                Forgot password?
              </button>
              <Link to="/register" className="font-semibold text-teal-700 hover:underline">
                New patient? Register for Permanent ID
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#0B4F6C] to-[#0D9488] py-3 text-sm font-bold text-white shadow-md hover:opacity-95 disabled:opacity-50 transition cursor-pointer"
            >
              <LogIn className="h-4 w-4" />
              {loading ? "Authenticating..." : "Login to MEDORA"}
            </button>
          </form>

          {forgotOpen && (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-3">
              <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                <KeyRound className="h-3.5 w-3.5" /> Password Reset
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Email or phone"
                  value={resetIdentifier}
                  onChange={(e) => setResetIdentifier(e.target.value)}
                  className="flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                />
                <button
                  type="button"
                  onClick={handleRequestReset}
                  className="rounded-xl bg-[#0B4F6C] px-3 py-2 text-xs font-semibold text-white cursor-pointer"
                >
                  Request Token
                </button>
              </div>
              {resetToken && (
                <div className="space-y-2">
                  <input
                    type="password"
                    placeholder="New password (min 6 chars)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs"
                  />
                  <button
                    type="button"
                    onClick={handleCompleteReset}
                    className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white cursor-pointer"
                  >
                    Confirm New Password
                  </button>
                </div>
              )}
              {resetMessage && <p className="text-xs text-teal-800">{resetMessage}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
