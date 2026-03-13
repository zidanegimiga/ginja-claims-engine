"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  accent?: boolean;
  delay?: number;
}

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  trend = "neutral",
  accent = false,
  delay = 0,
}: StatCardProps) {
  const trendColor = {
    up: "text-emerald-400",
    down: "text-red-400",
    neutral: "text-muted-foreground",
  }[trend];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "rounded-lg border bg-card p-5 card-hover",
        accent ? "border-accent/30 accent-glow-sm" : "border-border",
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
        <div
          className={cn(
            "flex items-center justify-center w-7 h-7 rounded-md",
            accent
              ? "bg-accent/10 border border-accent/20"
              : "bg-muted border border-border",
          )}
        >
          <Icon
            className={cn(
              "w-3.5 h-3.5",
              accent ? "text-accent" : "text-muted-foreground",
            )}
            strokeWidth={1.5}
          />
        </div>
      </div>

      <p
        className={cn(
          "text-2xl font-semibold tracking-tight tabular-nums",
          accent ? "text-accent" : "text-foreground",
        )}
      >
        {value}
      </p>

      {sub && <p className={cn("text-[11px] mt-1", trendColor)}>{sub}</p>}
    </motion.div>
  );
}
