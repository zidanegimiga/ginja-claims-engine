import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { Decision } from "@/types";

const CURRENCY_LOCALES: Record<string, string> = {
  KES: "en-KE",
  RWF: "rw-RW",
  UGX: "en-UG",
  TZS: "en-TZ",
  USD: "en-US",
  EUR: "en-DE",
  GBP: "en-GB",
};

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

//  Decision helpers
export function getDecisionColor(decision: Decision): string {
  return {
    Pass: "text-success",
    Flag: "text-warning",
    Fail: "text-destructive",
  }[decision];
}

export function getDecisionBadgeClass(decision: Decision): string {
  return {
    Pass: "bg-success/10 text-success border-success/20",
    Flag: "bg-warning/10 text-warning border-warning/20",
    Fail: "bg-destructive/10 text-destructive border-destructive/20",
  }[decision];
}

export function getRiskColor(score: number): string {
  if (score < 0.3) return "text-success";
  if (score < 0.6) return "text-warning";
  return "text-destructive";
}

export function getRiskBarColor(score: number): string {
  if (score < 0.3) return "bg-success";
  if (score < 0.6) return "bg-warning";
  return "bg-destructive";
}

// Formatting
export function formatCurrency(
  amount: number | null | undefined,
  currency: string = "KES",
): string {
  if (amount === null || amount === undefined || isNaN(amount)) return "—";

  const locale = CURRENCY_LOCALES[currency] ?? "en-KE";

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function parseDate(dateString: string | null | undefined): Date | null {
  if (!dateString) return null;
  const d = new Date(dateString);
  return isNaN(d.getTime()) ? null : d;
}

function getUserLocale(): string {
  if (typeof navigator !== "undefined") return navigator.language;
  return "en-KE"; // SSR fallback
}

export function formatDate(dateString: string | null | undefined): string {
  const d = parseDate(dateString);
  if (!d) return "—";

  return new Intl.DateTimeFormat(getUserLocale(), {
    day:   "2-digit",
    month: "short",
    year:  "numeric",
  }).format(d);
}

export function formatDateTime(dateString: string | null | undefined): string {
  const d = parseDate(dateString);
  if (!d) return "—";

  return new Intl.DateTimeFormat(getUserLocale(), {
    day:    "2-digit",
    month:  "short",
    year:   "numeric",
    hour:   "2-digit",
    minute: "2-digit",
  }).format(d);
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatPercent(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

// Truncation
export function truncateId(id: string, chars: number = 8): string {
  if (!id) return "not_present";

  if (id.length <= chars) return id;
  return `${id.slice(0, chars)}…`;
}
