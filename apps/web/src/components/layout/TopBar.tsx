/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { useTheme } from "next-themes";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sun,
  Moon,
  Bell,
  ChevronDown,
  LogOut,
  User,
  Settings,
  Shield,
  Copy,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";

function Avatar({
  name,
  image,
}: {
  name?: string | null;
  image?: string | null;
}) {
  if (image) {
    return (
      <Image
        src={image}
        alt={name ?? "User"}
        width={56}
        height={56}
        className="w-7 h-7 rounded-full object-cover ring-1 ring-border"
      />
    );
  }
  const initials =
    name
      ?.split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() ?? "?";

  return (
    <div className="w-7 h-7 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
      <span className="text-[10px] font-semibold text-accent font-mono">
        {initials}
      </span>
    </div>
  );
}

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  claims_officer: "Claims Officer",
  viewer: "Viewer",
};

const ROLE_COLORS: Record<string, string> = {
  admin: "text-amber-500  bg-amber-500/10  border-amber-500/20",
  claims_officer: "text-accent     bg-accent/10     border-accent/20",
  viewer: "text-muted-foreground bg-muted   border-border",
};

export function TopBar() {
  const { data: session } = useSession();
  const { theme, setTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [mounted, setMounted] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const user = session?.user;
  const role = user?.role ?? "viewer";

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  useEffect(() => {
    function handle(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, []);

  async function copyUserId() {
    if (!user?.id) return;
    await navigator.clipboard.writeText(user.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <header
      className={cn(
        "h-16 flex items-center justify-between px-6 shrink-0 z-10",
        "border-b border-[var(--sidebar-border)]",
        "bg-[var(--topbar)]/80 backdrop-blur-md",
      )}
    >
      <div className="flex items-center gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse shrink-0" />
        <span className="text-xs text-muted-foreground font-mono tabular-nums">
          {new Date().toLocaleDateString("en-KE", {
            weekday: "short",
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
          className={cn(
            "flex items-center justify-center w-8 h-8 rounded-lg",
            "text-muted-foreground hover:text-foreground hover:bg-muted",
            "transition-all duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
          )}
        >
          {mounted && (
            <AnimatePresence mode="wait" initial={false}>
              {theme === "dark" ? (
                <motion.div
                  key="sun"
                  initial={{ rotate: -90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: 90, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  <Sun className="w-4 h-4" strokeWidth={1.5} />
                </motion.div>
              ) : (
                <motion.div
                  key="moon"
                  initial={{ rotate: 90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: -90, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  <Moon className="w-4 h-4" strokeWidth={1.5} />
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </button>

        {/* Notifications */}
        <button
          aria-label="Notifications"
          className={cn(
            "relative flex items-center justify-center w-8 h-8 rounded-lg",
            "text-muted-foreground hover:text-foreground hover:bg-muted",
            "transition-all duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
          )}
        >
          <Bell className="w-4 h-4" strokeWidth={1.5} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-accent" />
        </button>

        {/* Divider */}
        <div className="w-px h-5 bg-border mx-1" aria-hidden />

        {/* Profile menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-haspopup="true"
            aria-label="Profile menu"
            className={cn(
              "flex items-center gap-2 h-8 pl-1 pr-2 rounded-lg",
              "hover:bg-muted transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
            )}
          >
            <Avatar name={user?.name} image={user?.image} />
            <div className="text-left hidden sm:block">
              <p className="text-xs font-medium text-foreground leading-tight max-w-[120px] truncate">
                {user?.name ?? user?.email ?? "User"}
              </p>
              <p className="text-[10px] text-muted-foreground leading-tight">
                {ROLE_LABELS[role] ?? role}
              </p>
            </div>
            <motion.div
              animate={{ rotate: menuOpen ? 180 : 0 }}
              transition={{ duration: 0.15 }}
            >
              <ChevronDown
                className="w-3 h-3 text-muted-foreground"
                strokeWidth={2}
              />
            </motion.div>
          </button>

          {/* Dropdown */}
          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.12, ease: "easeOut" }}
                className={cn(
                  "absolute right-0 top-full mt-2 w-64",
                  "bg-card border border-border rounded-xl",
                  "shadow-2xl shadow-black/20 overflow-hidden z-50",
                )}
                role="menu"
                aria-label="User menu"
              >
                {/* User info */}
                <div className="px-4 py-3 border-b border-border">
                  <div className="flex items-center gap-3">
                    <Avatar name={user?.name} image={user?.image} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground truncate">
                        {user?.name ?? "User"}
                      </p>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {user?.email}
                      </p>
                    </div>
                  </div>

                  {/* Role badge + copy ID */}
                  <div className="mt-2.5 flex items-center justify-between">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md",
                        "text-[10px] font-medium border",
                        ROLE_COLORS[role],
                      )}
                    >
                      <Shield className="w-2.5 h-2.5" strokeWidth={2} />
                      {ROLE_LABELS[role] ?? role}
                    </span>

                    <button
                      onClick={copyUserId}
                      className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                      aria-label="Copy user ID"
                    >
                      {copied ? (
                        <>
                          <Check
                            className="w-3 h-3 text-accent"
                            strokeWidth={2}
                          />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" strokeWidth={1.5} />
                          Copy ID
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Menu items */}
                <div className="p-1.5">
                  {[
                    { icon: User, label: "Profile", href: "/settings" },
                    { icon: Settings, label: "Settings", href: "/settings" },
                  ].map((item) => (
                    <a
                      key={item.label}
                      href={item.href}
                      role="menuitem"
                      onClick={() => setMenuOpen(false)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg",
                        "text-sm text-muted-foreground hover:text-foreground hover:bg-muted",
                        "transition-colors duration-100",
                      )}
                    >
                      <item.icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                      {item.label}
                    </a>
                  ))}
                </div>

                {/* Sign out */}
                <div className="p-1.5 border-t border-border">
                  <button
                    role="menuitem"
                    onClick={() => signOut({ callbackUrl: "/login" })}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 rounded-lg",
                      "text-sm text-destructive/70 hover:text-destructive hover:bg-destructive/[0.06]",
                      "transition-colors duration-100",
                    )}
                  >
                    <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Sign out
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
