"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import {
  Building2,
  MapPin,
  Phone,
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { useRecentClaims } from "@/hooks/useDashboard";
import { Skeleton } from "@/components/ui/Skeleton";
import { DecisionBadge } from "@/components/ui/Badge";
import { cn, formatCurrency } from "@/lib/utils";

const CARD = "rounded-xl border border-border bg-card p-5";

interface ProviderSummary {
  provider_id: string;
  total: number;
  passed: number;
  flagged: number;
  failed: number;
  avg_amount: number;
  fraud_rate: number;
}

function useProviderSummaries() {
  const { data, isLoading } = useRecentClaims({ limit: 500 });

  if (!data) return { providers: [], isLoading };

  const map: Record<string, ProviderSummary> = {};

  data.results.forEach((claim) => {
    const id = claim.provider_id ?? "unknown";
    if (!map[id]) {
      map[id] = {
        provider_id: id,
        total: 0,
        passed: 0,
        flagged: 0,
        failed: 0,
        avg_amount: 0,
        fraud_rate: 0,
      };
    }
    const p = map[id];
    p.total++;
    if (claim.decision === "Pass") p.passed++;
    if (claim.decision === "Flag") p.flagged++;
    if (claim.decision === "Fail") p.failed++;
    p.avg_amount += claim.claimed_amount ?? 0;
  });

  const providers = Object.values(map)
    .map((p) => ({
      ...p,
      avg_amount: p.total > 0 ? p.avg_amount / p.total : 0,
      fraud_rate: p.total > 0 ? (p.failed / p.total) * 100 : 0,
    }))
    .sort((a, b) => b.total - a.total);

  return { providers, isLoading };
}

export default function ProvidersPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const role = session?.user?.role;

  const { providers, isLoading } = useProviderSummaries();

  // Redirect non-admins
  useEffect(() => {
    if (role && role !== "admin") router.replace("/dashboard");
  }, [role, router]);

  if (role && role !== "admin") return null;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* ── Header ───────────────────────────────────────────────── */}
      <div>
        <h1
          className="text-xl font-semibold text-foreground tracking-tight"
          style={{ fontFamily: "var(--font-syne)" }}
        >
          Providers
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Healthcare provider performance and risk overview
        </p>
      </div>

      {/* ── Summary cards ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          {
            label: "Total Providers",
            value: providers.length,
            icon: Building2,
            color: "text-accent",
          },
          {
            label: "High Risk Providers",
            value: providers.filter((p) => p.fraud_rate > 30).length,
            icon: AlertTriangle,
            color: "text-red-500",
          },
          {
            label: "Clean Providers",
            value: providers.filter((p) => p.fraud_rate === 0).length,
            icon: CheckCircle2,
            color: "text-emerald-500",
          },
        ].map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={CARD}
          >
            <div className="flex items-center gap-2 mb-2">
              <card.icon
                className={cn("w-4 h-4", card.color)}
                strokeWidth={1.5}
              />
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                {card.label}
              </span>
            </div>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-2xl font-semibold text-foreground tabular-nums">
                {card.value}
              </p>
            )}
          </motion.div>
        ))}
      </div>

      {/* ── Providers table ──────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="rounded-xl border border-border bg-card overflow-hidden"
      >
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">
            All Providers
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {[
                  "Provider ID",
                  "Total Claims",
                  "Passed",
                  "Flagged",
                  "Failed",
                  "Avg Amount",
                  "Fraud Rate",
                ].map((col) => (
                  <th
                    key={col}
                    className="px-5 py-3 text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-border">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-5 py-3">
                          <Skeleton className="h-4 w-20" />
                        </td>
                      ))}
                    </tr>
                  ))
                : providers.map((p, i) => (
                    <motion.tr
                      key={p.provider_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-5 py-3 font-mono text-xs text-foreground tabular-nums">
                        {p.provider_id}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-foreground">
                        {p.total}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-emerald-500">
                        {p.passed}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-amber-500">
                        {p.flagged}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-red-500">
                        {p.failed}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-foreground">
                        {formatCurrency(p.avg_amount)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden max-w-[60px]">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                p.fraud_rate > 50
                                  ? "bg-red-500"
                                  : p.fraud_rate > 20
                                    ? "bg-amber-500"
                                    : "bg-emerald-500",
                              )}
                              style={{
                                width: `${Math.min(p.fraud_rate, 100)}%`,
                              }}
                            />
                          </div>
                          <span
                            className={cn(
                              "text-xs tabular-nums font-medium",
                              p.fraud_rate > 50
                                ? "text-red-500"
                                : p.fraud_rate > 20
                                  ? "text-amber-500"
                                  : "text-emerald-500",
                            )}
                          >
                            {p.fraud_rate.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
            </tbody>
          </table>

          {!isLoading && providers.length === 0 && (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No provider data yet — adjudicate some claims first.
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
