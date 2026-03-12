"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2, ShieldCheck, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";

  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginForm) {
    setAuthError(null);
    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      redirect: false,
    });

    if (result?.error) {
      setAuthError("Invalid email or password. Please try again.");
      return;
    }

    router.push(callbackUrl);
    router.refresh();
  }

  return (
    <div className="relative w-full min-h-screen flex items-center justify-center overflow-hidden">

      <div
        className="absolute inset-0 opacity-[0.03] dark:opacity-[0.06]"
        style={{
          backgroundImage: `
            linear-gradient(hsl(var(--border)) 1px, transparent 1px),
            linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-accent/5 blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md mx-4"
      >
        <div className="rounded-lg border border-border bg-card p-8 shadow-xl shadow-black/10">

          <div className="mb-8">
            <div className="flex items-center gap-2.5 mb-6">
              <div className="flex items-center justify-center w-9 h-9 rounded-md bg-accent/10 border border-accent/20">
                <Activity className="w-4.5 h-4.5 text-accent" strokeWidth={1.5} />
              </div>
              <span className="text-sm font-semibold tracking-wide text-foreground">
                GINJA AI
              </span>
            </div>

            <h1 className="text-2xl font-semibold text-foreground tracking-tight">
              Claims Intelligence
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Sign in to access the adjudication engine
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Email address
              </label>
              <input
                {...register("email")}
                type="email"
                autoComplete="email"
                placeholder="you@organisation.com"
                className={cn(
                  "w-full h-10 px-3 rounded-md border bg-background text-sm",
                  "text-foreground placeholder:text-muted-foreground/50",
                  "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60",
                  "transition-colors duration-150",
                  errors.email
                    ? "border-destructive/60 focus:ring-destructive/30"
                    : "border-input"
                )}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={cn(
                    "w-full h-10 px-3 pr-10 rounded-md border bg-background text-sm",
                    "text-foreground placeholder:text-muted-foreground/50",
                    "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60",
                    "transition-colors duration-150",
                    errors.password
                      ? "border-destructive/60 focus:ring-destructive/30"
                      : "border-input"
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  tabIndex={-1}
                >
                  {showPassword
                    ? <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                    : <Eye className="w-4 h-4" strokeWidth={1.5} />
                  }
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            {/* Auth error */}
            {authError && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2.5"
              >
                <p className="text-xs text-destructive">{authError}</p>
              </motion.div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "w-full h-10 rounded-md text-sm font-medium",
                "bg-accent text-accent-foreground",
                "hover:bg-accent/90 active:scale-[0.98]",
                "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:ring-offset-2 focus:ring-offset-card",
                "disabled:opacity-60 disabled:cursor-not-allowed",
                "transition-all duration-150 flex items-center justify-center gap-2"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-border flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
            <span>
              Secured with encrypted sessions and role-based access control
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}