/* eslint-disable @typescript-eslint/ban-ts-comment */
"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { DashboardStats } from "@/types";
import { Skeleton } from "@/components/ui/Skeleton";

interface DecisionChartProps {
  stats?: DashboardStats;
  loading?: boolean;
}

const COLORS = {
  Pass: "hsl(142, 71%, 45%)",
  Flag: "hsl(38, 92%, 50%)",
  Fail: "hsl(0, 72%, 51%)",
};

export function DecisionChart({ stats, loading }: DecisionChartProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-5">
        <Skeleton className="h-4 w-36 mb-4" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    );
  }

  const data = [
    { name: "Pass", value: stats?.passed ?? 0 },
    { name: "Flag", value: stats?.flagged ?? 0 },
    { name: "Fail", value: stats?.failed ?? 0 },
  ].filter((d) => d.value > 0);

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-sm font-semibold text-foreground mb-4">
        Decision Distribution
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={COLORS[entry.name as keyof typeof COLORS]}
                opacity={0.9}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "hsl(240, 10%, 7%)",
              border: "1px solid hsl(240, 3.7%, 15.9%)",
              borderRadius: "8px",
              fontSize: "12px",
              color: "hsl(0, 0%, 98%)",
            }}
            //@ts-ignore
            formatter={(value: number, name: string) => [
              `${value} claims`,
              name,
            ]}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span style={{ color: "hsl(240, 5%, 54%)", fontSize: "11px" }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
