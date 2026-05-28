import { clsx } from "clsx";

interface Props {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  compact?: boolean;
}

export default function KPICard({ label, value, sub, highlight, compact }: Props) {
  if (compact) {
    return (
      <div
        className={clsx(
          "relative rounded-lg p-3 flex flex-col gap-1 overflow-hidden",
          "bg-[#0d1020] border",
          highlight ? "border-rupture/30" : "border-border/60"
        )}
      >
        <div
          className={clsx(
            "absolute top-0 left-0 right-0 h-px",
            highlight
              ? "bg-gradient-to-r from-rupture/70 via-rupture/20 to-transparent"
              : "bg-gradient-to-r from-accent/40 via-accent/10 to-transparent"
          )}
        />
        <span className="text-[9px] font-semibold text-muted/70 uppercase tracking-widest leading-none">
          {label}
        </span>
        <span
          className={clsx(
            "text-[13px] font-mono font-bold leading-none truncate",
            highlight ? "text-rupture" : "text-white"
          )}
        >
          {value}
        </span>
        {sub && <span className="text-[9px] text-muted/60 font-mono leading-none truncate">{sub}</span>}
      </div>
    );
  }

  return (
    <div
      className={clsx(
        "relative rounded-xl p-4 flex flex-col gap-1.5 overflow-hidden transition-all duration-300",
        "bg-surface border",
        highlight
          ? "border-rupture/30 shadow-[0_0_20px_rgba(255,107,53,0.08)]"
          : "border-border hover:border-border/80"
      )}
    >
      <div
        className={clsx(
          "absolute top-0 left-0 right-0 h-px",
          highlight
            ? "bg-gradient-to-r from-rupture/80 via-rupture/30 to-transparent"
            : "bg-gradient-to-r from-accent/50 via-accent/15 to-transparent"
        )}
      />
      <span className="text-[10px] font-semibold text-muted uppercase tracking-widest">
        {label}
      </span>
      <span
        className={clsx(
          "text-2xl font-mono font-bold leading-none",
          highlight ? "text-rupture" : "text-white"
        )}
      >
        {value}
      </span>
      {sub && <span className="text-[11px] text-muted font-mono">{sub}</span>}
    </div>
  );
}
