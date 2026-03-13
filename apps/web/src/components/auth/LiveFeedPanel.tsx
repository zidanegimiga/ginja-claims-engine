"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2, AlertTriangle, XCircle, TrendingUp, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

const FEED_ITEMS = [
  { id: "CLM-00291", member: "M-4821", amount: "KES 12,400",  decision: "Pass", risk: 0.08, time: "just now" },
  { id: "CLM-00290", member: "M-3342", amount: "KES 87,000",  decision: "Flag", risk: 0.71, time: "1m ago"   },
  { id: "CLM-00289", member: "M-9103", amount: "KES 4,200",   decision: "Pass", risk: 0.12, time: "2m ago"   },
  { id: "CLM-00288", member: "M-1194", amount: "KES 230,000", decision: "Fail", risk: 0.94, time: "3m ago"   },
  { id: "CLM-00287", member: "M-6677", amount: "KES 18,750",  decision: "Pass", risk: 0.21, time: "5m ago"   },
  { id: "CLM-00286", member: "M-2251", amount: "KES 54,300",  decision: "Flag", risk: 0.63, time: "6m ago"   },
];

const STATS = [
  { label: "Processed today", value: "1,284", sub: "+12% vs yesterday" },
  { label: "Avg risk score",  value: "0.24",  sub: "Healthy baseline"  },
  { label: "Fraud detected",  value: "3.1%",  sub: "38 claims flagged" },
];

function DecisionIcon({ decision }: { decision: string }) {
  if (decision === "Pass") return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" strokeWidth={1.5} />;
  if (decision === "Flag") return <AlertTriangle className="w-3.5 h-3.5 text-amber-400"   strokeWidth={1.5} />;
  return <XCircle className="w-3.5 h-3.5 text-red-400" strokeWidth={1.5} />;
}

function RiskBar({ score }: { score: number }) {
  const color = score < 0.3 ? "bg-emerald-400" : score < 0.6 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="w-16 h-1 rounded-full bg-white/10 overflow-hidden">
      <motion.div
        className={cn("h-full rounded-full", color)}
        initial={{ width: 0 }}
        animate={{ width: `${score * 100}%` }}
        transition={{ duration: 0.6, ease: "easeOut", delay: 0.3 }}
      />
    </div>
  );
}

export function LiveFeedPanel() {
  return (
    <div className="relative h-full flex flex-col justify-between p-10">

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-[hsl(171,77%,40%)]/[0.06] blur-[100px] pointer-events-none" />
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="relative"
      >
        <div className="flex items-center gap-2 mb-1">
          <div className="w-1.5 h-1.5 rounded-full bg-[hsl(171,77%,56%)] animate-pulse" />
          <span className="text-[11px] font-medium text-[hsl(171,77%,56%)] uppercase tracking-widest">
            Live adjudication feed
          </span>
        </div>
        <p className="text-white/30 text-xs">
          Real-time claims processing across Kenya and Rwanda
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="relative grid grid-cols-3 gap-3"
      >
        {STATS.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + i * 0.07 }}
            className="rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3"
          >
            <p className="text-[10px] text-white/35 uppercase tracking-wider mb-1">{stat.label}</p>
            <p className="text-xl font-semibold text-white tabular-nums">{stat.value}</p>
            <p className="text-[10px] text-[hsl(171,77%,56%)]/70 mt-0.5">{stat.sub}</p>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.35 }}
        className="relative flex-1 flex flex-col justify-center"
      >
        <p className="text-[10px] text-white/25 uppercase tracking-widest mb-3">Recent decisions</p>
        <div className="space-y-1.5">
          {FEED_ITEMS.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.06, duration: 0.35 }}
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-white/[0.05] bg-white/[0.02] hover:bg-white/[0.04] transition-colors duration-150"
            >
              <DecisionIcon decision={item.decision} />
              <span className="text-[11px] font-mono text-white/50 w-24 shrink-0">{item.id}</span>
              <span className="text-[11px] text-white/30 w-16 shrink-0">{item.member}</span>
              <span className="text-[11px] font-mono text-white/70 flex-1 tabular-nums">{item.amount}</span>
              <RiskBar score={item.risk} />
              <span className="text-[10px] text-white/25 w-12 text-right shrink-0">{item.time}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="relative flex items-center justify-between"
      >
        <div className="flex items-center gap-2 text-[10px] text-white/20">
          <TrendingUp className="w-3 h-3" strokeWidth={1.5} />
          <span>Powered by XGBoost + SHAP explainability</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-white/20">
          <Clock className="w-3 h-3" strokeWidth={1.5} />
          <span className="tabular-nums">avg 142ms adjudication</span>
        </div>
      </motion.div>
    </div>
  );
}