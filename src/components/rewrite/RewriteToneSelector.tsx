"use client";

import { REWRITE_TONE_OPTIONS } from "@/lib/rewrite/types";
import type { RewriteTone } from "@/lib/rewrite/types";

interface RewriteToneSelectorProps {
  tone: RewriteTone;
  onToneChange: (tone: RewriteTone) => void;
  customInstruction: string;
  onCustomInstructionChange: (value: string) => void;
  disabled?: boolean;
}

/** Tone presets plus an optional free-text instruction for the rewrite request. */
export default function RewriteToneSelector({
  tone,
  onToneChange,
  customInstruction,
  onCustomInstructionChange,
  disabled = false,
}: RewriteToneSelectorProps) {
  return (
    <div>
      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Tone
      </span>

      <div role="radiogroup" aria-label="Rewrite tone" className="mt-2 flex flex-wrap gap-2">
        {REWRITE_TONE_OPTIONS.map((option) => {
          const isActive = option.id === tone;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              disabled={disabled}
              title={option.description}
              onClick={() => onToneChange(option.id)}
              className={`whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50 ${
                isActive
                  ? "border-[#7C5CFF]/45 bg-[#7C5CFF] text-white"
                  : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:bg-white/[0.06] hover:text-slate-200"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <label
        htmlFor="rewrite-custom-instruction"
        className="mt-4 block text-[11px] font-semibold uppercase tracking-wider text-slate-400"
      >
        Custom instruction <span className="normal-case text-slate-600">(optional)</span>
      </label>
      <textarea
        id="rewrite-custom-instruction"
        value={customInstruction}
        onChange={(event) => onCustomInstructionChange(event.target.value)}
        disabled={disabled}
        rows={2}
        placeholder="e.g. keep it under two sentences"
        className="mt-2 w-full resize-none rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 transition-colors duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50"
      />
    </div>
  );
}