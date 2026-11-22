"use client";

import {
  BarChart3,
  BookOpenCheck,
  CheckCheck,
  FileText,
  Globe2,
  Lightbulb,
  Map,
  PenLine,
  ScanSearch,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import Reveal from "@/components/common/Reveal";

interface Feature {
  title: string;
  description: string;
  icon: LucideIcon;
  accent: string;
  /**
   * True for features that don't exist in the product yet (their component
   * folders currently contain no implementation). Keeps this section honest
   * about current capability rather than implying everything listed here is
   * already live in the dashboard.
   */
  comingSoon?: boolean;
}

const FEATURES: Feature[] = [
  {
    title: "Website Analysis",
    description:
      "Understand the strengths and weaknesses of your website content at a glance.",
    icon: ScanSearch,
    accent: "#7C5CFF",
  },
  {
    title: "SEO Analysis",
    description:
      "Surface the content signals that can make your pages easier to discover.",
    icon: BarChart3,
    accent: "#A78BFA",
  },
  {
    title: "Readability",
    description:
      "See where your writing becomes difficult to scan, understand, or follow.",
    icon: BookOpenCheck,
    accent: "#67E8F9",
  },
  {
    title: "Grammar",
    description:
      "Catch grammar and wording issues before they reach your audience.",
    icon: CheckCheck,
    accent: "#8B6FFF",
  },
  {
    title: "AI Rewrite",
    description:
      "Transform unclear sentences into cleaner, more confident writing.",
    icon: PenLine,
    accent: "#A78BFA",
    comingSoon: true,
  },
  {
    title: "AI Suggestions",
    description:
      "Get practical recommendations that explain what to change and why.",
    icon: Lightbulb,
    accent: "#67E8F9",
    comingSoon: true,
  },
  {
    title: "Before / After",
    description:
      "Compare original and improved content so every change stays understandable.",
    icon: FileText,
    accent: "#7C5CFF",
  },
  {
    title: "Confusion Heatmap",
    description:
      "Visually identify the parts of your content that may create friction for readers.",
    icon: Map,
    accent: "#A78BFA",
    comingSoon: true,
  },
  {
    title: "Location Intelligence",
    description:
      "Understand how content can be interpreted across different geographic audiences.",
    icon: Globe2,
    accent: "#67E8F9",
    comingSoon: true,
  },
];

export default function FeatureGrid() {
  return (
    <section
      id="features"
      className="relative overflow-hidden bg-[#08090D] py-24 sm:py-32"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/3 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-[#7C5CFF]/[0.045] blur-[140px]"
      />

      <div className="relative mx-auto max-w-7xl px-5 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#A78BFA]">
            Everything your content needs
          </p>

          <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">
            One intelligence layer for your website.
          </h2>

          <p className="mt-4 text-base leading-7 text-slate-400">
            From the first analysis to the final rewrite, Verbly helps you
            understand what your content is saying and how to make it better.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => {
            const Icon = feature.icon;

            return (
              <Reveal
                key={feature.title}
                delayMs={index * 70}
                className="h-full"
              >
                <article className="group relative h-full overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6 transition-all duration-500 hover:-translate-y-1 hover:border-white/[0.14] hover:bg-white/[0.045] hover:shadow-[0_20px_60px_rgba(0,0,0,0.3)]">
                  {/* Hover glow */}
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute -right-20 -top-20 h-40 w-40 rounded-full opacity-0 blur-[70px] transition-opacity duration-500 group-hover:opacity-30"
                    style={{ backgroundColor: feature.accent }}
                  />

                  {/* Icon */}
                  <div
                    className="relative flex h-11 w-11 items-center justify-center rounded-xl border transition-all duration-500 group-hover:scale-105"
                    style={{
                      borderColor: `${feature.accent}35`,
                      backgroundColor: `${feature.accent}12`,
                    }}
                  >
                    <Icon
                      className="h-5 w-5 transition-transform duration-500 group-hover:rotate-[-4deg] group-hover:scale-110"
                      style={{ color: feature.accent }}
                    />
                  </div>

                  <h3 className="relative mt-6 flex items-start justify-between gap-2 text-lg font-semibold tracking-tight text-white">
                    <span>{feature.title}</span>
                    {feature.comingSoon && (
                      <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium normal-case tracking-normal text-slate-400">
                        Coming soon
                      </span>
                    )}
                  </h3>

                  <p className="relative mt-2 text-sm leading-6 text-slate-400">
                    {feature.description}
                  </p>

                  {/* Bottom interaction line */}
                  <div className="relative mt-7 h-px overflow-hidden bg-white/[0.06]">
                    <div
                      className="h-full w-0 transition-all duration-700 ease-out group-hover:w-full"
                      style={{
                        background: `linear-gradient(90deg, transparent, ${feature.accent}, transparent)`,
                      }}
                    />
                  </div>

                  {/* Small corner marker */}
                  <div className="absolute right-5 top-5 opacity-0 transition-all duration-500 group-hover:translate-x-0 group-hover:opacity-100">
                    <Sparkles
                      className="h-3.5 w-3.5"
                      style={{ color: feature.accent }}
                    />
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}