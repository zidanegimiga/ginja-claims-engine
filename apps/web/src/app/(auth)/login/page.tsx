/* eslint-disable @typescript-eslint/ban-ts-comment */
"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, Loader2, Activity, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  FormField,
  OAuthButton,
  AuthDivider,
  LiveFeedPanel,
} from "@/components/auth";

// Schemas
const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

const signupSchema = z
  .object({
    name: z.string().min(2, "Full name must be at least 2 characters"),
    email: z.string().email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type LoginForm = z.infer<typeof loginSchema>;
type SignupForm = z.infer<typeof signupSchema>;
type Mode = "login" | "signup";

// Variants
const panelVariants = {
  enter: (dir: number) => ({
    x: dir > 0 ? 32 : -32,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
  },
  exit: (dir: number) => ({
    x: dir > 0 ? -32 : 32,
    opacity: 0,
    transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function AuthPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";
  const sessionError = searchParams.get("error");

  const [mode, setMode] = useState<Mode>("login");
  const [direction, setDirection] = useState(1);
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [authError, setAuthError] = useState<string | null>(
    sessionError === "session_expired"
      ? "Your session expired. Please sign in again."
      : null,
  );
  const [oauthLoading, setOauthLoading] = useState<
    "google" | "microsoft" | null
  >(null);

  // Forms
  const loginForm = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });
  const signupForm = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
  });

  // Mode switch
  function switchMode(next: Mode) {
    setDirection(next === "signup" ? 1 : -1);
    setAuthError(null);
    setShowPass(false);
    setShowConfirm(false);
    loginForm.reset();
    signupForm.reset();
    setMode(next);
  }

  // OAuth
  async function handleOAuth(provider: "google" | "microsoft") {
    setOauthLoading(provider);
    await signIn(provider === "microsoft" ? "azure-ad" : provider, {
      callbackUrl: new URL(`/dashboard`, window.location.origin).href,
    });
    setOauthLoading(null);
  }

    // const microsoft_auth = async (e) => {
    //   e.preventDefault();
    //   await signIn("azure-ad", {
    //     redirect: true,
    //     callbackUrl: new URL(`/auth/login-confirmation`, window.location.origin)
    //       .href,
    //   });
    //   // await signIn('microsoft-entra-id', {
    //   //   redirect: true,
    //   //   callbackUrl: new URL(`/auth/login-confirmation`, window.location.origin)
    //   //     .href,
    //   // });
    // };

  // Login submit
  async function onLogin(data: LoginForm) {
    setAuthError(null);
    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      mode: "login",
      redirect: false,
    });
    if (result?.error) {
      setAuthError("Invalid email or password.");
      return;
    }
    router.push('/dashboard');
    router.refresh();
  }

  // Signup submit
  async function onSignup(data: SignupForm) {
    setAuthError(null);
    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      name: data.name,
      mode: "register",
      redirect: false,
    });
    if (result?.error) {
      setAuthError(
        result.error === "CredentialsSignin"
          ? "An account with this email already exists."
          : "Something went wrong. Please try again.",
      );
      return;
    }
    router.push('/dashboard');
    router.refresh();
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0A0A0A]">
      <div className="relative flex flex-col justify-center w-full max-w-[480px] px-12 shrink-0 bg-[#0A0A0A] overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Logo */}
        <div className="absolute top-8 left-12 flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-md bg-[hsl(171,77%,56%)]/10 border border-[hsl(171,77%,56%)]/30">
            <Activity
              className="w-4 h-4 text-[hsl(171,77%,56%)]"
              strokeWidth={1.5}
            />
          </div>
          <span className="text-sm font-semibold tracking-widest text-white/80 uppercase">
            Ginja AI
          </span>
        </div>

        <div
          className="relative"
          style={{ minHeight: mode === "signup" ? 520 : 420 }}
        >
          <AnimatePresence custom={direction} mode="wait">
            {mode === "login" ? (
              <motion.div
                key="login"
                custom={direction}
                // @ts-ignore
                variants={panelVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="absolute inset-0 flex flex-col justify-center space-y-6"
              >
                <div>
                  <h1 className="text-[28px] font-semibold text-white tracking-tight leading-tight">
                    Welcome back
                  </h1>
                  <p className="mt-1.5 text-sm text-white/40">
                    Sign in to the claims intelligence platform
                  </p>
                </div>

                <div className="space-y-2.5">
                  <OAuthButton
                    provider="google"
                    onClick={() => handleOAuth("google")}
                    loading={oauthLoading === "google"}
                  />
                  <OAuthButton
                    provider="microsoft"
                    onClick={() => handleOAuth("microsoft")}
                    loading={oauthLoading === "microsoft"}
                  />
                </div>

                <AuthDivider />

                <form
                  onSubmit={loginForm.handleSubmit(onLogin)}
                  className="space-y-4"
                >
                  <FormField
                    label="Email address"
                    type="email"
                    autoComplete="email"
                    placeholder="you@organisation.com"
                    error={loginForm.formState.errors.email?.message}
                    {...loginForm.register("email")}
                  />

                  <FormField
                    label="Password"
                    type={showPass ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    error={loginForm.formState.errors.password?.message}
                    rightElement={
                      <button
                        type="button"
                        onClick={() => setShowPass((v) => !v)}
                        tabIndex={-1}
                        className="text-white/30 hover:text-white/70 transition-colors"
                      >
                        {showPass ? (
                          <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                        ) : (
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        )}
                      </button>
                    }
                    {...loginForm.register("password")}
                  />

                  <AnimatePresence>
                    {authError && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="rounded-lg border border-red-500/20 bg-red-500/10 px-3.5 py-2.5"
                      >
                        <p className="text-[11px] text-red-400">{authError}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <button
                    type="submit"
                    disabled={loginForm.formState.isSubmitting}
                    className={cn(
                      "w-full h-11 rounded-lg text-sm font-semibold",
                      "bg-accent text-accent-foreground",
                      "hover:bg-accent/90 active:scale-[0.98]",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "transition-all duration-150 flex items-center justify-center gap-2",
                      "shadow-[0_0_24px_hsl(171,77%,56%,0.25)] my-8",
                    )}
                  >
                    {loginForm.formState.isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Signing in…
                      </>
                    ) : (
                      "Sign in"
                    )}
                  </button>
                </form>

                <p className="text-[12px] text-white/30 text-center">
                  Don&apos;t have an account?{" "}
                  <button
                    onClick={() => switchMode("signup")}
                    className="text-[hsl(171,77%,56%)] hover:text-[hsl(171,77%,66%)] transition-colors font-medium"
                  >
                    Create one
                  </button>
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="signup"
                custom={direction}
                // @ts-ignore
                variants={panelVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="absolute inset-0 flex flex-col justify-center space-y-5"
              >
                <div>
                  <h1 className="text-[28px] font-semibold text-white tracking-tight leading-tight">
                    Create account
                  </h1>
                  <p className="mt-1.5 text-sm text-white/40">
                    Join the Ginja AI claims platform
                  </p>
                </div>

                <div className="space-y-2.5">
                  <OAuthButton
                    provider="google"
                    onClick={() => handleOAuth("google")}
                    loading={oauthLoading === "google"}
                  />
                  <OAuthButton
                    provider="microsoft"
                    onClick={() => handleOAuth("microsoft")}
                    loading={oauthLoading === "microsoft"}
                  />
                </div>

                <AuthDivider />

                <form
                  onSubmit={signupForm.handleSubmit(onSignup)}
                  className="space-y-3.5"
                >
                  <FormField
                    label="Full name"
                    type="text"
                    autoComplete="name"
                    placeholder="Ada Okonkwo"
                    error={signupForm.formState.errors.name?.message}
                    {...signupForm.register("name")}
                  />

                  <FormField
                    label="Email address"
                    type="email"
                    autoComplete="email"
                    placeholder="you@organisation.com"
                    error={signupForm.formState.errors.email?.message}
                    {...signupForm.register("email")}
                  />

                  <FormField
                    label="Password"
                    type={showPass ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="Min. 8 characters"
                    error={signupForm.formState.errors.password?.message}
                    rightElement={
                      <button
                        type="button"
                        onClick={() => setShowPass((v) => !v)}
                        tabIndex={-1}
                        className="text-white/30 hover:text-white/70 transition-colors"
                      >
                        {showPass ? (
                          <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                        ) : (
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        )}
                      </button>
                    }
                    {...signupForm.register("password")}
                  />

                  <FormField
                    label="Confirm password"
                    type={showConfirm ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="••••••••"
                    error={signupForm.formState.errors.confirmPassword?.message}
                    rightElement={
                      <button
                        type="button"
                        onClick={() => setShowConfirm((v) => !v)}
                        tabIndex={-1}
                        className="text-white/30 hover:text-white/70 transition-colors"
                      >
                        {showConfirm ? (
                          <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                        ) : (
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        )}
                      </button>
                    }
                    {...signupForm.register("confirmPassword")}
                  />

                  <AnimatePresence>
                    {authError && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="rounded-lg border border-red-500/20 bg-red-500/10 px-3.5 py-2.5"
                      >
                        <p className="text-[11px] text-red-400">{authError}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <button
                    type="submit"
                    disabled={signupForm.formState.isSubmitting}
                    className={cn(
                      "w-full h-11 rounded-lg text-sm font-semibold",
                      "bg-accent text-accent-foreground",
                      "hover:bg-accent/90 active:scale-[0.98]",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "transition-all duration-150 flex items-center justify-center gap-2",
                      "shadow-[0_0_24px_hsl(171,77%,56%,0.25)] my-8",
                    )}
                  >
                    {signupForm.formState.isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Creating account…
                      </>
                    ) : (
                      "Create account"
                    )}
                  </button>
                </form>

                <p className="text-[12px] text-white/30 text-center">
                  Already have an account?{" "}
                  <button
                    onClick={() => switchMode("login")}
                    className="text-[hsl(171,77%,56%)] hover:text-[hsl(171,77%,66%)] transition-colors font-medium"
                  >
                    Sign in
                  </button>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="absolute bottom-8 left-12 right-12 flex items-center gap-2 text-[11px] text-white/20">
          <ShieldCheck className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
          <span>Encrypted sessions · RBAC · JWT rotation</span>
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden bg-[#0D1210] border-l border-white/[0.06]">
        <LiveFeedPanel />
      </div>
    </div>
  );
}
