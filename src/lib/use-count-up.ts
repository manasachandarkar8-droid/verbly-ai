"use client";

import { useEffect, useRef, useState } from "react";

interface UseCountUpOptions {
  /** Duration of the animation in ms. Defaults to 900. */
  durationMs?: number;
  /** Delay before the animation starts, in ms. Defaults to 0. */
  delayMs?: number;
}

/** Cubic ease-out — quick start, gentle settle. Matches the rest of the UI's motion. */
function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
}

/**
 * Animates a number counting up from 0 to `target` whenever `target` changes.
 *
 * - Respects `prefers-reduced-motion`: jumps straight to the target value.
 * - Cleans up its `requestAnimationFrame` loop on unmount or when the target
 *   changes again mid-animation.
 */
export function useCountUp(target: number, options: UseCountUpOptions = {}): number {
  const { durationMs = 900, delayMs = 0 } = options;
  const [value, setValue] = useState(0);

  const frameRef = useRef<number | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      setValue(target);
      return;
    }

    setValue(0);

    const startAnimation = () => {
      const startTime = performance.now();

      const step = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / durationMs);
        const eased = easeOutCubic(progress);

        setValue(Math.round(eased * target));

        if (progress < 1) {
          frameRef.current = requestAnimationFrame(step);
        } else {
          frameRef.current = null;
        }
      };

      frameRef.current = requestAnimationFrame(step);
    };

    if (delayMs > 0) {
      timeoutRef.current = setTimeout(startAnimation, delayMs);
    } else {
      startAnimation();
    }

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [target, durationMs, delayMs]);

  return value;
}