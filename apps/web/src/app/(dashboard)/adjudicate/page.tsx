/* eslint-disable @typescript-eslint/ban-ts-comment */
"use client";

import { useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { useAdjudicate } from "@/hooks/useClaim";
import { AdjudicationResult } from "@/types";
import { DecisionBadge } from "@/components/ui/Badge";
import { RiskScore } from "@/components/ui/RiskScore";
import { ShapChart } from "@/features/claims/components/ShapChart";
import { cn, formatDuration } from "@/lib/utils";

const schema = z.object({
  member_id: z.string().min(1, "Required"),
  provider_id: z.string().min(1, "Required"),
  diagnosis_code: z.string().min(1, "Required"),
  procedure_code: z.string().min(1, "Required"),
  claimed_amount: z
    .string()
    .min(1, "Required")
    .transform((v) => parseFloat(v)),
  approved_tariff: z
    .string()
    .min(1, "Required")
    .transform((v) => parseFloat(v)),
  date_of_service: z.string().min(1, "Required"),
  provider_type: z.enum([
    "hospital",
    "clinic",
    "pharmacy",
    "laboratory",
    "specialist",
  ]),
  location: z.string().min(1, "Required"),
  member_age: z
    .string()
    .optional()
    .transform((v) => (v ? parseInt(v) : undefined)),
});

type FormData = z.infer<typeof schema>;

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        {label}
      </label>
      {children}
      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  );
}

const inputClass = cn(
  "w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground",
  "placeholder:text-muted-foreground/50",
  "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60",
  "transition-all duration-150",
);

