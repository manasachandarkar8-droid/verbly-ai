"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  title = "We couldn't analyze that site",
  message = "Something went wrong while trying to reach that website. Double-check the URL and try again.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="relative mx-auto w-full max-w-xl overflow-hidden rounded-2xl border border-red-400/20 bg-[#0D0F15]/90 p-6 text-center shadow-[0_25px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-8 motion-safe:animate-[errorReveal_500ms_cubic-bezier(0.16,1,0.3,1)_both]"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-500/10 blur-[100px]"
      />

      <div className="relative mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-red-400/25 bg-red-400/10">
        <AlertTriangle className="h-5 w-5 text-red-400" aria-hidden="true" />
      </div>

      <h3 className="relative mt-5 text-lg font-semibold tracking-tight text-white">
        {title}
      </h3>

      <p className="relative mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-400">
        {message}
      </p>

      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="group relative mt-6 inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-[#7C5CFF] px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(124,92,255,0.25)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#896EFF] hover:shadow-[0_18px_50px_rgba(124,92,255,0.38)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0"
        >
          <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          <RotateCcw className="relative h-4 w-4" aria-hidden="true" />
          <span className="relative">Try again</span>
        </button>
      ) : null}

      <style jsx>{`
        @keyframes errorReveal {
          from {
            opacity: 0;
            transform: translateY(12px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        @media (prefers-reduced-motion: reduce) {
          div {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}