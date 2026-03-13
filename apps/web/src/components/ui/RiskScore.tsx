import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface RiskScoreProps {
  score: number; // 0–1
  showBar?: boolean;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}

function getRiskColor(score: number) {
  if (score < 0.3) return { text: "text-emerald-400", bar: "bg-emerald-400" };
  if (score < 0.6) return { text: "text-amber-400", bar: "bg-amber-400" };
  return { text: "text-red-400", bar: "bg-red-400" };
}

export function RiskScore({
  score,
  showBar = true,
  showLabel = true,
  size = "md",
}: RiskScoreProps) {
  const { text, bar } = getRiskColor(score);
  const pct = `${(score * 100).toFixed(0)}%`;

  const textSize = { sm: "text-[11px]", md: "text-sm", lg: "text-base" }[size];

  return (
    <div className="flex items-center gap-2">
      {showLabel && (
        <span
          className={cn("tabular-nums font-mono font-medium", text, textSize)}
        >
          {score.toFixed(3)}
        </span>
      )}
      {showBar && (
        <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
          <motion.div
            className={cn("h-full rounded-full", bar)}
            initial={{ width: 0 }}
            animate={{ width: pct }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </div>
      )}
    </div>
  );
}
