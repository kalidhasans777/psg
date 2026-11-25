import React from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  CalendarCheck2,
  FileSearch,
  Fingerprint,
  History,
  Lock,
  Mic,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  CheckCircle2,
  Phone,
  Mail,
  MapPin,
} from "lucide-react";
import { MedoraLogo } from "../components/MedoraLogo";

const FEATURES = [
  {
    icon: <Fingerprint className="h-6 w-6 text-[#0B4F6C]" />,
    title: "Permanent Patient ID",
    desc: "Every patient receives one concurrency-safe permanent ID (e.g., MED-2026-00125) linked to their complete medical journey.",
  },
  {
    icon: <History className="h-6 w-6 text-teal-600" />,
    title: "Complete Medical History",
    desc: "All 2026, 2027, 2029, and future hospital visits remain preserved separately in a chronological timeline without overwriting old records.",
  },
  {
    icon: <Sparkles className="h-6 w-6 text-[#0B4F6C]" />,
    title: "Advanced AI Medical Summarizer",
    desc: "Context-aware clinical engine organizes symptoms, lab findings, consultations, and multi-year history with uncertainty flags.",
  },
  {
    icon: <Mic className="h-6 w-6 text-teal-600" />,
    title: "Tamil Voice Assistant",
    desc: "Tamil-first speech recognition (ta-IN) and Indian English (en-IN) help elderly and regional-language patients share symptoms naturally.",
  },
  {
    icon: <FileSearch className="h-6 w-6 text-[#0B4F6C]" />,
    title: "Medical Report Analysis",
    desc: "Secure PDF, JPG, and PNG uploads with automated structured parameter extraction against supplied reference intervals.",
  },
  {
    icon: <Stethoscope className="h-6 w-6 text-teal-600" />,
    title: "Doctor Dashboard",
    desc: "Search any Permanent Patient ID to view longitudinal history, compare reports, verify AI summaries, and document consultations.",
  },
  {
    icon: <Lock className="h-6 w-6 text-[#0B4F6C]" />,
    title: "Secure Medical Records",
    desc: "Role-based access control, patient ownership isolation, encrypted passwords, private report downloads, and full audit trails.",
  },
  {
    icon: <CalendarCheck2 className="h-6 w-6 text-teal-600" />,
    title: "Appointment Management",
    desc: "Unified scheduling across hospital departments with doctor assignment, check-in tracking, and follow-up notifications.",
  },
];

