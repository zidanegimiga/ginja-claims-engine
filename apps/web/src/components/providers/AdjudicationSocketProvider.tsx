"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { useSession } from "next-auth/react";
import { useToast } from "@/components/ui/Toast";
import { AdjudicationResult } from "@/types";

type JobStatus = "queued" | "processing" | "done" | "error";

export interface AdjudicationJob {
  jobId: string;
  status: JobStatus;
  label: string;
  result?: AdjudicationResult;
  error?: string;
}

interface SocketContextValue {
  jobs: AdjudicationJob[];
  submitJob: (payload: object, label: string) => string;
  clearJob: (jobId: string) => void;
  isConnected: boolean;
}

const SocketContext = createContext<SocketContextValue | null>(null);

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws").replace(
    "/api/v1",
    "",
  ) ??
  "ws://localhost:8000";

export function AdjudicationSocketProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session } = useSession();
  const toast = useToast();
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setConn] = useState(false);
  const [jobs, setJobs] = useState<AdjudicationJob[]>([]);
  const pendingRef = useRef<Record<string, string>>({});

  const apiKey = session?.user?.api_key;

  useEffect(() => {
    if (!apiKey) return;

    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const ws = new WebSocket(`${WS_URL}/ws/adjudicate?api_key=${apiKey}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConn(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            job_id: string;
            status: JobStatus;
            result?: AdjudicationResult;
            error?: string;
          };

          const label = pendingRef.current[msg.job_id] ?? "Claim";

          setJobs((prev) => {
            const existing = prev.findIndex((j) => j.jobId === msg.job_id);
            const updated: AdjudicationJob = {
              jobId: msg.job_id,
              status: msg.status,
              label,
              result: msg.result,
              error: msg.error,
            };
            if (existing >= 0) {
              const next = [...prev];
              next[existing] = updated;
              return next;
            }
            return [...prev, updated];
          });

          if (msg.status === "done" && msg.result) {
            const decision = msg.result.decision;
            const toastType =
              decision === "Pass"
                ? "success"
                : decision === "Flag"
                  ? "warning"
                  : "error";
            toast[toastType](
              `${label} — ${decision}`,
              `Risk score: ${(msg.result.risk_score * 100).toFixed(0)}%`,
            );
            delete pendingRef.current[msg.job_id];
          }

          if (msg.status === "error") {
            toast.error(`${label} failed`, msg.error);
            delete pendingRef.current[msg.job_id];
          }
        } catch {}
      };

      ws.onclose = () => {
        setConn(false);
        retryTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      clearTimeout(retryTimeout);
      wsRef.current?.close();
    };
  }, [apiKey]);

  const submitJob = useCallback(
    (payload: object, label: string): string => {
      const jobId = `job-${Date.now()}-${Math.random().toString(36).slice(2)}`;

      pendingRef.current[jobId] = label;

      setJobs((prev) => [...prev, { jobId, status: "queued", label }]);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ job_id: jobId, ...payload }));
        toast.info(`${label} queued`, "Processing in background…");
      } else {
        toast.warning("WebSocket offline", "Falling back to REST API");
      }

      return jobId;
    },
    [toast],
  );

  const clearJob = useCallback((jobId: string) => {
    setJobs((prev) => prev.filter((j) => j.jobId !== jobId));
  }, []);

  return (
    <SocketContext.Provider value={{ jobs, submitJob, clearJob, isConnected }}>
      {children}
    </SocketContext.Provider>
  );
}

export function useAdjudicationSocket() {
  const ctx = useContext(SocketContext);
  if (!ctx)
    throw new Error(
      "useAdjudicationSocket must be used inside AdjudicationSocketProvider",
    );
  return ctx;
}
