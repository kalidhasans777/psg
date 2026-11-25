import React, { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Edit3,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import { AISummary } from "../types";
import { api } from "../services/api";

interface Props {
  summary: AISummary;
  canReview?: boolean;
  onReviewed?: (updated: AISummary) => void;
}

export const AISummaryCard: React.FC<Props> = ({ summary, canReview = false, onReviewed }) => {
  const [editing, setEditing] = useState(false);
  const [editedText, setEditedText] = useState(summary.doctor_edited_text || summary.ai_generated_text);
  const [reviewNotes, setReviewNotes] = useState(summary.review_notes || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const statusBadge = {
    pending_verification: "bg-amber-50 text-amber-800 border-amber-200",
    approved: "bg-emerald-50 text-emerald-800 border-emerald-200",
    edited: "bg-sky-50 text-sky-800 border-sky-200",
    rejected: "bg-rose-50 text-rose-800 border-rose-200",
  }[summary.verification_status];

  const isFallback = summary.ai_provider.includes("fallback");

  const handleReview = async (decision: "approved" | "edited" | "rejected") => {
    setSubmitting(true);
    setError("");
    try {
      const updated = await api.put<AISummary>(`/ai/summaries/${summary.id}/review`, {
        decision,
        edited_text: decision === "edited" ? editedText : undefined,
        review_notes: reviewNotes || undefined,
      });
      setEditing(false);
      onReviewed?.(updated);
    } catch (err: any) {
      setError(err.message || "Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-[#EFF6FF] px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-[#0B4F6C]">
              <Sparkles className="h-3.5 w-3.5" />
              {summary.summary_type.replace(/_/g, " ")}
            </span>
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusBadge}`}>
              {summary.verification_status === "pending_verification"
                ? "Pending Doctor Verification"
                : summary.verification_status.toUpperCase()}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              {isFallback ? "Fallback Clinical Extractor (Set GEMINI_API_KEY for live Gemini)" : `${summary.ai_provider} · ${summary.model_identifier}`}
            </span>
          </div>
          <p className="mt-1.5 text-xs text-slate-500">
            Source: {summary.source_reference || "Clinical Record"} · Generated {new Date(summary.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Mandatory Safety Disclaimer Banner */}
      <div className="mt-3 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/70 px-3 py-2 text-xs font-semibold text-amber-900">
        <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600" />
        <span>
          {summary.disclaimer} — Clinical decisions remain solely with the attending doctor.
        </span>
      </div>

      {/* Structured Sections Preview */}
      <div className="mt-4 space-y-3">
        {Object.entries(summary.ai_generated_json || {})
          .filter(([key]) => key !== "mode_note")
          .map(([key, value]) => (
            <div key={key} className="rounded-xl bg-slate-50 p-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-[#0B4F6C]">
                {key.replace(/_/g, " ")}
              </p>
              {Array.isArray(value) ? (
                value.length === 0 ? (
                  <p className="mt-1 text-sm text-slate-500">None recorded</p>
                ) : (
                  <ul className="mt-1.5 space-y-1 text-sm text-slate-700">
                    {value.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                        <span>
                          {typeof item === "object" && item !== null
                            ? Object.entries(item)
                                .filter(([, v]) => v !== null && v !== undefined && v !== "")
                                .map(([ik, iv]) => `${ik.replace(/_/g, " ")}: ${typeof iv === "object" ? JSON.stringify(iv) : iv}`)
                                .join(" · ")
                            : String(item)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )
              ) : typeof value === "object" && value !== null ? (
                <div className="mt-1.5 grid grid-cols-1 gap-1.5 sm:grid-cols-2 text-sm text-slate-700">
                  {Object.entries(value).map(([ok, ov]) => (
                    <div key={ok} className="rounded-lg bg-white px-2.5 py-1.5 border border-slate-100">
                      <span className="text-xs font-semibold text-slate-500">{ok.replace(/_/g, " ")}: </span>
                      <span className="font-medium text-slate-800">
                        {typeof ov === "object" ? JSON.stringify(ov) : String(ov ?? "Not specified")}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-800 whitespace-pre-wrap">{String(value ?? "Not specified")}</p>
              )}
            </div>
          ))}
      </div>

      {summary.doctor_edited_text && (
        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50/70 p-3.5">
          <p className="text-xs font-bold uppercase tracking-wider text-sky-900">
            Doctor-Reviewed / Edited Summary
          </p>
          <pre className="mt-1.5 whitespace-pre-wrap font-sans text-sm text-slate-800">
            {summary.doctor_edited_text}
          </pre>
          {summary.review_notes && (
            <p className="mt-2 text-xs text-sky-800">
              <strong>Review Notes:</strong> {summary.review_notes}
            </p>
          )}
        </div>
      )}

      {summary.sources && summary.sources.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <BookOpen className="h-3.5 w-3.5 text-teal-600" />
          <span className="font-semibold">Sources:</span>
          {summary.sources.map((src, i) => (
            <span key={i} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
              {src.citation_note || `${src.source_type} #${src.source_record_id}`}
            </span>
          ))}
        </div>
      )}

      {error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      {canReview && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          {editing ? (
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-700">
                Edit Doctor-Reviewed Version (Original AI output remains preserved)
              </label>
              <textarea
                rows={5}
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-teal-600 focus:outline-none"
              />
              <input
                type="text"
                placeholder="Clinical review notes (optional)"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none"
              />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleReview("edited")}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-[#0B4F6C] px-4 py-2 text-xs font-semibold text-white hover:bg-[#083b52] disabled:opacity-50 cursor-pointer"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Save Edited Version
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleReview("approved")}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 cursor-pointer"
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve Summary
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-sky-300 bg-sky-50 px-3.5 py-2 text-xs font-semibold text-sky-800 hover:bg-sky-100 cursor-pointer"
              >
                <Edit3 className="h-4 w-4" />
                Edit
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleReview("rejected")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 cursor-pointer"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
