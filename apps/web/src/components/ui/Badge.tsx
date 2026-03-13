import { cn } from "@/lib/utils";
import { Decision } from "@/types";

interface BadgeProps {
  decision: Decision;
  className?: string;
}

const STYLES: Record<Decision, string> = {
  Pass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Flag: "bg-amber-500/10  text-amber-400 border-amber-500/20",
  Fail: "bg-red-500/10 text-red-400 border-red-500/20",
};

export function DecisionBadge({ decision, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border tabular-nums",
        STYLES[decision],
        className,
      )}
    >
      {decision}
    </span>
  );
}
