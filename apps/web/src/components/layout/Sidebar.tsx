"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useSession } from "next-auth/react";
import {
  LayoutDashboard,
  FileSearch,
  Zap,
  Upload,
  Users,
  BarChart3,
  Settings,
  Shield,
  Activity,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  roles?: string[];
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/claims", label: "Claims", icon: FileSearch },
  {
    href: "/adjudicate",
    label: "Adjudicate",
    icon: Zap,
    roles: ["admin", "claims_officer"],
  },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/providers", label: "Providers", icon: Users, roles: ["admin"] },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

const COLLAPSED_W = 64;
const EXPANDED_W = 220;

interface SidebarProps {
  initialPinned?: boolean;
}

export function Sidebar({ initialPinned = false }: SidebarProps) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const role = session?.user?.role ?? "viewer";

  const [pinned, setPinned] = useState(initialPinned);
  const [hovered, setHovered] = useState(false);

  const expanded = pinned || hovered;

  // No useEffect — state comes from server via cookie
  function togglePin() {
    const next = !pinned;
    setPinned(next);
    document.cookie = `sidebar-pinned=${next}; path=/; max-age=31536000; SameSite=Lax`;
  }

  const visibleNav = NAV.filter(
    (item) => !item.roles || item.roles.includes(role),
  );

  return (
    <motion.aside
      initial={false}
      animate={{ width: expanded ? EXPANDED_W : COLLAPSED_W }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative flex flex-col h-full shrink-0 overflow-hidden bg-[var(--sidebar)] border-r border-[var(--sidebar-border)] select-none z-20"
      aria-label="Main navigation"
    >
      {/* ── Logo ─────────────────────────────────────────────────── */}
      <div className="flex items-center h-16 px-4 border-b border-[var(--sidebar-border)] shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 shrink-0">
          <Shield className="w-4 h-4 text-accent" strokeWidth={1.5} />
        </div>
        <AnimatePresence>
          {expanded && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="ml-3 text-sm font-semibold text-foreground tracking-tight whitespace-nowrap"
              style={{ fontFamily: "var(--font-syne)" }}
            >
              Ginja<span className="text-accent">AI</span>
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* ── Nav ──────────────────────────────────────────────────── */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-hidden">
        {visibleNav.map((item) => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center h-9 rounded-lg px-2",
                "transition-colors duration-150 outline-none",
                "focus-visible:ring-2 focus-visible:ring-accent/60",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
              aria-current={active ? "page" : undefined}
            >
              {active && (
                <motion.div
                  layoutId="active-pill"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-accent"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}

              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-transform duration-150 group-hover:scale-110",
                  active ? "text-accent" : "text-muted-foreground",
                )}
                strokeWidth={1.5}
              />

              <AnimatePresence>
                {expanded && (
                  <motion.span
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }}
                    transition={{ duration: 0.12 }}
                    className="ml-3 text-xs font-medium whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>

              {!expanded && (
                <div
                  role="tooltip"
                  className="absolute left-full ml-3 px-2 py-1 rounded-md bg-card border border-border text-foreground text-xs opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap z-50 shadow-xl"
                >
                  {item.label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Engine status ────────────────────────────────────────── */}
      <div className="px-2 pb-2">
        <div className="flex items-center h-9 rounded-lg px-2 gap-2 border border-border bg-muted/40">
          <div className="relative shrink-0">
            <Activity
              className="w-4 h-4 text-muted-foreground"
              strokeWidth={1.5}
            />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          </div>
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[10px] text-muted-foreground whitespace-nowrap"
              >
                Engine online
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Pin toggle ───────────────────────────────────────────── */}
      <div className="px-2 pb-3 shrink-0 border-t border-[var(--sidebar-border)] pt-2">
        <button
          onClick={togglePin}
          aria-label={pinned ? "Collapse sidebar" : "Pin sidebar open"}
          className="flex items-center h-9 w-full rounded-lg px-2 gap-3 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
        >
          {pinned ? (
            <PanelLeftClose className="w-4 h-4 shrink-0" strokeWidth={1.5} />
          ) : (
            <PanelLeftOpen className="w-4 h-4 shrink-0" strokeWidth={1.5} />
          )}
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-xs whitespace-nowrap"
              >
                {pinned ? "Unpin sidebar" : "Pin sidebar"}
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
}
