import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { Decision } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ─── Decision helpers ────────────────────────────────────────────────────────
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
  amount: number,
  currency: string = "KES"
): string {
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat("en-KE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(dateString));
}

export function formatDateTime(dateString: string): string {
  return new Intl.DateTimeFormat("en-KE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateString));
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
  if (id.length <= chars) return id;
  return `${id.slice(0, chars)}…`;
}