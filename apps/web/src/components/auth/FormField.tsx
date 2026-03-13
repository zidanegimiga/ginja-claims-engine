import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  rightElement?: React.ReactNode;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, rightElement, className, ...props }, ref) => (
    <div className="space-y-6">
      <label className="text-[11px] font-medium text-white/40 uppercase tracking-widest">
        {label}
      </label>
      <div className="relative">
        <input
          ref={ref}
          className={cn(
            "w-full h-11 px-4 rounded-lg border text-sm mt-4",
            "bg-white/[0.04] text-white placeholder:text-white/20",
            "focus:outline-none focus:ring-2 focus:ring-[hsl(171,77%,56%)]/40 focus:border-[hsl(171,77%,56%)]/50",
            "transition-all duration-150",
            rightElement && "pr-11",
            error
              ? "border-red-500/50"
              : "border-white/10 hover:border-white/20",
            className
          )}
          {...props}
        />
        {rightElement && (
          <div className="absolute right-3.5 top-[50%]">
            {rightElement}
          </div>
        )}
      </div>
      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </div>
  )
);

FormField.displayName = "FormField";