export default function AdjudicatePage() {
  const { mutateAsync: adjudicate, isPending } = useAdjudicate();
  const [result, setResult] = useState<AdjudicationResult | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    // @ts-ignore
    resolver: zodResolver(schema) as Resolver<FormData>,
  });

  async function onSubmit(data: FormData) {
    const res = await adjudicate({
      ...data,
      source: { source_type: "manual", documents: [] },
    });
    setResult(res);
  }

  function handleReset() {
    setResult(null);
    reset();
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground tracking-tight">
          Adjudicate Claim
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Submit a claim for real-time AI adjudication
        </p>
      </div>

      <AnimatePresence mode="wait">
        {!result ? (
          <motion.form
            key="form"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            onSubmit={handleSubmit(onSubmit)}
            className="rounded-lg border border-border bg-card p-6 space-y-5"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Field label="Member ID" error={errors.member_id?.message}>
                <input
                  {...register("member_id")}
                  placeholder="M-0001"
                  className={inputClass}
                />
              </Field>

              <Field label="Provider ID" error={errors.provider_id?.message}>
                <input
                  {...register("provider_id")}
                  placeholder="P-0001"
                  className={inputClass}
                />
              </Field>

              <Field
                label="Diagnosis Code (ICD-10)"
                error={errors.diagnosis_code?.message}
              >
                <input
                  {...register("diagnosis_code")}
                  placeholder="A09"
                  className={cn(inputClass, "font-mono tabular-nums")}
                />
              </Field>

              <Field
                label="Procedure Code"
                error={errors.procedure_code?.message}
              >
                <input
                  {...register("procedure_code")}
                  placeholder="99213"
                  className={cn(inputClass, "font-mono tabular-nums")}
                />
              </Field>

              <Field
                label="Claimed Amount"
                error={errors.claimed_amount?.message}
              >
                <input
                  {...register("claimed_amount")}
                  type="decimal"
                  step="0.01"
                  placeholder="0.00"
                  className={cn(inputClass, "tabular-nums")}
                />
              </Field>

              <Field
                label="Approved Tariff"
                error={errors.approved_tariff?.message}
              >
                <input
                  {...register("approved_tariff")}
                  type="decimal"
                  step="0.01"
                  placeholder="0.00"
                  className={cn(inputClass, "tabular-nums")}
                />
              </Field>

              <Field
                label="Date of Service"
                error={errors.date_of_service?.message}
              >
                <input
                  {...register("date_of_service")}
                  type="date"
                  className={inputClass}
                />
              </Field>

              <Field
                label="Provider Type"
                error={errors.provider_type?.message}
              >
                <select {...register("provider_type")} className={inputClass}>
                  <option value="">Select type…</option>
                  {[
                    "hospital",
                    "clinic",
                    "pharmacy",
                    "laboratory",
                    "specialist",
                  ].map((t) => (
                    <option key={t} value={t}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Location" error={errors.location?.message}>
                <input
                  {...register("location")}
                  placeholder="Nairobi"
                  className={inputClass}
                />
              </Field>

              <Field label="Member Age" error={errors.member_age?.message}>
                <input
                  {...register("member_age")}
                  type="numeric"
                  placeholder="35"
                  className={cn(inputClass, "tabular-nums")}
                />
              </Field>
            </div>

            <div className="pt-2 border-t border-border">
              <button
                type="submit"
                disabled={isPending}
                className={cn(
                  "flex items-center gap-2 h-10 px-6 rounded-lg text-sm font-semibold",
                  "bg-accent text-accent-foreground",
                  "hover:bg-accent/90 active:scale-[0.98]",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "transition-all duration-150",
                  "shadow-[0_0_20px_hsl(var(--accent)/0.2)]",
                )}
              >
                {isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Adjudicating…
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" strokeWidth={1.5} />
                    Adjudicate Claim
                  </>
                )}
              </button>
            </div>
          </motion.form>
        ) : (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div
              className={cn(
                "rounded-lg border p-5 flex items-center justify-between",
                result.decision === "Pass" &&
                  "border-emerald-500/30 bg-emerald-500/5",
                result.decision === "Flag" &&
                  "border-amber-500/30  bg-amber-500/5",
                result.decision === "Fail" &&
                  "border-red-500/30    bg-red-500/5",
              )}
            >
              <div className="flex items-center gap-3">
                {result.decision === "Pass" && (
                  <CheckCircle2
                    className="w-6 h-6 text-emerald-400"
                    strokeWidth={1.5}
                  />
                )}
                {result.decision === "Flag" && (
                  <AlertTriangle
                    className="w-6 h-6 text-amber-400"
                    strokeWidth={1.5}
                  />
                )}
                {result.decision === "Fail" && (
                  <XCircle className="w-6 h-6 text-red-400" strokeWidth={1.5} />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-base font-semibold text-foreground">
                      {result.decision === "Pass"
                        ? "Claim Approved"
                        : result.decision === "Flag"
                          ? "Claim Flagged for Review"
                          : "Claim Rejected"}
                    </p>
                    <DecisionBadge decision={result.decision} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 font-mono tabular-nums">
                    {result.claim_id}
                  </p>
                </div>
              </div>
              <div className="text-right shrink-0 ml-4">
                <RiskScore score={result.risk_score} size="lg" />
                <p className="text-[10px] text-muted-foreground mt-1 tabular-nums">
                  {formatDuration(result.processing_time_ms)}
                </p>
              </div>
            </div>

            {/* EOB */}
            {result.explanation_of_benefits && (
              <div className="rounded-lg border border-border bg-card p-5">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                  Explanation of Benefits
                </p>
                <p className="text-sm text-foreground leading-relaxed">
                  {result.explanation_of_benefits}
                </p>
              </div>
            )}

            {/* SHAP */}
            {result.feature_contributions && (
              <ShapChart contributions={result.feature_contributions} />
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleReset}
                className={cn(
                  "h-10 px-6 rounded-lg border border-border text-sm font-medium",
                  "text-muted-foreground hover:text-foreground hover:bg-muted",
                  "transition-all duration-150",
                )}
              >
                Adjudicate another
              </button>
              <a
                href={`/claims/${result.claim_id}`}
                className={cn(
                  "flex items-center gap-2 h-10 px-6 rounded-lg text-sm font-medium",
                  "bg-accent/10 text-accent border border-accent/20",
                  "hover:bg-accent/20 transition-all duration-150",
                )}
              >
                View full claim
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
