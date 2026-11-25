import React, { useState } from "react";
import { Check, Copy, Printer, ShieldCheck, User as UserIcon } from "lucide-react";

interface PatientIdCardProps {
  patientName: string;
  permanentPatientId: string;
  registrationDate: string;
  age?: number;
  phone?: string;
  bloodGroup?: string | null;
  allergies?: string | null;
}

export const PatientIdCard: React.FC<PatientIdCardProps> = ({
  patientName,
  permanentPatientId,
  registrationDate,
  age,
  phone,
  bloodGroup,
  allergies,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(permanentPatientId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback ignored
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-4">
      <div className="print-only-card relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0B1F3A] via-[#0B4F6C] to-[#0D9488] p-6 text-white shadow-xl">
        <div className="absolute -right-12 -top-12 h-44 w-44 rounded-full bg-white/10 blur-xl" />
        <div className="absolute -bottom-10 left-1/3 h-36 w-36 rounded-full bg-emerald-400/15 blur-xl" />

        <div className="relative flex flex-wrap items-start justify-between gap-4 border-b border-white/15 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
              <UserIcon className="h-6 w-6 text-teal-200" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-teal-200">
                MEDORA Permanent Health Card
              </p>
              <h3 className="text-xl font-bold tracking-tight">{patientName}</h3>
            </div>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-100 border border-emerald-300/30">
            <ShieldCheck className="h-3.5 w-3.5" />
            Active Permanent ID
          </div>
        </div>

        <div className="relative mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-wider text-sky-200">Permanent Patient ID</p>
            <p className="mt-1 font-mono text-2xl font-extrabold tracking-wider text-white">
              {permanentPatientId}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-sky-200">Registration Date</p>
              <p className="font-semibold">{registrationDate}</p>
            </div>
            {age !== undefined && (
              <div>
                <p className="text-xs text-sky-200">Age / Blood Group</p>
                <p className="font-semibold">
                  {age} yrs {bloodGroup ? `· ${bloodGroup}` : ""}
                </p>
              </div>
            )}
            {phone && (
              <div>
                <p className="text-xs text-sky-200">Registered Phone</p>
                <p className="font-semibold">{phone}</p>
              </div>
            )}
            {allergies && (
              <div className="col-span-2">
                <p className="text-xs text-amber-200">Known Allergies</p>
                <p className="font-medium text-amber-100">{allergies}</p>
              </div>
            )}
          </div>
        </div>

        <p className="relative mt-5 border-t border-white/15 pt-3 text-[11px] text-sky-100/90">
          One Patient. One Permanent ID. Present this ID on every hospital visit to connect all future consultations and reports.
        </p>
      </div>

      <div className="no-print flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition cursor-pointer"
        >
          {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4 text-[#0B4F6C]" />}
          {copied ? "Copied Patient ID!" : "Copy Patient ID"}
        </button>
        <button
          type="button"
          onClick={handlePrint}
          className="inline-flex items-center gap-2 rounded-xl bg-[#0B4F6C] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#083b52] transition cursor-pointer"
        >
          <Printer className="h-4 w-4" />
          Download / Print Identification Card
        </button>
      </div>
    </div>
  );
};
