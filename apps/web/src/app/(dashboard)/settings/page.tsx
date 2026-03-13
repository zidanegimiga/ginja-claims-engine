/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { motion } from "framer-motion";
import { useTheme } from "next-themes";
import {
  User,
  Shield,
  Bell,
  Palette,
  Key,
  Check,
  Loader2,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/Toast";
import Image from "next/image";

const CARD = "rounded-xl border border-border bg-card p-6";

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={CARD}
    >
      <div className="mb-5 pb-4 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      {children}
    </motion.div>
  );
}

function Row({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <div>
        <p className="text-sm text-foreground">{label}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
      <div className="ml-4 shrink-0">{children}</div>
    </div>
  );
}

function Toggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={value}
      onClick={() => onChange(!value)}
      className={cn(
        "relative w-9 h-5 rounded-full transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
        value ? "bg-accent" : "bg-muted",
      )}
    >
      <motion.span
        animate={{ x: value ? 2 : -16 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm"
      />
    </button>
  );
}

const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: [
    "View claims",
    "Adjudicate claims",
    "Upload documents",
    "Manage providers",
    "View analytics",
    "Manage users",
    "System settings",
  ],
  claims_officer: [
    "View claims",
    "Adjudicate claims",
    "Upload documents",
    "View analytics",
  ],
  viewer: ["View claims", "View analytics"],
};

export default function SettingsPage() {
  const { data: session } = useSession();
  const { theme, setTheme } = useTheme();
  const toast = useToast();

  const [mounted, setMounted] = useState(false);
useEffect(() => setMounted(true), []);

  const user = session?.user;
  const role = user?.role ?? "viewer";

  const [notifications, setNotifications] = useState({
    adjudication_complete: true,
    high_risk_flagged: true,
    system_alerts: false,
    weekly_report: true,
  });

  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    toast.success("Settings saved", "Your preferences have been updated.");
  }

  return (
    <div className="space-y-5 max-w-2xl">
      {/*  Header  */}
      <div>
        <h1
          className="text-xl font-semibold text-foreground tracking-tight"
          style={{ fontFamily: "var(--font-syne)" }}
        >
          Settings
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Manage your account and preferences
        </p>
      </div>

      {/*  Profile  */}
      <Section title="Profile" description="Your account information">
        <div className="flex items-center gap-4 mb-5">
          {user?.image ? (
            <Image
              src={user.image}
              alt={user.name}
              width={56}
              height={56}
              className="w-14 h-14 rounded-full object-cover ring-2 ring-border"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center">
              <span className="text-lg font-semibold text-accent font-mono">
                {user?.name
                  ?.split(" ")
                  .map((n: string) => n[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase() ?? "?"}
              </span>
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-foreground">
              {user?.name ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              {user?.email ?? "—"}
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5 font-mono tabular-nums">
              ID: {user?.id ?? "—"}
            </p>
          </div>
        </div>

        <Row label="Full name">
          <p className="text-sm text-muted-foreground">{user?.name ?? "—"}</p>
        </Row>
        <Row label="Email address">
          <p className="text-sm text-muted-foreground">{user?.email ?? "—"}</p>
        </Row>
        <Row label="Account type" description="Set by your administrator">
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border",
              role === "admin" &&
                "text-amber-500 bg-amber-500/10 border-amber-500/20",
              role === "claims_officer" &&
                "text-accent bg-accent/10 border-accent/20",
              role === "viewer" &&
                "text-muted-foreground bg-muted border-border",
            )}
          >
            <Shield className="w-2.5 h-2.5" strokeWidth={2} />
            {role === "admin"
              ? "Administrator"
              : role === "claims_officer"
                ? "Claims Officer"
                : "Viewer"}
          </span>
        </Row>
      </Section>

      {/*  Appearance  */}
      <Section
        title="Appearance"
        description="Customise the look of the application"
      >
        <Row label="Theme" description="Switch between light and dark mode">
          <div className="flex items-center gap-2 p-1 rounded-lg border border-border bg-muted/30">
{(["light", "dark"] as const).map((t) => (
  <button
    key={t}
    onClick={() => setTheme(t)}
    className={cn(
      "flex items-center gap-1.5 h-7 px-3 rounded-md text-xs font-medium transition-all duration-150",
      mounted && theme === t
        ? "bg-card text-foreground shadow-sm"
        : "text-muted-foreground hover:text-foreground"
    )}
  >
    {t === "light"
      ? <Sun  className="w-3 h-3" strokeWidth={1.5} />
      : <Moon className="w-3 h-3" strokeWidth={1.5} />
    }
    {t.charAt(0).toUpperCase() + t.slice(1)}
  </button>
))}
          </div>
        </Row>
      </Section>

      <Section
        title="Notifications"
        description="Choose what you want to be notified about"
      >
        {(
          Object.entries(notifications) as [
            keyof typeof notifications,
            boolean,
          ][]
        ).map(([key, val]) => (
          <Row
            key={key}
            label={key
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
          >
            <Toggle
              value={val}
              onChange={(v) =>
                setNotifications((prev) => ({ ...prev, [key]: v }))
              }
            />
          </Row>
        ))}
      </Section>

      <Section
        title="Permissions"
        description="What your role allows you to do"
      >
        <div className="space-y-2">
          {(ROLE_PERMISSIONS[role] ?? []).map((permission) => (
            <div key={permission} className="flex items-center gap-2">
              <Check
                className="w-3.5 h-3.5 text-accent shrink-0"
                strokeWidth={2}
              />
              <span className="text-sm text-muted-foreground">
                {permission}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className={cn(
            "flex items-center gap-2 h-10 px-6 rounded-lg text-sm font-semibold",
            "bg-accent text-accent-foreground",
            "hover:bg-accent/90 active:scale-[0.98]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-all duration-150",
            "shadow-[0_0_20px_hsl(var(--accent)/0.15)]",
          )}
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <Check className="w-4 h-4" strokeWidth={2} />
              Save changes
            </>
          )}
        </button>
      </div>
    </div>
  );
}
