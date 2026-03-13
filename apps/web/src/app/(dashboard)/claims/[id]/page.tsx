"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Hash,
  User,
  Building2,
  Calendar,
  FileText,
  ExternalLink,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useClaim } from "@/hooks/useClaim";
import { DecisionBadge } from "@/components/ui/Badge";
import { RiskScore } from "@/components/ui/RiskScore";
import { Skeleton } from "@/components/ui/Skeleton";
import { ShapChart } from "@/features/claims/components/ShapChart";
import { DocumentLinks } from "@/features/claims/components/DocumentLinks";

import {
  formatCurrency,
  formatDateTime,
  formatDuration,
  cn,
} from "@/lib/utils";

interface Props {
  params: Promise<{ id: string }>;
}

export default function ClaimDetailPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { data: claim, isLoading, error } = useClaim(id);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertTriangle className="w-8 h-8 text-destructive" strokeWidth={1.5} />
        <p className="text-sm text-muted-foreground">Claim not found</p>
        <button
          onClick={() => router.back()}
          className="text-xs text-accent hover:text-accent/80 transition-colors"
        >
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-start gap-4">
        <button
          onClick={() => router.back()}
          className="mt-0.5 flex items-center justify-center w-8 h-8 rounded-lg border border-border hover:bg-muted transition-colors shrink-0"
        >
          <ArrowLeft
            className="w-4 h-4 text-muted-foreground"
            strokeWidth={1.5}
          />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            {isLoading ? (
              <Skeleton className="h-6 w-48" />
            ) : (
              <>
                <h1 className="text-xl font-semibold text-foreground font-mono tabular-nums">
                  {claim?.claim_id}
                </h1>
                {claim && <DecisionBadge decision={claim.decision} />}
              </>
            )}
          </div>
          <div className="text-sm text-muted-foreground mt-0.5">
            {isLoading ? (
              <Skeleton className="h-4 w-40 mt-1" />
            ) : (
              `Adjudicated ${formatDateTime(claim?.adjudicated_at)}`
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: User, label: "Member ID", value: claim?.member_id },
          { icon: Building2, label: "Provider", value: claim?.provider_id },
          {
            icon: Hash,
            label: "Claimed",
            value: formatCurrency(claim?.claimed_amount as number),
          },
          {
            icon: Calendar,
            label: "Date of Service",
            value: formatDateTime(claim?.date_of_service),
          },
        ].map(({ icon: Icon, label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-border bg-card p-4"
          >
            <div className="flex items-center gap-1.5 mb-2">
              <Icon
                className="w-3.5 h-3.5 text-muted-foreground"
                strokeWidth={1.5}
              />
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                {label}
              </span>
            </div>
            {isLoading ? (
              <Skeleton className="h-5 w-24" />
            ) : (
              <p className="text-sm font-medium text-foreground tabular-nums">
                {value ?? "—"}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-1.5 mb-3">
            <ShieldCheck
              className="w-3.5 h-3.5 text-muted-foreground"
              strokeWidth={1.5}
            />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Risk Score
            </span>
          </div>
          {isLoading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div className="space-y-2">
              <RiskScore score={claim?.risk_score ?? 0} size="lg" />
              <p className="text-[11px] text-muted-foreground">
                Confidence: {((claim?.confidence ?? 0) * 100).toFixed(1)}%
              </p>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-1.5 mb-3">
            <Zap
              className="w-3.5 h-3.5 text-muted-foreground"
              strokeWidth={1.5}
            />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Adjudication Stage
            </span>
          </div>
          {isLoading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <div className="space-y-1">
              <p className="text-2xl font-semibold text-foreground">
                Stage {claim?.adjudication_stage}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {
                  {
                    1: "Basic validation",
                    2: "Clinical rules",
                    3: "ML scoring",
                  }[claim?.adjudication_stage ?? 3]
                }
              </p>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-1.5 mb-3">
            <Clock
              className="w-3.5 h-3.5 text-muted-foreground"
              strokeWidth={1.5}
            />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Processing Time
            </span>
          </div>
          {isLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <p className="text-2xl font-semibold text-foreground tabular-nums">
              {formatDuration(claim?.processing_time_ms ?? 0)}
            </p>
          )}
        </div>
      </div>

      {!isLoading && claim?.reasons && claim.reasons.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Adjudication Reasons
          </h2>
          <ul className="space-y-2">
            {claim.reasons.map((reason, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 text-sm text-muted-foreground"
              >
                <AlertTriangle
                  className="w-3.5 h-3.5 text-warning shrink-0 mt-0.5"
                  strokeWidth={1.5}
                />
                {reason}
              </li>
            ))}
          </ul>
          {claim.explanation_of_benefits && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">
                Explanation of Benefits
              </p>
              <p className="text-sm text-foreground leading-relaxed">
                {claim.explanation_of_benefits}
              </p>
            </div>
          )}
        </div>
      )}

      {!isLoading && claim && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Financials
          </h2>
          <div className="space-y-0">
            {[
              {
                label: "Claimed Amount",
                value: formatCurrency(claim.claimed_amount),
              },
              {
                label: "Approved Tariff",
                value: formatCurrency(claim.approved_tariff),
              },
              {
                label: "Variance",
                value: (
                  <span
                    className={
                      claim.claimed_amount > claim.approved_tariff
                        ? "text-red-500"
                        : "text-emerald-500"
                    }
                  >
                    {claim.claimed_amount > claim.approved_tariff ? "+" : ""}
                    {formatCurrency(
                      claim.claimed_amount - claim.approved_tariff,
                    )}
                  </span>
                ),
              },
              {
                label: "Deviation",
                value: (
                  <span
                    className={
                      Math.abs(claim.claimed_amount - claim.approved_tariff) /
                        claim.approved_tariff >
                      0.1
                        ? "text-red-500"
                        : "text-muted-foreground"
                    }
                  >
                    {(
                      ((claim.claimed_amount - claim.approved_tariff) /
                        claim.approved_tariff) *
                      100
                    ).toFixed(1)}
                    %
                  </span>
                ),
              },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex items-center justify-between py-2.5 border-b border-border last:border-0"
              >
                <span className="text-xs text-muted-foreground">{label}</span>
                <span className="text-xs font-mono tabular-nums text-foreground">
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isLoading && claim?.patient && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Patient
          </h2>
          <div className="space-y-0">
            {[
              { label: "Full Name", value: claim.patient.full_name },
              { label: "National ID", value: claim.patient.national_id },
              { label: "Date of Birth", value: claim.patient.date_of_birth },
              { label: "Phone", value: claim.patient.phone },
              { label: "Scheme Number", value: claim.patient.scheme_number },
              {
                label: "Age",
                value: claim.member_age
                  ? `${claim.member_age} years`
                  : undefined,
              },
            ]
              .filter((row) => row.value)
              .map(({ label, value }) => (
                <div
                  key={label}
                  className="flex items-center justify-between py-2.5 border-b border-border last:border-0"
                >
                  <span className="text-xs text-muted-foreground">{label}</span>
                  <span className="text-xs font-mono tabular-nums text-foreground">
                    {value}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {!isLoading && claim?.audit_trail && claim.audit_trail.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Audit Trail
          </h2>
          <div className="space-y-3">
            {claim.audit_trail.map((entry, i: number) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-accent mt-1.5 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-foreground">
                    {entry.action}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {entry.timestamp ? formatDateTime(entry.timestamp) : ""}
                    {entry.actor ? ` · ${entry.actor}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isLoading && claim?.feature_contributions && (
        <ShapChart contributions={claim.feature_contributions} />
      )}

      {!isLoading && claim?.source && (
        <DocumentLinks claimId={claim.claim_id} source={claim.source} />
      )}
    </div>
  );
}
