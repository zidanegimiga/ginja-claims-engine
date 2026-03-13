/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Upload,
  FileText,
  X,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ChevronRight,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { cn, formatCurrency } from "@/lib/utils";
import { useToast } from "@/components/ui/Toast";
import apiClient from "@/lib/api-client";
import type { PdfExtractionResult, ClaimRequest, ProviderType } from "@/types";
import { useForm, Controller, type Resolver } from "react-hook-form";



//  Form schema
const schema = z.object({
  member_id: z.string().min(1, "Required"),
  provider_id: z.string().min(1, "Required"),
  diagnosis_code: z.string().min(1, "Required"),
  procedure_code: z.string().min(1, "Required"),
  claimed_amount: z.preprocess(
    (v) => parseFloat(String(v)),
    z.number().positive("Must be positive"),
  ),
  approved_tariff: z.preprocess(
    (v) => parseFloat(String(v)),
    z.number().positive("Must be positive"),
  ),
  date_of_service: z.string().min(1, "Required"),
  provider_type: z.enum([
    "hospital",
    "clinic",
    "pharmacy",
    "laboratory",
    "specialist",
  ]),
  location: z.string().min(1, "Required"),
  member_age: z.preprocess(
    (v) => (v === "" || v === undefined ? undefined : parseFloat(String(v))),
    z.number().min(0).max(120).optional(),
  ),
  invoice_number: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const PROVIDER_TYPES: ProviderType[] = [
  "hospital",
  "clinic",
  "pharmacy",
  "laboratory",
  "specialist",
];

//  Field component
function Field({
  label,
  error,
  children,
  ai,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
  ai?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </label>
        {ai && (
          <span className="flex items-center gap-0.5 text-[10px] text-accent">
            <Sparkles className="w-2.5 h-2.5" strokeWidth={1.5} />
            AI filled
          </span>
        )}
      </div>
      {children}
      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  );
}

const INPUT = cn(
  "w-full h-9 px-3 rounded-lg text-sm bg-muted/40 border border-border",
  "text-foreground placeholder:text-muted-foreground",
  "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60",
  "transition-all duration-150",
);

//  Upload states
type UploadState =
  | "idle"
  | "uploading"
  | "extracting"
  | "review"
  | "submitting"
  | "done";

export default function UploadPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const toast = useToast();

  const [state, setState] = useState<UploadState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [documentKey, setDocumentKey] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<PdfExtractionResult | null>(
    null,
  );
  const [aiFields, setAiFields] = useState<Set<string>>(new Set());

  const apiKey = (session?.user as any)?.api_key ?? "";

const { register, handleSubmit, reset, control, formState: { errors } } =
  useForm<FormValues, unknown, FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
  });

  //  Upload to Extract pipeline
  async function handleUploadAndExtract(pdf: File) {
    try {
      // 1. Upload to R2
      setState("uploading");
      const formData = new FormData();
      formData.append("file", pdf);

      const { data: uploaded } = await apiClient.post(
        "/claims/upload",
        formData,
        {
          headers: {
            "X-API-Key": apiKey,
            "Content-Type": "multipart/form-data",
          },
        },
      );
      setDocumentKey(uploaded.key);

      // 2. Extract data from PDF
      setState("extracting");
      const { data: extracted } = await apiClient.post<PdfExtractionResult>(
        "/claims/extract",
        { document_key: uploaded.key },
        { headers: { "X-API-Key": apiKey } },
      );
      setExtraction(extracted);

      // 3. Pre-fill form with extracted data
      const d = extracted.extracted_data;
      const filled = new Set<string>();

      const values: Partial<FormValues> = {};
      const map: [keyof typeof d, keyof FormValues][] = [
        ["member_id", "member_id"],
        ["provider_id", "provider_id"],
        ["diagnosis_code", "diagnosis_code"],
        ["procedure_code", "procedure_code"],
        ["claimed_amount", "claimed_amount"],
        ["approved_tariff", "approved_tariff"],
        ["date_of_service", "date_of_service"],
        ["provider_type", "provider_type"],
        ["location", "location"],
        ["member_age", "member_age"],
      ];

      map.forEach(([src, dst]) => {
        const val = d[src];
        if (val !== undefined && val !== null) {
          (values as any)[dst] = val;
          filled.add(dst);
        }
      });

      reset(values);
      setAiFields(filled);
      setState("review");

      if (extracted.extraction_warnings.length > 0) {
        toast.warning(
          "Extraction warnings",
          extracted.extraction_warnings.join(". "),
        );
      }
    } catch (err: any) {
      console.error(err);
      toast.error(
        "Upload failed",
        err?.response?.data?.detail ?? "Could not process the PDF.",
      );
      setState("idle");
      setFile(null);
    }
  }

  //  Drop handler
  const onDrop = useCallback(
    async (accepted: File[]) => {
      const pdf = accepted[0];
      if (!pdf) return;
      setFile(pdf);
      await handleUploadAndExtract(pdf);
    },
    [apiKey],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
    disabled: state !== "idle",
  });

  //  Submit adjudication
  async function onSubmit(values: FormValues) {
    if (!documentKey) return;
    setState("submitting");

    try {
      const payload: ClaimRequest = {
        ...values,
        source: {
          source_type: "pdf",
          documents: [
            {
              document_key: documentKey,
              document_name: file?.name ?? "upload.pdf",
              document_type: "pdf",
              uploaded_by: (session?.user as any)?.id ?? "unknown",
              uploaded_at: new Date().toISOString(),
              extraction_confidence: extraction?.confidence,
              extraction_provider: extraction?.provider_name,
            },
          ],
        },
      };

      const { data: result } = await apiClient.post(
        "/claims/adjudicate",
        payload,
        { headers: { "X-API-Key": apiKey } },
      );

      setState("done");
      toast.success(
        "Claim adjudicated",
        `${result.claim_id} → ${result.decision}`,
      );

      setTimeout(() => {
        router.push(`/claims/${result.claim_id}`);
      }, 1500);
    } catch (err: any) {
      console.error(err);
      toast.error(
        "Adjudication failed",
        err?.response?.data?.detail ?? "Something went wrong.",
      );
      setState("review");
    }
  }

  //  Reset
  function handleReset() {
    setState("idle");
    setFile(null);
    setDocumentKey(null);
    setExtraction(null);
    setAiFields(new Set());
    reset({});
  }

  //  Render
  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1
            className="text-xl font-semibold text-foreground tracking-tight"
            style={{ fontFamily: "var(--font-syne)" }}
          >
            Upload Claim
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Upload a PDF claim form — fields are extracted automatically
          </p>
        </div>
        {state !== "idle" && state !== "done" && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
            Start over
          </button>
        )}
      </div>

      {/* Drop zone */}
      <AnimatePresence mode="wait">
  {state === "idle" && (
    <motion.div
      key="dropzone"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
    >
      <div
        {...getRootProps()}
        className={cn(
          "relative flex flex-col items-center justify-center",
          "h-48 rounded-xl border-2 border-dashed cursor-pointer",
          "transition-all duration-200",
          isDragActive
            ? "border-accent bg-accent/5 scale-[1.01]"
            : "border-border hover:border-accent/50 hover:bg-muted/30"
        )}
      >
        <input {...getInputProps()} />
        <div className={cn(
          "flex items-center justify-center w-12 h-12 rounded-xl mb-3",
          "bg-accent/10 border border-accent/20",
          isDragActive && "scale-110 animate-pulse"
        )}>
          <Upload className="w-5 h-5 text-accent" strokeWidth={1.5} />
        </div>
        <p className="text-sm font-medium text-foreground">
          {isDragActive ? "Drop it here" : "Drag & drop a PDF claim form"}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          or click to browse — max 20 MB
        </p>
      </div>
    </motion.div>
  )}

        {/* Processing states */}
        {(state === "uploading" || state === "extracting") && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex flex-col items-center justify-center h-48 rounded-xl border border-border bg-card gap-4"
          >
            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-accent" strokeWidth={1.5} />
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-background border border-border flex items-center justify-center">
                <Loader2 className="w-3 h-3 text-accent animate-spin" />
              </div>
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                {state === "uploading"
                  ? "Uploading to secure storage…"
                  : "Extracting claim data…"}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {file?.name}
              </p>
            </div>
            <div className="flex gap-2">
              {(["uploading", "extracting"] as const).map((s) => (
                <div
                  key={s}
                  className={cn(
                    "h-1 w-16 rounded-full transition-colors duration-300",
                    state === s
                      ? "bg-accent animate-pulse"
                      : state === "extracting" && s === "uploading"
                        ? "bg-accent"
                        : "bg-muted",
                  )}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Extraction summary */}
      {(state === "review" || state === "submitting" || state === "done") &&
        extraction && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "flex items-start gap-3 p-4 rounded-xl border",
              extraction.is_valid
                ? "bg-emerald-500/5 border-emerald-500/20"
                : "bg-amber-500/5 border-amber-500/20",
            )}
          >
            {extraction.is_valid ? (
              <CheckCircle2
                className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0"
                strokeWidth={1.5}
              />
            ) : (
              <AlertTriangle
                className="w-4 h-4 text-amber-500 mt-0.5 shrink-0"
                strokeWidth={1.5}
              />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">
                  {extraction.is_valid
                    ? "Extraction successful"
                    : "Extraction incomplete"}
                </p>
                <span className="text-xs text-muted-foreground font-mono">
                  {(extraction.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {file?.name} · {aiFields.size} fields populated by{" "}
                {extraction.provider_name}
              </p>
              {extraction.validation_errors.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {extraction.validation_errors.map((e, i) => (
                    <li key={i} className="text-xs text-amber-500">
                      · {e}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}

      {/* Review & submit form */}
      {(state === "review" || state === "submitting") && (
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
>
  <form
    onSubmit={handleSubmit(onSubmit)}
    className="space-y-5"
  >
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h2 className="text-sm font-semibold text-foreground">
                Review extracted data
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Verify and correct any fields before submitting
              </p>
            </div>

            <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field
                label="Member ID"
                error={errors.member_id?.message}
                ai={aiFields.has("member_id")}
              >
                <input
                  {...register("member_id")}
                  className={INPUT}
                  placeholder="MEM-00001"
                />
              </Field>

              <Field
                label="Provider ID"
                error={errors.provider_id?.message}
                ai={aiFields.has("provider_id")}
              >
                <input
                  {...register("provider_id")}
                  className={INPUT}
                  placeholder="PRV-00001"
                />
              </Field>

              <Field
                label="Diagnosis Code"
                error={errors.diagnosis_code?.message}
                ai={aiFields.has("diagnosis_code")}
              >
                <input
                  {...register("diagnosis_code")}
                  className={INPUT}
                  placeholder="J06.9"
                />
              </Field>

              <Field
                label="Procedure Code"
                error={errors.procedure_code?.message}
                ai={aiFields.has("procedure_code")}
              >
                <input
                  {...register("procedure_code")}
                  className={INPUT}
                  placeholder="99213"
                />
              </Field>

              <Field
                label="Claimed Amount (KES)"
                error={errors.claimed_amount?.message}
                ai={aiFields.has("claimed_amount")}
              >
                <input
                  {...register("claimed_amount")}
                  type="number"
                  className={INPUT}
                  placeholder="5000"
                />
              </Field>

              <Field
                label="Approved Tariff (KES)"
                error={errors.approved_tariff?.message}
                ai={aiFields.has("approved_tariff")}
              >
                <input
                  {...register("approved_tariff")}
                  type="number"
                  className={INPUT}
                  placeholder="4800"
                />
              </Field>

              <Field
                label="Date of Service"
                error={errors.date_of_service?.message}
                ai={aiFields.has("date_of_service")}
              >
                <input
                  {...register("date_of_service")}
                  type="date"
                  className={INPUT}
                />
              </Field>

              <Field
                label="Provider Type"
                error={errors.provider_type?.message}
                ai={aiFields.has("provider_type")}
              >
                <Controller
                  name="provider_type"
                  control={control}
                  render={({ field }) => (
                    <select {...field} className={INPUT}>
                      <option value="">Select type</option>
                      {PROVIDER_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                  )}
                />
              </Field>

              <Field
                label="Location"
                error={errors.location?.message}
                ai={aiFields.has("location")}
              >
                <input
                  {...register("location")}
                  className={INPUT}
                  placeholder="Nairobi"
                />
              </Field>

              <Field
                label="Member Age"
                error={errors.member_age?.message}
                ai={aiFields.has("member_age")}
              >
                <input
                  {...register("member_age")}
                  type="number"
                  className={INPUT}
                  placeholder="35"
                />
              </Field>

              <Field
                label="Invoice Number"
                error={errors.invoice_number?.message}
              >
                <input
                  {...register("invoice_number")}
                  className={INPUT}
                  placeholder="INV-2026-001"
                />
              </Field>

              <Field label="Notes" error={errors.notes?.message}>
                <input
                  {...register("notes")}
                  className={INPUT}
                  placeholder="Optional notes"
                />
              </Field>
            </div>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleReset}
              className="h-10 px-4 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={state === "submitting"}
              className={cn(
                "flex items-center gap-2 h-10 px-6 rounded-lg text-sm font-semibold",
                "bg-accent text-accent-foreground",
                "hover:bg-accent/90 active:scale-[0.98]",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-all duration-150",
                "shadow-[0_0_20px_hsl(var(--accent)/0.15)]",
              )}
            >
              {state === "submitting" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Adjudicating…
                </>
              ) : (
                <>
                  <ChevronRight className="w-4 h-4" strokeWidth={2} />
                  Submit for adjudication
                </>
              )}
            </button>
          </div>
        </form>
        </motion.div>
      )}

      {/* Done state */}
      {state === "done" && (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center h-48 rounded-xl border border-emerald-500/20 bg-emerald-500/5 gap-3"
        >
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <CheckCircle2
              className="w-5 h-5 text-emerald-500"
              strokeWidth={1.5}
            />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">
              Claim submitted successfully
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Redirecting to claim detail…
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
