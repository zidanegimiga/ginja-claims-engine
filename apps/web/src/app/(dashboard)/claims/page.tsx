"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Filter, Search } from "lucide-react";
import { useRecentClaims } from "@/hooks/useDashboard";
import { ClaimsTable } from "@/features/claims/components/ClaimsTable";
import { Decision } from "@/types";
import { cn } from "@/lib/utils";

const DECISIONS: { label: string; value: Decision | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pass", value: "Pass" },
  { label: "Flag", value: "Flag" },
  { label: "Fail", value: "Fail" },
];

const PAGE_SIZE = 15;

export default function ClaimsPage() {
  const [decision, setDecision] = useState<Decision | "all">("all");
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useRecentClaims({
    limit: PAGE_SIZE,
    skip: page * PAGE_SIZE,
    decision: decision === "all" ? undefined : decision,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            Claims
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data ? `${data.total.toLocaleString()} total claims` : "Loading…"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground"
            strokeWidth={1.5}
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search claim ID or member…"
            className={cn(
              "w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-card text-sm",
              "text-foreground placeholder:text-muted-foreground/50",
              "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60",
              "transition-all duration-150",
            )}
          />
        </div>

        {/* Decision filter */}
        <div className="flex items-center gap-1 p-1 rounded-lg border border-border bg-card">
          <Filter
            className="w-3.5 h-3.5 text-muted-foreground ml-2"
            strokeWidth={1.5}
          />
          {DECISIONS.map((d) => (
            <button
              key={d.value}
              onClick={() => {
                setDecision(d.value);
                setPage(0);
              }}
              className={cn(
                "h-7 px-3 rounded-md text-xs font-medium transition-all duration-150",
                decision === d.value
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <ClaimsTable
        claims={data?.results ?? []}
        loading={isLoading}
        showHeader={false}
      />

      {totalPages > 1 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-between pt-2"
        >
          <p className="text-xs text-muted-foreground">
            Page {page + 1} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className={cn(
                "h-8 px-4 rounded-lg border border-border text-xs font-medium",
                "text-muted-foreground hover:text-foreground hover:bg-muted",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                "transition-all duration-150",
              )}
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className={cn(
                "h-8 px-4 rounded-lg border border-border text-xs font-medium",
                "text-muted-foreground hover:text-foreground hover:bg-muted",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                "transition-all duration-150",
              )}
            >
              Next
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
