/* eslint-disable @typescript-eslint/ban-ts-comment */
"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { ClaimListItem } from "@/types";
import { Skeleton } from "@/components/ui/Skeleton";

interface RiskHistogramProps {
  claims?:  ClaimListItem[];
  loading?: boolean;
}

function buildBuckets(claims: ClaimListItem[]) {
  const buckets = Array.from({ length: 10 }, (_, i) => ({
    range: `${i * 10}–${(i + 1) * 10}`,
    count: 0,
    mid:   (i + 0.5) / 10,
  }));

  claims.forEach(c => {
    const idx = Math.min(Math.floor(c.risk_score * 10), 9);
    buckets[idx].count++;
  });

  return buckets;
}

function getBarColor(mid: number) {
  if (mid < 0.3) return "hsl(142, 71%, 45%)";
  if (mid < 0.6) return "hsl(38, 92%, 50%)";
  return "hsl(0, 72%, 51%)";
}

export function RiskHistogram({ claims = [], loading }: RiskHistogramProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-5">
        <Skeleton className="h-4 w-40 mb-4" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    );
  }

  const data = buildBuckets(claims);

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-sm font-semibold text-foreground mb-4">
        Risk Score Distribution
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} barSize={18}>
          <XAxis
            dataKey="range"
            tick={{ fill: "hsl(240, 5%, 54%)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "hsl(240, 5%, 54%)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              background:   "hsl(240, 10%, 7%)",
              border:       "1px solid hsl(240, 3.7%, 15.9%)",
              borderRadius: "8px",
              fontSize:     "12px",
              color:        "hsl(0, 0%, 98%)",
            }}
            // @ts-ignore
            formatter={(value: number) => [`${value} claims`, "Count"]}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={getBarColor(entry.mid)} opacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}