const WORKFLOW_STEPS = [
  { step: "Step 1", title: "Patient registers", desc: "Complete one-time registration with demographic details and privacy consent." },
  { step: "Step 2", title: "MEDORA generates a permanent Patient ID", desc: "Backend atomically assigns a lifelong unique MED-YYYY-XXXXX ID." },
  { step: "Step 3", title: "Patient explains symptoms through voice or text", desc: "Speak naturally in Tamil or English and confirm the recognized transcript." },
  { step: "Step 4", title: "Patient uploads medical reports", desc: "Upload CBC, blood sugar, lipid, thyroid, or other PDF/image lab reports." },
  { step: "Step 5", title: "AI organizes and summarizes the medical information", desc: "Structured clinical summaries link current complaints with prior history." },
  { step: "Step 6", title: "Doctor reviews the information", desc: "Doctor verifies, edits, or rejects AI outputs and makes all clinical decisions." },
  { step: "Step 7", title: "Every future visit is connected to the same Patient ID", desc: "Returning after months or years instantly retrieves the complete timeline." },
];

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
          <Link to="/">
            <MedoraLogo />
          </Link>
          <nav className="hidden items-center gap-5 lg:gap-7 text-sm font-semibold text-slate-600 lg:flex">
            <a href="#home" className="whitespace-nowrap hover:text-[#0B4F6C] transition">Home</a>
            <a href="#features" className="whitespace-nowrap hover:text-[#0B4F6C] transition">Features</a>
            <a href="#how-it-works" className="whitespace-nowrap hover:text-[#0B4F6C] transition">How It Works</a>
            <a href="#about" className="whitespace-nowrap hover:text-[#0B4F6C] transition">About</a>
            <a href="#contact" className="whitespace-nowrap hover:text-[#0B4F6C] transition">Contact</a>
          </nav>
          <div className="flex items-center gap-3 shrink-0">
            <Link
              to="/login"
              className="whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold text-[#0B4F6C] hover:bg-sky-50 transition"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="whitespace-nowrap inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#0B4F6C] to-[#0D9488] px-4 py-2 text-sm font-semibold text-white shadow-md shadow-teal-900/15 hover:opacity-95 transition"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section id="home" className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img
            src="/images/hero-doctor-patient.jpg"
            alt="Doctor consulting with patient in modern hospital"
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0B1F3A]/92 via-[#0B4F6C]/85 to-[#0D9488]/65" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:py-32">
          <div className="max-w-2xl text-white">
            <span className="inline-flex items-center gap-2 rounded-full border border-teal-300/30 bg-white/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-teal-100 backdrop-blur">
              <Activity className="h-3.5 w-3.5 text-emerald-300" />
              One Patient. One Permanent ID. A Complete Medical Journey.
            </span>

            <h1 className="mt-5 font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-5xl">
              Your Complete Medical Journey, Connected Through One ID.
            </h1>

            <p className="mt-5 text-base leading-relaxed text-sky-100 sm:text-lg">
              MEDORA brings your medical history, health reports and consultations together in one secure platform. Explain your symptoms in your own language and help doctors understand your health information faster with AI-powered medical summarization.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to="/register"
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-bold text-[#0B1F3A] shadow-lg hover:bg-emerald-400 transition"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="#features"
                className="inline-flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-6 py-3.5 text-sm font-bold text-white backdrop-blur hover:bg-white/20 transition"
              >
                Explore Features
              </a>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 rounded-xl border border-teal-200/40 bg-[#0B1F3A]/60 px-5 py-3.5 text-sm font-semibold text-teal-100 hover:bg-[#0B1F3A]/80 transition"
              >
                Doctor / Admin / Demo Login
              </Link>
            </div>

            <div className="mt-10 grid grid-cols-3 gap-4 border-t border-white/15 pt-6 text-xs sm:text-sm">
              <div>
                <p className="font-mono text-lg font-bold text-emerald-300">MED-2026-XXXXX</p>
                <p className="text-sky-100/80">Lifelong Permanent ID</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">ta-IN / en-IN</p>
                <p className="text-sky-100/80">Tamil-First Voice Intake</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">3 Dashboards</p>
                <p className="text-sky-100/80">Patient · Doctor · Admin</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="bg-slate-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-xs font-bold uppercase tracking-widest text-teal-700">Platform Capabilities</span>
            <h2 className="mt-2 font-display text-3xl font-extrabold text-[#0B1F3A] sm:text-4xl">
              Built for Clinical Continuity, Accessibility & Safety
            </h2>
            <p className="mt-3 text-slate-600">
              Every module connects to one centralized backend and PostgreSQL database schema so no visit, lab report, or prescription is ever lost.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md hover:border-teal-200 transition"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#EFF6FF]">
                  {f.icon}
                </div>
                <h3 className="mt-4 text-lg font-bold text-[#0B1F3A]">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How MEDORA Works */}
      <section id="how-it-works" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-xs font-bold uppercase tracking-widest text-[#0B4F6C]">7-Step Clinical Journey</span>
            <h2 className="mt-2 font-display text-3xl font-extrabold text-[#0B1F3A] sm:text-4xl">
              How MEDORA Works
            </h2>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
            {WORKFLOW_STEPS.map((item, idx) => (
              <div
                key={item.step}
                className="relative rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50/70 p-5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="rounded-lg bg-[#0B4F6C] px-2.5 py-1 text-xs font-bold text-white">
                    {item.step}
                  </span>
                  <span className="font-mono text-xs font-bold text-teal-600">0{idx + 1}</span>
                </div>
                <h3 className="mt-3 text-base font-bold text-[#0B1F3A]">{item.title}</h3>
                <p className="mt-1.5 text-sm text-slate-600">{item.desc}</p>
              </div>
            ))}
            <div className="flex flex-col justify-center rounded-2xl bg-gradient-to-br from-[#0B4F6C] to-[#0D9488] p-6 text-white shadow-md">
              <ShieldCheck className="h-8 w-8 text-emerald-300" />
              <h3 className="mt-3 text-lg font-bold">Doctor-in-the-Loop Safety</h3>
              <p className="mt-1.5 text-sm text-sky-100">
                Every AI summary displays pending verification status until approved, edited, or rejected by an authorized doctor.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* About & Contact */}
      <section id="about" className="border-t border-slate-200 bg-slate-50 py-16">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 px-4 sm:px-6 lg:grid-cols-2">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-teal-700">About MEDORA</span>
            <h2 className="mt-2 font-display text-2xl font-extrabold text-[#0B1F3A] sm:text-3xl">
              Solving Fragmented Medical Records with Tamil-First AI
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              Patients visiting multiple doctors over years often carry scattered paper prescriptions and lab reports—and elderly or Tamil-speaking patients struggle with English typing portals. MEDORA unifies every consultation, symptom statement, and lab report under one permanent ID while assisting physicians with structured, source-traceable clinical summaries.
            </p>
            <ul className="mt-5 space-y-2 text-sm text-slate-700">
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /> Separate persistent visit records across years (2026 → 2027 → 2029)</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /> Strict patient ownership & RBAC privacy protection</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /> Grounded medical terminology & trusted WHO / ICMR / NHM references</li>
            </ul>
          </div>

          <div id="contact" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-bold text-[#0B1F3A]">Hospital Support & Contact</h3>
            <p className="mt-1 text-sm text-slate-600">
              Need help retrieving your Permanent Patient ID or onboarding your hospital department?
            </p>
            <div className="mt-5 space-y-3 text-sm text-slate-700">
              <div className="flex items-center gap-3">
                <Phone className="h-4 w-4 text-[#0B4F6C]" />
                <span>+91 44 2815 9000 (24/7 Patient Helpdesk)</span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-[#0B4F6C]" />
                <span>care@medora.health</span>
              </div>
              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-[#0B4F6C]" />
                <span>MEDORA Digital Health Campus, Chennai & Coimbatore, Tamil Nadu</span>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/register" className="rounded-xl bg-[#0B4F6C] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#083b52]">
                Register New Patient
              </Link>
              <Link to="/login" className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50">
                Sign In to Portal
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0B1F3A] py-12 text-slate-300">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
            <div className="md:col-span-2">
              <MedoraLogo dark />
              <p className="mt-3 max-w-md text-xs leading-relaxed text-slate-400">
                MEDORA – One Patient. One Permanent ID. A Complete Medical Journey. Built with strict clinical safety, privacy isolation, and Tamil-first accessibility.
              </p>
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-white">Navigation</h4>
              <ul className="mt-3 space-y-2 text-xs">
                <li><a href="#about" className="hover:text-white">About MEDORA</a></li>
                <li><a href="#features" className="hover:text-white">Features</a></li>
                <li><a href="#contact" className="hover:text-white">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-white">Governance</h4>
              <ul className="mt-3 space-y-2 text-xs">
                <li><a href="#about" className="hover:text-white">Privacy Policy</a></li>
                <li><a href="#about" className="hover:text-white">Terms and Conditions</a></li>
                <li><span className="text-teal-300">Medical Disclaimer: AI assists documentation only; doctors make all clinical decisions.</span></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 border-t border-white/10 pt-6 text-center text-xs text-slate-500">
            © {new Date().getFullYear()} MEDORA Healthcare Platform. Synthetic demonstration records are clearly labelled.
          </div>
        </div>
      </footer>
    </div>
  );
};
