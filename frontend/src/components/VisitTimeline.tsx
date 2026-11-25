import React, { useState } from "react";
import {
  Calendar,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Pill,
  Stethoscope,
  Activity,
} from "lucide-react";
import { VisitRecord, AISummary } from "../types";
import { api } from "../services/api";
import { AISummaryCard } from "./AISummaryCard";

interface Props {
  visits: VisitRecord[];
  canReviewAI?: boolean;
  onSummaryReviewed?: (updated: AISummary) => void;
}

export const VisitTimeline: React.FC<Props> = ({ visits, canReviewAI = false, onSummaryReviewed }) => {
  const [expandedVisitId, setExpandedVisitId] = useState<number | null>(visits[0]?.id ?? null);

  if (!visits.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        No hospital visits recorded yet under this Permanent Patient ID.
      </div>
    );
  }

  return (
    <div className="relative space-y-5 before:absolute before:left-5 before:top-4 before:bottom-4 before:w-0.5 before:bg-teal-100">
      {visits.map((visit) => {
        const isOpen = expandedVisitId === visit.id;
        return (
          <div key={visit.id} className="relative pl-12">
            <span className="absolute left-2.5 top-5 flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br from-[#0B4F6C] to-[#0D9488] text-white ring-4 ring-slate-50">
              <Calendar className="h-3 w-3" />
            </span>

            <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setExpandedVisitId(isOpen ? null : visit.id)}
                className="flex w-full flex-wrap items-center justify-between gap-3 px-5 py-4 text-left hover:bg-slate-50/70 transition cursor-pointer"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-lg bg-[#0B4F6C] px-2.5 py-0.5 font-mono text-xs font-bold text-white">
                      {visit.visit_year}
                    </span>
                    <span className="font-mono text-xs font-semibold text-teal-700">
                      {visit.visit_code}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 capitalize">
                      {visit.visit_type.replace("_", " ")}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                        visit.status === "completed"
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-sky-50 text-sky-700"
                      }`}
                    >
                      {visit.status.replace("_", " ")}
                    </span>
                  </div>
                  <h4 className="mt-1.5 text-base font-bold text-[#0B1F3A]">
                    {visit.chief_complaint || "Hospital Visit Record"}
                  </h4>
                  <p className="text-xs text-slate-500">
                    Date: {new Date(visit.visit_date).toLocaleDateString()}
                    {visit.department_name ? ` · ${visit.department_name}` : ""}
                    {visit.doctor_name ? ` · ${visit.doctor_name}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span>{visit.symptoms.length} symptoms</span>
                  <span>{visit.reports.length} reports</span>
                  <span>{visit.ai_summaries.length} AI summaries</span>
                  {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </div>
              </button>

              {isOpen && (
                <div className="space-y-5 border-t border-slate-100 bg-slate-50/50 p-5">
                  {/* Symptoms */}
                  {visit.symptoms.length > 0 && (
                    <div>
                      <h5 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                        <Activity className="h-4 w-4 text-teal-600" />
                        Patient-Reported Symptoms
                      </h5>
                      <div className="space-y-2">
                        {visit.symptoms.map((sym) => (
                          <div key={sym.id} className="rounded-xl border border-slate-200 bg-white p-3.5 text-sm">
                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                              <span className="rounded bg-teal-50 px-2 py-0.5 font-semibold text-teal-800">
                                Channel: {sym.source_channel} ({sym.language})
                              </span>
                              <span>
                                Duration: {sym.duration || "N/A"} · Severity: {sym.severity || "N/A"}
                              </span>
                            </div>
                            {sym.raw_transcript && (
                              <p className="mt-2 rounded-lg bg-slate-50 p-2 text-xs text-slate-700">
                                <strong>Original Statement:</strong> {sym.raw_transcript}
                              </p>
                            )}
                            <p className="mt-2 font-medium text-slate-800">{sym.description}</p>
                            {sym.current_medications && (
                              <p className="mt-1 text-xs text-slate-600">
                                <strong>Medications Reported:</strong> {sym.current_medications}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Medical Reports */}
                  {visit.reports.length > 0 && (
                    <div>
                      <h5 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                        <FileText className="h-4 w-4 text-teal-600" />
                        Uploaded Medical Reports & Extracted Values
                      </h5>
                      <div className="space-y-3">
                        {visit.reports.map((rep) => (
                          <div key={rep.id} className="rounded-xl border border-slate-200 bg-white p-4">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p className="font-semibold text-slate-900">
                                  {rep.category} — {rep.file_name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  Report Date: {rep.report_date} · Extraction: {rep.processing_status} · Verification:{" "}
                                  <span className="font-semibold text-teal-700">{rep.verification_status}</span>
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={() => api.downloadBlob(`/reports/${rep.id}/download`, rep.file_name)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-[#0B4F6C] hover:bg-slate-50 cursor-pointer"
                              >
                                <Download className="h-3.5 w-3.5" />
                                Download Original
                              </button>
                            </div>
                            {rep.findings.length > 0 && (
                              <div className="mt-3 overflow-x-auto">
                                <table className="w-full text-left text-xs">
                                  <thead>
                                    <tr className="border-b border-slate-100 text-slate-500">
                                      <th className="py-1.5 pr-3">Parameter</th>
                                      <th className="py-1.5 pr-3">Observed Value</th>
                                      <th className="py-1.5 pr-3">Supplied Reference Range</th>
                                      <th className="py-1.5">Status</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {rep.findings.map((f) => (
                                      <tr key={f.id} className="border-b border-slate-50">
                                        <td className="py-1.5 pr-3 font-medium text-slate-800">{f.test_name}</td>
                                        <td className="py-1.5 pr-3 font-semibold text-slate-900">{f.observed_value}</td>
                                        <td className="py-1.5 pr-3 text-slate-600">{f.reference_range || "Not supplied"}</td>
                                        <td className="py-1.5">
                                          <span
                                            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
                                              f.status_relative_to_range === "within"
                                                ? "bg-emerald-50 text-emerald-700"
                                                : f.status_relative_to_range === "uncertain"
                                                ? "bg-slate-100 text-slate-600"
                                                : "bg-amber-50 text-amber-800"
                                            }`}
                                          >
                                            {f.status_relative_to_range}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Summaries */}
                  {visit.ai_summaries.length > 0 && (
                    <div className="space-y-3">
                      <h5 className="text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                        AI Summaries for This Visit
                      </h5>
                      {visit.ai_summaries.map((sum) => (
                        <AISummaryCard
                          key={sum.id}
                          summary={sum}
                          canReview={canReviewAI}
                          onReviewed={onSummaryReviewed}
                        />
                      ))}
                    </div>
                  )}

                  {/* Consultations & Prescriptions */}
                  {visit.consultations.length > 0 && (
                    <div>
                      <h5 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                        <Stethoscope className="h-4 w-4 text-teal-600" />
                        Doctor Consultation Record (Clinical Decisions)
                      </h5>
                      {visit.consultations.map((c) => (
                        <div key={c.id} className="rounded-xl border border-teal-200 bg-white p-4 text-sm space-y-1.5">
                          <p className="text-xs font-semibold text-teal-700">{c.doctor_name || "Attending Physician"}</p>
                          <p><strong>Assessment:</strong> {c.clinical_assessment}</p>
                          {c.diagnosis && <p><strong>Doctor Diagnosis:</strong> {c.diagnosis}</p>}
                          {c.treatment_plan && <p><strong>Treatment Plan:</strong> {c.treatment_plan}</p>}
                          {c.follow_up_date && <p><strong>Follow-up Date:</strong> {c.follow_up_date}</p>}
                        </div>
                      ))}
                    </div>
                  )}

                  {visit.prescriptions.length > 0 && (
                    <div>
                      <h5 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
                        <Pill className="h-4 w-4 text-teal-600" />
                        Doctor-Approved Prescriptions
                      </h5>
                      {visit.prescriptions.map((rx) => (
                        <div key={rx.id} className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
                          <ul className="space-y-1">
                            {rx.medications.map((m, idx) => (
                              <li key={idx}>
                                <strong>{m.medicine_name}</strong> — {m.dosage} · {m.frequency} · {m.duration}
                              </li>
                            ))}
                          </ul>
                          {rx.instructions && <p className="mt-2 text-xs text-slate-600">Instructions: {rx.instructions}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
