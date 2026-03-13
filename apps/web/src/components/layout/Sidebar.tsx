"use client";

import { useState, useEffect } from "react";
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
  ChevronRight,
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
  badge?: string;
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

export function Sidebar() {
  const { data: session } = useSession();
  const pathname = usePathname();
  const role = session?.user?.role ?? "viewer";

  const [pinned, setPinned] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("sidebar-pinned") === "true";
  });
  const [hovered, setHovered] = useState(false);

  const expanded = pinned || hovered;

  function togglePin() {
    const next = !pinned;
    setPinned(next);
    localStorage.setItem("sidebar-pinned", String(next));
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
      className={cn(
        "relative flex flex-col h-full shrink-0 overflow-hidden",
        "bg-[#0D0D0D] border-r border-white/[0.06]",
        "select-none z-20",
      )}
      aria-label="Main navigation"
    >
      <div className="flex items-center h-16 px-4 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 shrink-0">
          <Shield className="w-4 h-4 text-teal-400" strokeWidth={1.5} />
        </div>
        <AnimatePresence>
          {expanded && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="ml-3 text-sm font-semibold text-white tracking-tight font-['Syne',sans-serif] whitespace-nowrap"
            >
              Ginja<span className="text-teal-400">AI</span>
            </motion.span>
          )}
        </AnimatePresence>
      </div>

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
                "focus-visible:ring-2 focus-visible:ring-teal-400/60",
                active
                  ? "bg-teal-500/10 text-teal-400"
                  : "text-white/40 hover:text-white/80 hover:bg-white/[0.04]",
              )}
              aria-current={active ? "page" : undefined}
            >
              {active && (
                <motion.div
                  layoutId="active-pill"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-teal-400"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}

              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-transform duration-150",
                  "group-hover:scale-110",
                  active ? "text-teal-400" : "text-white/40",
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
                  className={cn(
                    "absolute left-full ml-3 px-2 py-1 rounded-md",
                    "bg-[#1A1A1A] border border-white/10 text-white text-xs",
                    "opacity-0 group-hover:opacity-100 pointer-events-none",
                    "transition-opacity duration-150 whitespace-nowrap z-50",
                    "shadow-xl",
                  )}
                >
                  {item.label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="px-2 pb-2">
        <div
          className={cn(
            "flex items-center h-9 rounded-lg px-2 gap-2",
            "border border-white/[0.04] bg-white/[0.02]",
          )}
        >
          <div className="relative shrink-0">
            <Activity className="w-4 h-4 text-white/20" strokeWidth={1.5} />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
          </div>
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[10px] text-white/30 whitespace-nowrap"
              >
                Engine online
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="px-2 pb-3 shrink-0 border-t border-white/[0.06] pt-2">
        <button
          onClick={togglePin}
          aria-label={pinned ? "Collapse sidebar" : "Pin sidebar open"}
          className={cn(
            "flex items-center h-9 w-full rounded-lg px-2 gap-3",
            "text-white/30 hover:text-white/60 hover:bg-white/[0.04]",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/60",
          )}
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
