import React from "react";

interface Props {
  dark?: boolean;
  size?: "sm" | "md" | "lg";
}

export const MedoraLogo: React.FC<Props> = ({ dark = false, size = "md" }) => {
  const iconDim = size === "lg" ? "h-11 w-11" : size === "sm" ? "h-8 w-8" : "h-9 w-9";
  const textSize = size === "lg" ? "text-2xl" : size === "sm" ? "text-lg" : "text-xl";

  return (
    <div className="inline-flex items-center gap-2.5 select-none">
      <div
        className={`${iconDim} rounded-xl bg-gradient-to-br from-[#0B4F6C] via-[#0D9488] to-[#10B981] flex items-center justify-center shadow-md shadow-teal-900/15`}
      >
        <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4l2.5-6 4 12 2.5-6H21" />
        </svg>
      </div>
      <div className="leading-tight">
        <span className={`${textSize} font-display font-extrabold tracking-tight ${dark ? "text-white" : "text-[#0B1F3A]"}`}>
          MEDORA
        </span>
        <span className={`block text-[10px] font-medium tracking-wider uppercase ${dark ? "text-teal-200" : "text-teal-700"}`}>
          One ID · Complete Care
        </span>
      </div>
    </div>
  );
};
