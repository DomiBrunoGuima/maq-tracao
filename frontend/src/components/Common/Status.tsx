import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { getConexaoCLP } from "../../api/client";

// ── Indicador de conexão do CLP ─────────────────────────────────────────────

export function ConexaoCLPIndicator() {
  const { data, isLoading } = useQuery({
    queryKey: ["clp-conexao"],
    queryFn: getConexaoCLP,
    refetchInterval: 4000,
    retry: false,
  });
  const online = !!data?.online;
  const ip = data?.simulador ? "simulador" : data?.ip || "não configurado";

  return (
    <div
      title={online ? `Latência ${data?.latencia_ms ?? "—"} ms` : data?.motivo || "Sem resposta"}
      className={clsx(
        "rounded-lg border px-3 py-2",
        isLoading ? "border-border bg-bg"
          : online ? "border-emerald-500/40 bg-emerald-500/10"
          : "border-red-500/40 bg-red-500/10",
      )}
    >
      <div className="flex items-center gap-2">
        <span className={clsx(
          "w-2.5 h-2.5 rounded-full flex-shrink-0",
          isLoading ? "bg-muted" : online ? "bg-emerald-400 animate-pulse" : "bg-red-500",
        )} />
        <span className={clsx(
          "text-xs font-bold tracking-wide",
          isLoading ? "text-muted" : online ? "text-emerald-300" : "text-red-300",
        )}>
          {isLoading ? "VERIFICANDO CLP…" : online ? "CLP CONECTADO" : "CLP DESCONECTADO"}
        </span>
      </div>
      <p className="text-[11px] font-mono text-muted mt-0.5 pl-[18px]">
        IP: {ip}{data?.port && !data.simulador ? `:${data.port}` : ""}
      </p>
    </div>
  );
}

// ── Status do ensaio ────────────────────────────────────────────────────────

export type StatusEnsaio = "parado" | "preparando" | "executando" | "ruptura" | "finalizado";

const ETAPAS: { key: StatusEnsaio; label: string; cor: string }[] = [
  { key: "parado", label: "Parado", cor: "bg-slate-500" },
  { key: "preparando", label: "Preparando", cor: "bg-amber-400" },
  { key: "executando", label: "Executando", cor: "bg-emerald-400" },
  { key: "ruptura", label: "Ruptura detectada", cor: "bg-red-500" },
  { key: "finalizado", label: "Finalizado", cor: "bg-sky-400" },
];

export function StatusEnsaioBar({ status }: { status: StatusEnsaio }) {
  return (
    <div className="bg-surface border border-border rounded-xl px-4 py-3 flex flex-wrap items-center gap-x-5 gap-y-2">
      <span className="text-[10px] font-semibold text-muted uppercase tracking-widest">Status do ensaio</span>
      {ETAPAS.map((e) => {
        const ativo = e.key === status;
        return (
          <div key={e.key} className={clsx(
            "flex items-center gap-2 px-3 py-1 rounded-full text-sm transition-all",
            ativo ? "bg-border/60 font-semibold text-white ring-1 ring-border" : "text-muted/60",
          )}>
            <span className={clsx(
              "w-2.5 h-2.5 rounded-full",
              ativo ? e.cor : "bg-muted/30",
              ativo && (e.key === "executando" || e.key === "preparando") && "animate-pulse",
            )} />
            {e.label}
          </div>
        );
      })}
    </div>
  );
}

// ── Valor em tempo real grande ──────────────────────────────────────────────

export function BigValue({
  icon, label, value, unit, color = "text-white", sub,
}: {
  icon: React.ReactNode; label: string; value: string; unit: string; color?: string; sub?: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl px-5 py-4">
      <div className="flex items-center gap-2 text-muted">
        <span className="text-accent opacity-80">{icon}</span>
        <p className="text-xs font-semibold uppercase tracking-wider">{label}</p>
      </div>
      <p className={clsx("mt-2 font-mono font-bold tracking-tight leading-none", color)}>
        <span className="text-5xl tabular-nums">{value}</span>
        <span className="text-xl ml-2 opacity-70">{unit}</span>
      </p>
      {sub && <p className="text-xs text-muted mt-2 font-mono">{sub}</p>}
    </div>
  );
}

/** Número formatado para os mostradores grandes ("—" sem leitura). */
export function fmtBig(v: number | null | undefined, dec: number): string {
  return v == null || !Number.isFinite(v) ? "—" : v.toFixed(dec);
}
