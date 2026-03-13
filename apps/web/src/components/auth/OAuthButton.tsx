import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import { GoogleIcon, MicrosoftIcon } from "../ui/sharedIcons";

interface OAuthButtonProps {
  provider: "google" | "microsoft";
  onClick: () => void;
  loading?: boolean;
}

const PROVIDERS = {
  google: {
    label: "Continue with Google",
    icon: (
      <GoogleIcon/>
    ),
  },
  microsoft: {
    label: "Continue with Microsoft",
    icon: (
      <MicrosoftIcon/>
    ),
  },
};

export function OAuthButton({ provider, onClick, loading }: OAuthButtonProps) {
  const { label, icon } = PROVIDERS[provider];
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className={cn(
        "w-full h-11 rounded-lg border border-white/10 bg-white/[0.03]",
        "flex items-center justify-center gap-3",
        "text-sm text-white/70 hover:text-white",
        "hover:bg-white/[0.06] hover:border-white/20",
        "transition-all duration-150",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      <span>{label}</span>
    </button>
  );
}
