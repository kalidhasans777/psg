import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Globe,
  Mic,
  MicOff,
  Play,
  RotateCcw,
  Send,
  Volume2,
} from "lucide-react";
import { api } from "../services/api";
import { AISummary } from "../types";
import { AISummaryCard } from "./AISummaryCard";

interface Props {
  visitId?: number;
  onConfirmed?: (result: { visit_id: number; visit_code: string; ai_summary?: AISummary }) => void;
}

const TAMIL_PROMPTS = [
  "வணக்கம்! உங்களுக்கு என்ன உடல்நலப் பிரச்சனை இருக்கிறது? உங்கள் அறிகுறிகளைச் சொல்லுங்கள்.",
  "இந்த அறிகுறிகள் எத்தனை நாட்களாக இருக்கின்றன? வேறு ஏதாவது பிரச்சனை அல்லது சோர்வு இருக்கிறதா?",
  "நீங்கள் இதற்காக ஏதாவது மாத்திரை அல்லது மருந்து எடுத்துக்கொண்டீர்களா?",
  "சரி. நீங்கள் சொன்ன விவரங்களை இப்போது காட்டுகிறேன். சரியாக இருக்கிறதா என்று பார்த்து உறுதிப்படுத்துங்கள்.",
];

const ENGLISH_PROMPTS = [
  "Hello! What health problem are you experiencing today? Please describe your symptoms.",
  "How many days have you had these symptoms? Do you have any additional discomfort or fatigue?",
  "Have you taken any tablets or medications for this so far?",
  "Thank you. Please review and edit your recognized statement below before confirming.",
];

