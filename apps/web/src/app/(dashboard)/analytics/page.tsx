"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";
import { useClaimsSample, useDashboardStats } from "@/hooks/useDashboard";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn, formatCurrency } from "@/lib/utils";

const CARD = "rounded-xl border border-border bg-card p-5";

function StatTrend({ value }: { value: number }) {
  if (value > 0)
    return (
      <span className="flex items-center gap-1 text-xs text-emerald-500">
        <TrendingUp className="w-3 h-3" strokeWidth={2} />+{value}%
      </span>
    );
  if (value < 0)
    return (
      <span className="flex items-center gap-1 text-xs text-red-500">
        <TrendingDown className="w-3 h-3" strokeWidth={2} />
        {value}%
      </span>
    );
  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      <Minus className="w-3 h-3" strokeWidth={2} />
      0%
    </span>
  );
}

export default function AnalyticsPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: sample, isLoading: sampleLoading } = useClaimsSample();

  // Risk score distribution buckets
  const riskBuckets = useMemo(() => {
    if (!sample) return [];
    const buckets = Array.from({ length: 10 }, (_, i) => ({
      range: `${i * 10}–${i * 10 + 10}`,
      count: 0,
    }));
    sample.results.forEach((c) => {
      const idx = Math.min(Math.floor((c.risk_score ?? 0) * 10), 9);
      buckets[idx].count++;
    });
    return buckets;
  }, [sample]);

  // Amount distribution
  const amountBuckets = useMemo(() => {
    if (!sample) return [];
    const brackets = [
      { label: "0–5k", min: 0, max: 5000 },
      { label: "5–20k", min: 5000, max: 20000 },
      { label: "20–50k", min: 20000, max: 50000 },
      { label: "50–100k", min: 50000, max: 100000 },
      { label: "100k+", min: 100000, max: Infinity },
    ];
    return brackets.map((b) => ({
      label: b.label,
      count: sample.results.filter(
        (c) =>
          (c.claimed_amount ?? 0) >= b.min && (c.claimed_amount ?? 0) < b.max,
      ).length,
    }));
  }, [sample]);

  // Decision by provider type
    const providerBreakdown = useMemo(() => {
    if (!sample?.results) return [];
    const map: Record<string, { pass: number; flag: number; fail: number }> = {};
    sample.results.forEach(c => {
        const pt = c.provider_type ?? "unknown";
        if (!map[pt]) map[pt] = { pass: 0, flag: 0, fail: 0 };
        if (c.decision === "Pass") map[pt].pass++;
        if (c.decision === "Flag") map[pt].flag++;
        if (c.decision === "Fail") map[pt].fail++;
    });
    return Object.entries(map).map(([type, counts]) => ({ type, ...counts }));
    }, [sample]);

  const loading = statsLoading || sampleLoading;

  const TEAL = "hsl(171, 77%, 56%)";
  const AMBER = "hsl(38, 92%, 50%)";
  const RED = "hsl(0, 72%, 51%)";
  const MUTED = "hsl(0, 0%, 45%)";

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1
          className="text-xl font-semibold text-foreground tracking-tight"
          style={{ fontFamily: "var(--font-syne)" }}
        >
          Analytics
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Claims performance and risk intelligence
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: "Total Claims",
            value: stats?.total_claims ?? 0,
            trend: 12,
            fmt: (v: number) => v.toLocaleString(),
          },
          {
            label: "Avg Risk Score",
            value: stats?.avg_risk_score ?? 0,
            trend: -3,
            fmt: (v: number) => `${(v * 100).toFixed(1)}%`,
          },
          {
            label: "Fraud Rate",
            value: stats
              ? (stats.failed / Math.max(stats.total_claims, 1)) * 100
              : 0,
            trend: -8,
            fmt: (v: number) => `${v.toFixed(1)}%`,
          },
          {
            label: "Pass Rate",
            value: stats
              ? (stats.passed / Math.max(stats.total_claims, 1)) * 100
              : 0,
            trend: 5,
            fmt: (v: number) => `${v.toFixed(1)}%`,
          },
        ].map((kpi, i) => (
          <motion.div
            key={kpi.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={CARD}
          >
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
              {kpi.label}
            </p>
            {loading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="flex items-end justify-between">
                <p className="text-2xl font-semibold text-foreground tabular-nums">
                  {kpi.fmt(kpi.value)}
                </p>
                <StatTrend value={kpi.trend} />
              </div>
            )}
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={CARD}
        >
          <div className="flex items-center gap-2 mb-4">
            <Activity
              className="w-3.5 h-3.5 text-muted-foreground"
              strokeWidth={1.5}
            />
            <h2 className="text-sm font-semibold text-foreground">
              Risk Score Distribution
            </h2>
          </div>
          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={riskBuckets} barSize={18}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  vertical={false}
                />
                <XAxis
                  dataKey="range"
                  tick={{ fontSize: 9, fill: MUTED }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: MUTED }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  cursor={{ fill: "var(--muted)", opacity: 0.4 }}
                />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {riskBuckets.map((_, i) => (
                    <Cell key={i} fill={i < 4 ? TEAL : i < 7 ? AMBER : RED} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className={CARD}
        >
          <div className="flex items-center gap-2 mb-4">
            <Activity
              className="w-3.5 h-3.5 text-muted-foreground"
              strokeWidth={1.5}
            />
            <h2 className="text-sm font-semibold text-foreground">
              Claimed Amount Brackets
            </h2>
          </div>
          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={amountBuckets} barSize={28}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: MUTED }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: MUTED }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  cursor={{ fill: "var(--muted)", opacity: 0.4 }}
                />
                <Bar dataKey="count" fill={TEAL} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className={CARD}
      >
        <h2 className="text-sm font-semibold text-foreground mb-4">
          Decisions by Provider Type
        </h2>
        {loading ? (
          <Skeleton className="h-56 w-full" />
        ) : providerBreakdown.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Not enough data yet
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={providerBreakdown} barGap={2} barSize={16}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border)"
                vertical={false}
              />
              <XAxis
                dataKey="type"
                tick={{ fontSize: 10, fill: MUTED }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: MUTED }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                cursor={{ fill: "var(--muted)", opacity: 0.4 }}
              />
              <Bar
                dataKey="pass"
                name="Pass"
                fill={TEAL}
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey="flag"
                name="Flag"
                fill={AMBER}
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey="fail"
                name="Fail"
                fill={RED}
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </motion.div>
    </div>
  );
}
