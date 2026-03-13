"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Hash, User, Building2, Clock, ChevronRight } from "lucide-react";
import { ClaimListItem } from "@/types";
import { DecisionBadge } from "@/components/ui/Badge";
import { RiskScore } from "@/components/ui/RiskScore";
import { TableRowSkeleton } from "@/components/ui/Skeleton";
import { formatDateTime, truncateId, formatCurrency } from "@/lib/utils";

interface ClaimsTableProps {
  claims: ClaimListItem[];
  loading?: boolean;
  showHeader?: boolean;
}

export function ClaimsTable({
  claims,
  loading = false,
  showHeader = true,
}: ClaimsTableProps) {
  const router = useRouter();

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {showHeader && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">
            Recent Claims
          </h2>
          <button
            onClick={() => router.push("/claims")}
            className="text-[11px] text-accent hover:text-accent/80 transition-colors flex items-center gap-1"
          >
            View all
            <ChevronRight className="w-3 h-3" strokeWidth={2} />
          </button>
        </div>
      )}

      {/* Table header */}
      <div className="grid grid-cols-[1fr_1fr_1fr_100px_80px_140px_32px] gap-4 px-5 py-2.5 border-b border-border bg-muted/30">
        {[
          { icon: Hash, label: "Claim ID" },
          { icon: User, label: "Member" },
          { icon: Building2, label: "Provider" },
          // { icon: null, label: "Amount" },
          { icon: null, label: "Decision" },
          { icon: Clock, label: "Date" },
          { icon: null, label: "" },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            {Icon && (
              <Icon
                className="w-3 h-3 text-muted-foreground/60"
                strokeWidth={1.5}
              />
            )}
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              {label}
            </span>
          </div>
        ))}
      </div>

      {/* Rows */}
      <div className="divide-y divide-border">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
        ) : claims.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-muted-foreground">
            No claims found
          </div>
        ) : (
          claims.map((claim, i) => (
            <motion.div
              key={claim.claim_id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.04 }}
              onClick={() => router.push(`/claims/${claim.claim_id}`)}
              className="grid grid-cols-[1fr_1fr_1fr_100px_80px_140px_32px] gap-4 px-5 py-3.5 hover:bg-muted/30 transition-colors duration-150 cursor-pointer group"
            >
              {/* <span className="text-[12px] font-mono text-muted-foreground tabular-nums truncate">
                {truncateId(claim.claim_id, 12)}
              </span> */}
              <span className="text-[12px] text-foreground font-mono tabular-nums truncate">
                {claim.member_id}
              </span>
              <span className="text-[12px] text-muted-foreground truncate">
                {claim.provider_id}
              </span>
              {/* <span className="text-[12px] font-mono tabular-nums text-foreground">
                {formatCurrency(claim.claimed_amount)}
                {claim.claimed_amount}
              </span> */}
              <DecisionBadge decision={claim.decision} />
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {formatDateTime(claim.adjudicated_at)}
              </span>
              <ChevronRight
                className="w-3.5 h-3.5 text-muted-foreground/0 group-hover:text-muted-foreground transition-colors"
                strokeWidth={1.5}
              />
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