export const TamilVoiceAssistant: React.FC<Props> = ({ visitId, onConfirmed }) => {
  const [language, setLanguage] = useState<"ta-IN" | "en-IN" | "mixed">("ta-IN");
  const [step, setStep] = useState<number>(0);
  const [isListening, setIsListening] = useState(false);
  const [rawTranscript, setRawTranscript] = useState("");
  const [editableTranscript, setEditableTranscript] = useState("");
  const [duration, setDuration] = useState("");
  const [severity, setSeverity] = useState("moderate");
  const [medications, setMedications] = useState("");
  const [collectedData, setCollectedData] = useState<Record<string, any>>({});
  const [audioConsent, setAudioConsent] = useState(true);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirmedSummary, setConfirmedSummary] = useState<AISummary | null>(null);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    api.get("/voice/capabilities").then(setCapabilities).catch(() => {});
    return () => {
      stopListening();
      if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
    };
  }, []);

  const currentPrompt =
    language === "en-IN" ? ENGLISH_PROMPTS[step] : TAMIL_PROMPTS[step];

  const speakPrompt = (textToSpeak: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(textToSpeak);
    utter.lang = language === "en-IN" ? "en-IN" : "ta-IN";
    utter.rate = 0.95;
    window.speechSynthesis.speak(utter);
  };

  const stopListening = () => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // ignore
    }
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    } catch {
      // ignore
    }
    setIsListening(false);
  };

  const startListening = async () => {
    setErrorMessage("");
    setStatusMessage("");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMessage("Microphone access is not supported in this browser. Please type your symptoms manually below.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setRecordedAudioUrl(url);

        // If server cloud speech provider is configured, also send audio for server-side transcription
        if (capabilities?.active_cloud_provider && blob.size > 0) {
          try {
            const fd = new FormData();
            fd.append("audio", blob, "voice.webm");
            fd.append("language", language === "mixed" ? "ta-IN" : language);
            const res = await api.post<any>("/voice/transcribe", fd);
            if (res.success && res.transcript) {
              setRawTranscript((prev) => (prev ? `${prev} ${res.transcript}` : res.transcript));
              setEditableTranscript((prev) => (prev ? `${prev} ${res.transcript}` : res.transcript));
            }
          } catch {
            // fallback to Web Speech API transcript already captured
          }
        }
      };
      recorder.start();
    } catch {
      setErrorMessage(
        "Microphone permission denied or no microphone detected. You can type or edit your Tamil/English symptoms directly below."
      );
      return;
    }

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) {
      setIsListening(true);
      setStatusMessage(
        "Audio recording active. Live browser SpeechRecognition API is unavailable in this browser—stop recording or type your symptoms below."
      );
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = language === "en-IN" ? "en-IN" : "ta-IN";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognitionRef.current = recognition;

    let finalForTurn = "";
    recognition.onresult = (event: any) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalForTurn += (finalForTurn ? " " : "") + piece;
        } else {
          interim += piece;
        }
      }
      const combined = [rawTranscript, finalForTurn, interim].filter(Boolean).join(" ").trim();
      setEditableTranscript(combined);
    };

    recognition.onerror = (ev: any) => {
      if (ev.error === "not-allowed") {
        setErrorMessage("Microphone permission was denied. Please enable microphone access or use manual text input.");
      } else if (ev.error !== "aborted") {
        setErrorMessage(`Speech recognition notice (${ev.error}). You can edit or type your symptoms manually.`);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      if (finalForTurn) {
        setRawTranscript((prev) => [prev, finalForTurn].filter(Boolean).join(" ").trim());
      }
      setIsListening(false);
    };

    recognition.start();
    setIsListening(true);
    setStatusMessage(
      language === "ta-IN"
        ? "கேட்கிறேன்... தமிழில் இயல்பாகப் பேசுங்கள் (Listening in Tamil...)"
        : "Listening... Speak clearly into your microphone."
    );
  };

  const handleNextAssistantTurn = async () => {
    stopListening();
    try {
      const res = await api.post<any>("/voice/assistant", {
        language,
        step,
        patient_utterance: editableTranscript,
        collected_data: collectedData,
      });
      setCollectedData(res.collected_data || {});
      setStep(res.current_step);
      if (res.collected_data?.duration && !duration) {
        setDuration(res.collected_data.duration);
      }
      if (res.collected_data?.medications && !medications) {
        setMedications(res.collected_data.medications);
      }
      speakPrompt(res.assistant_prompt);
    } catch (err: any) {
      setErrorMessage(err.message || "Assistant step failed");
    }
  };

  const handleReset = () => {
    stopListening();
    setStep(0);
    setRawTranscript("");
    setEditableTranscript("");
    setDuration("");
    setMedications("");
    setCollectedData({});
    setConfirmedSummary(null);
    setErrorMessage("");
    setStatusMessage("");
  };

  const handleConfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editableTranscript.trim()) {
      setErrorMessage("Please speak or enter your symptoms before confirming.");
      return;
    }
    if (!audioConsent) {
      setErrorMessage("Please accept consent to process and save your symptom transcript.");
      return;
    }
    setSubmitting(true);
    setErrorMessage("");
    try {
      const res = await api.post<any>("/voice/confirm-transcript", {
        visit_id: visitId || null,
        language,
        raw_transcript: rawTranscript || editableTranscript,
        confirmed_transcript: editableTranscript.trim(),
        duration: duration || null,
        severity,
        current_medications: medications || null,
        audio_consent: audioConsent,
        generate_ai_summary: true,
      });
      setStatusMessage(`Saved to Visit ${res.visit_code} and summarized for doctor review.`);
      if (res.ai_summary) {
        setConfirmedSummary(res.ai_summary);
      }
      onConfirmed?.(res);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to confirm transcript");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-xl font-bold text-[#0B1F3A]">
              Tamil-First Healthcare Voice Assistant (தமிழ் குரல் உதவியாளர்)
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Speak naturally in Tamil, English, or Tamil-English mix. Review and edit your transcript before saving.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-teal-600" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as any)}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 focus:border-teal-600 focus:outline-none"
            >
              <option value="ta-IN">தமிழ் (Tamil India · ta-IN)</option>
              <option value="en-IN">English (India · en-IN)</option>
              <option value="mixed">Tamil + English Mixed</option>
            </select>
          </div>
        </div>

        {/* Guided Assistant Prompt Card */}
        <div className="mt-5 rounded-2xl bg-gradient-to-r from-[#EFF6FF] to-teal-50/70 p-4 border border-sky-100">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">
              Guided Step {step + 1} of 4
            </span>
            <button
              type="button"
              onClick={() => speakPrompt(currentPrompt)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-[#0B4F6C] shadow-sm hover:bg-sky-50 cursor-pointer"
            >
              <Volume2 className="h-3.5 w-3.5" />
              Repeat Question (Audio)
            </button>
          </div>
          <p className="mt-2 text-base font-semibold text-[#0B1F3A]">{currentPrompt}</p>
        </div>

        {/* Microphone Controls */}
        <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-6 text-center">
          <div className="relative">
            {isListening && (
              <span className="animate-pulse-ring absolute inset-0 rounded-full bg-teal-400/50" />
            )}
            <button
              type="button"
              onClick={isListening ? stopListening : startListening}
              className={`relative flex h-20 w-20 items-center justify-center rounded-full text-white shadow-lg transition cursor-pointer ${
                isListening
                  ? "bg-rose-600 hover:bg-rose-700"
                  : "bg-gradient-to-br from-[#0B4F6C] to-[#0D9488] hover:scale-105"
              }`}
              aria-label={isListening ? "Stop recording" : "Start recording"}
            >
              {isListening ? <MicOff className="h-9 w-9" /> : <Mic className="h-9 w-9" />}
            </button>
          </div>
          <p className="mt-3 text-sm font-semibold text-slate-800">
            {isListening ? "Recording Active — Click to Stop" : "Click Microphone to Speak Symptoms"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {capabilities?.note || "Live speech recognition via Browser Web Speech API (ta-IN / en-IN) with manual fallback."}
          </p>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button
              type="button"
              onClick={handleNextAssistantTurn}
              className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700 cursor-pointer"
            >
              <Play className="h-3.5 w-3.5" />
              Next Guided Question
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry / Clear
            </button>
            {recordedAudioUrl && (
              <audio controls src={recordedAudioUrl} className="h-8 max-w-xs" />
            )}
          </div>
        </div>

        {statusMessage && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-2.5 text-sm text-emerald-800">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            {statusMessage}
          </div>
        )}

        {errorMessage && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-2.5 text-sm text-amber-900">
            <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
            {errorMessage}
          </div>
        )}

        {/* Editable Transcript & Patient Confirmation Form */}
        <form onSubmit={handleConfirmSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-800">
              Recognized Transcript (Editable Tamil / English Text — Manual Typing Fallback Available)
            </label>
            <textarea
              rows={4}
              value={editableTranscript}
              onChange={(e) => setEditableTranscript(e.target.value)}
              placeholder='Example: எனக்கு மூன்று நாட்களாக காய்ச்சல் இருக்கு. தலைவலியும் உடம்பு வலியும் இருக்கு.'
              className="mt-1.5 w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700">Duration</label>
              <input
                type="text"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="e.g., 3 days"
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Patient-Reported Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none"
              >
                <option value="mild">Mild</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Current Medications</label>
              <input
                type="text"
                value={medications}
                onChange={(e) => setMedications(e.target.value)}
                placeholder="e.g., None / Paracetamol"
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none"
              />
            </div>
          </div>

          <label className="flex items-start gap-2.5 rounded-xl bg-slate-50 p-3 text-xs text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={audioConsent}
              onChange={(e) => setAudioConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600"
            />
            <span>
              I confirm this transcript accurately represents my symptoms and consent to storing the confirmed symptom text for doctor review and AI summarization (raw audio is not permanently stored).
            </span>
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl bg-[#0B4F6C] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#083b52] disabled:opacity-50 transition cursor-pointer"
          >
            <Send className="h-4 w-4" />
            {submitting ? "Saving & Summarizing..." : "Confirm & Submit Symptoms for AI Summary"}
          </button>
        </form>
      </div>

      {confirmedSummary && (
        <AISummaryCard summary={confirmedSummary} canReview={false} />
      )}
    </div>
  );
};
