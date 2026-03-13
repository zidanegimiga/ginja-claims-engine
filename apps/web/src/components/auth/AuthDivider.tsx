export function AuthDivider() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-px bg-white/[0.08]" />
      <span className="text-[11px] text-white/25 uppercase tracking-widest">
        or
      </span>
      <div className="flex-1 h-px bg-white/[0.08]" />
    </div>
  );
}