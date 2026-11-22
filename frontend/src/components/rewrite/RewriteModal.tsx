"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import type { Finding } from "@/lib/analysis/types";
import type {
  GenerateRewrite,
  RewriteResult,
  RewriteStatus,
  RewriteTone,
} from "@/lib/rewrite/types";
import RewriteToneSelector from "./RewriteToneSelector";
import RewriteComparison from "./RewriteComparison";
import RewriteActions from "./RewriteActions";

interface RewriteModalProps {
  finding: Finding;
  onClose: () => void;
  onGenerateRewrite?: GenerateRewrite;
  initialResult?: RewriteResult;
  onRewriteComplete?: (result: RewriteResult) => void;
  initialCustomInstruction?: string;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * The Rewrite workspace: an accessible modal dialog showing a finding's
 * original content next to its AI-rewritten version, with tone controls and
 * generate/regenerate/copy actions. Deliberately has no Accept/Apply action
 * (see Phase 7 audit) since there is currently no legitimate destination for
 * an applied rewrite.
 */
export default function RewriteModal({
  finding,
  onClose,
  onGenerateRewrite,
  initialCustomInstruction,
  initialResult,
  onRewriteComplete,
}: RewriteModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const [mounted, setMounted] = useState(false);
  const [tone, setTone] = useState<RewriteTone>(initialResult?.tone ?? "concise");
  const [customInstruction, setCustomInstruction] = useState(initialCustomInstruction ?? "");
  const [status, setStatus] = useState<RewriteStatus>(initialResult ? "success" : "idle",);
  const [result, setResult] = useState<RewriteResult | null>(initialResult ?? null,);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [copied, setCopied] = useState(false);

  const originalContent = finding.sourceExcerpt ?? "";
  const isGeneratorConnected = Boolean(onGenerateRewrite);

  // Portal target is only available client-side; avoids an SSR/hydration
  // mismatch from rendering into document.body before it exists.
  useEffect(() => {
    setMounted(true);
  }, []);

  // Move focus into the dialog once it has actually rendered (i.e. after
  // `mounted` flips true — the portal content, including the close button,
  // doesn't exist in the DOM before then), and lock background scroll while
  // the dialog is open. Both are undone on unmount (when the modal closes).
  useEffect(() => {
    if (!mounted) return;

    closeButtonRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mounted]);

  // Escape closes the dialog; Tab is trapped within it while open.
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }

    if (event.key !== "Tab" || !dialogRef.current) return;

    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    ).filter((el) => el.offsetParent !== null);

    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleGenerate = async () => {
    if (!onGenerateRewrite) return;

    setStatus("loading");
    setErrorMessage(undefined);

    try {
      const generated = await onGenerateRewrite({
        findingId: finding.id,
        category: finding.category,
        originalContent,
        tone,
        customInstruction: customInstruction.trim() || undefined,
      });
      setResult(generated);
      setStatus("success");
      onRewriteComplete?.(generated);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Something went wrong generating this rewrite.",
      );
      setStatus("error");
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.rewrittenContent);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be denied or unavailable in some environments —
      // the Copy button simply won't show the "Copied" confirmation.
    }
  };

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6"
      onKeyDown={handleKeyDown}
    >
      <div
        aria-hidden="true"
        onClick={onClose}
        className="absolute inset-0 bg-[#050609]/80 backdrop-blur-sm motion-safe:animate-[rewriteOverlayIn_300ms_ease-out_both]"
      />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex h-full w-full max-w-full flex-col overflow-hidden border border-white/10 bg-[#0B0C12] shadow-[0_24px_80px_rgba(0,0,0,0.5)] motion-safe:animate-[rewriteSheetIn_350ms_cubic-bezier(0.16,1,0.3,1)_both] sm:h-auto sm:max-h-[85vh] sm:w-full sm:max-w-2xl sm:rounded-3xl sm:border-white/10 sm:bg-white/[0.03] sm:backdrop-blur-xl"
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-white/10 px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#A78BFA]">
              Rewrite with AI
            </span>
            <h2
              id={titleId}
              className="mt-1 truncate text-base font-semibold tracking-tight text-white sm:text-lg"
            >
              {finding.title}
            </h2>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close rewrite workspace"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors duration-300 hover:bg-white/[0.06] hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <div className="space-y-5">
            <RewriteComparison
              original={originalContent}
              rewritten={result?.rewrittenContent ?? null}
              status={status}
            />

            <RewriteToneSelector
              tone={tone}
              onToneChange={setTone}
              customInstruction={customInstruction}
              onCustomInstructionChange={setCustomInstruction}
              disabled={status === "loading" || !isGeneratorConnected}
            />
          </div>
        </div>

        <div className="shrink-0 border-t border-white/10 bg-[#0B0C12] px-5 py-4 sm:bg-transparent sm:px-6">
          <RewriteActions
            status={status}
            isGeneratorConnected={isGeneratorConnected}
            errorMessage={errorMessage}
            copied={copied}
            onGenerate={handleGenerate}
            onCopy={handleCopy}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes rewriteOverlayIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        @keyframes rewriteSheetIn {
          from {
            opacity: 0;
            transform: translateY(24px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>,
    document.body,
  );
}