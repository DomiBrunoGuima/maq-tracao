import { clsx } from "clsx";

interface Props {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  accent?: string; // tailwind color key from palette
}

export default function KPICard({ label, value, sub, highlight }: Props) {
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
      {/* Top accent line */}
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

      {sub && (
        <span className="text-[11px] text-muted font-mono">{sub}</span>
      )}
    </div>
  );
}
