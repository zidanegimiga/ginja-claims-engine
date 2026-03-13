"use client";

import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Activity,
  TrendingUp,
} from "lucide-react";
import {
  useClaimsSample,
  useDashboardStats,
  useRecentClaims,
} from "@/hooks/useDashboard";
import { StatCard } from "@/features/dashboard/components/StatCard";
import { StatCardSkeleton } from "@/components/ui/Skeleton";
import { DecisionChart } from "@/features/dashboard/components/DecisionChart";
import { RiskHistogram } from "@/features/dashboard/components/RiskHistogram";
import { formatPercent, formatDuration } from "@/lib/utils";
import { ClaimsTable } from "@/features/claims/components/ClaimsTable";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: recent, isLoading: recentLoading } = useRecentClaims({
    limit: 8,
  });
  const { data: sample, isLoading: sampleLoading } = useClaimsSample();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground tracking-tight">
          Dashboard
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Claims intelligence overview
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {statsLoading ? (
          Array.from({ length: 6 }).map((_, i) => <StatCardSkeleton key={i} />)
        ) : (
          <>
            <StatCard
              label="Total Claims"
              value={stats?.total_claims.toLocaleString() ?? "—"}
              icon={FileText}
              sub="All time"
              delay={0}
              accent
            />
            <StatCard
              label="Passed"
              value={stats?.passed.toLocaleString() ?? "—"}
              icon={CheckCircle2}
              sub={
                stats
                  ? `${formatPercent(stats.passed / stats.total_claims)} of total`
                  : ""
              }
              trend="up"
              delay={0.05}
            />
            <StatCard
              label="Flagged"
              value={stats?.flagged.toLocaleString() ?? "—"}
              icon={AlertTriangle}
              sub={
                stats
                  ? `${formatPercent(stats.flagged / stats.total_claims)} of total`
                  : ""
              }
              trend="neutral"
              delay={0.1}
            />
            <StatCard
              label="Failed"
              value={stats?.failed.toLocaleString() ?? "—"}
              icon={XCircle}
              sub={
                stats
                  ? `${formatPercent(stats.failed / stats.total_claims)} of total`
                  : ""
              }
              trend="down"
              delay={0.15}
            />
            <StatCard
              label="Avg Risk Score"
              value={stats?.avg_risk_score.toFixed(3) ?? "—"}
              icon={Activity}
              sub="Across all claims"
              delay={0.2}
            />
            <StatCard
              label="Fraud Rate"
              value={stats ? formatPercent(stats.fraud_rate) : "—"}
              icon={TrendingUp}
              sub="Failed / total"
              trend={
                stats ? (stats.fraud_rate > 0.1 ? "down" : "up") : "neutral"
              }
              delay={0.25}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DecisionChart stats={stats} loading={statsLoading} />
        <RiskHistogram claims={sample?.results} loading={sampleLoading} />
      </div>

      <ClaimsTable claims={recent?.results ?? []} loading={recentLoading} />
    </div>
  );
}
