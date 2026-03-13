"use client";

import { motion } from "framer-motion";
import { FeatureContributions } from "@/types";
import { cn } from "@/lib/utils";

interface ShapChartProps {
  contributions: FeatureContributions;
}

const LABELS: Record<string, string> = {
  provider_is_high_risk: "Provider Risk Flag",
  amount_deviation_pct: "Amount Deviation %",
  code_match: "Diagnosis/Procedure Match",
  provider_claim_frequency: "Provider Claim Frequency",
  member_claim_frequency: "Member Claim Frequency",
  member_age: "Member Age",
  amount_ratio: "Amount vs Tariff Ratio",
  is_duplicate: "Duplicate Claim Flag",
};

export function ShapChart({ contributions }: ShapChartProps) {
  const entries = Object.entries(contributions)
    .map(([key, value]) => ({
      key,
      label: LABELS[key] ?? key,
      value: value as number,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const maxAbs = Math.max(...entries.map((e) => Math.abs(e.value)), 0.01);

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-foreground">
          Feature Contributions
        </h2>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          SHAP values — positive values increase risk, negative values reduce it
        </p>
      </div>

      <div className="space-y-3">
        {entries.map(({ key, label, value }, i) => {
          const pct = (Math.abs(value) / maxAbs) * 100;
          const positive = value > 0;

          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="grid grid-cols-[1fr_120px_64px] gap-3 items-center"
            >
              <span className="text-xs text-muted-foreground truncate">
                {label}
              </span>

              <div className="relative h-1.5 rounded-full bg-muted overflow-hidden">
                <motion.div
                  className={cn(
                    "absolute top-0 h-full rounded-full",
                    positive
                      ? "bg-red-400 right-1/2"
                      : "bg-emerald-400 left-1/2",
                  )}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct / 2}%` }}
                  transition={{
                    duration: 0.5,
                    delay: i * 0.04,
                    ease: "easeOut",
                  }}
                />
              </div>

              <span
                className={cn(
                  "text-[11px] font-mono tabular-nums text-right",
                  positive ? "text-red-400" : "text-emerald-400",
                )}
              >
                {value > 0 ? "+" : ""}
                {value.toFixed(3)}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
