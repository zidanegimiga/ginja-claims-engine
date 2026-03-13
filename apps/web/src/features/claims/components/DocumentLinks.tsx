"use client";

import { useState } from "react";
import { FileText, ExternalLink, Loader2, GitMerge } from "lucide-react";
import { ClaimSource } from "@/types";
import { fetchDocumentUrl } from "@/lib/queries";
import { cn, formatPercent } from "@/lib/utils";

interface DocumentLinksProps {
  claimId: string;
  source: ClaimSource;
}

const SOURCE_LABELS: Record<string, string> = {
  pdf: "PDF Upload",
  csv: "CSV Import",
  json: "JSON Import",
  api: "REST API",
  manual: "Manual Entry",
};

const DOC_LABELS: Record<number, string> = {
  0: "Primary Document",
  1: "Secondary Document",
};

export function DocumentLinks({ claimId, source }: DocumentLinksProps) {
  const [loading, setLoading] = useState<number | null>(null);

  async function openDocument(index: 0 | 1) {
    setLoading(index);
    try {
      const url = await fetchDocumentUrl(claimId, index);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      alert("Could not load document. It may have been deleted.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-foreground">
          Source & Documents
        </h2>
        <span className="text-[11px] px-2 py-0.5 rounded-md bg-muted border border-border text-muted-foreground">
          {SOURCE_LABELS[source.source_type] ?? source.source_type}
        </span>
      </div>

      {source.documents && source.documents.length > 0 ? (
        <div className="space-y-2">
          {source.documents.map((doc, i) => (
            <div
              key={doc.document_key}
              className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex items-center justify-center w-8 h-8 rounded-md bg-accent/10 border border-accent/20 shrink-0">
                  <FileText className="w-4 h-4 text-accent" strokeWidth={1.5} />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                    {DOC_LABELS[i]}
                  </p>
                  <p className="text-sm text-foreground truncate">
                    {doc.document_name}
                  </p>
                  {doc.extraction_confidence !== undefined && (
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      Extraction confidence:{" "}
                      {formatPercent(doc.extraction_confidence)}
                      {doc.extraction_provider &&
                        ` · ${doc.extraction_provider}`}
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => openDocument(i as 0 | 1)}
                disabled={loading === i}
                className={cn(
                  "flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border",
                  "text-xs text-muted-foreground hover:text-foreground hover:bg-muted",
                  "transition-all duration-150 shrink-0 ml-3",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
              >
                {loading === i ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <ExternalLink className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
                View
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No documents attached to this claim.
        </p>
      )}

      {source.cross_reference_score !== undefined &&
        source.documents?.length === 2 && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2 mb-2">
              <GitMerge
                className="w-3.5 h-3.5 text-muted-foreground"
                strokeWidth={1.5}
              />
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                Cross-reference Score
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    source.cross_reference_score > 0.7
                      ? "bg-emerald-400"
                      : source.cross_reference_score > 0.4
                        ? "bg-amber-400"
                        : "bg-red-400",
                  )}
                  style={{ width: `${source.cross_reference_score * 100}%` }}
                />
              </div>
              <span className="text-sm font-mono tabular-nums text-foreground">
                {formatPercent(source.cross_reference_score)}
              </span>
            </div>
            {source.cross_reference_warnings?.map((w, i) => (
              <p key={i} className="text-[11px] text-warning mt-1.5">
                ⚠ {w}
              </p>
            ))}
          </div>
        )}
    </div>
  );
}
