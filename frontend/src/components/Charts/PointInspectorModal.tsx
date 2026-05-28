import { X } from "lucide-react";
import { useMemo } from "react";
import type { DataPoint, KPIs, ParametrosIHM } from "../../types";

// ── helpers ───────────────────────────────────────────────────

function n(pt: DataPoint, key: string): number | null {
  const v = pt[key];
  return typeof v === "number" ? v : null;
}

function fmt(v: number, d = 4): string {
  return v.toFixed(d);
}

// ── sub-components ────────────────────────────────────────────

function Badge({ children, color }: { children: React.ReactNode; color: "blue" | "green" | "amber" }) {
  const cls = {
    blue:  "bg-blue-500/10  text-blue-400  border-blue-500/20",
    green: "bg-green-500/10 text-green-400 border-green-500/20",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  }[color];
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[9px] font-mono font-medium ${cls}`}>
      {children}
    </span>
  );
}

function RawRow({ label, value, unit, source }: {
  label: string; value: string | null; unit?: string; source: React.ReactNode;
}) {
  return (
    <tr className="border-b border-white/5 last:border-0">
      <td className="py-1.5 pr-3 text-[10px] font-mono text-slate-400 whitespace-nowrap">{label}</td>
      <td className="py-1.5 pr-3 text-[11px] font-mono text-white font-semibold">
        {value ?? <span className="text-slate-600">—</span>}
        {unit && value && <span className="text-slate-500 ml-1 font-normal">{unit}</span>}
      </td>
      <td className="py-1.5">{source}</td>
    </tr>
  );
}

function CalcBlock({ title, steps, result, unit, ok }: {
  title: string;
  steps: { label: string; value: string }[];
  result: string;
  unit: string;
  ok: boolean;
}) {
  return (
    <div className={`rounded-lg border p-3 ${ok ? "border-accent/20 bg-accent/5" : "border-white/5 bg-white/[0.02]"}`}>
      <p className="text-[10px] font-semibold text-muted/70 uppercase tracking-wider mb-2">{title}</p>
      <div className="space-y-0.5 font-mono">
        {steps.map((s, i) => (
          <div key={i} className="flex items-baseline gap-2">
            <span className="text-[10px] text-slate-500 w-3 flex-shrink-0">{i === 0 ? "=" : "="}</span>
            <span className="text-[10px] text-slate-400">{s.label}</span>
            <span className="text-[10px] text-slate-500 ml-auto">{s.value}</span>
          </div>
        ))}
        <div className="flex items-baseline gap-2 pt-1.5 border-t border-white/10 mt-1.5">
          <span className="text-[11px] text-slate-500 w-3">∴</span>
          <span className={`text-sm font-bold ${ok ? "text-accent" : "text-white"}`}>{result}</span>
          <span className="text-[10px] text-slate-500 ml-1">{unit}</span>
        </div>
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────

interface Props {
  point: DataPoint;
  kpis: KPIs;
  ihmParams: ParametrosIHM | null | undefined;
  onClose: () => void;
}

export default function PointInspectorModal({ point, kpis, ihmParams, onClose }: Props) {
  const calc = useMemo(() => {
    const F  = n(point, "Forca_N");
    const d  = n(point, "Deslocamento");
    const σ  = n(point, "Tensao_Pa");
    const ε  = n(point, "Deform_Along");
    const E  = n(point, "Modulo_Elast");
    const t  = n(point, "elapsed_seconds");
    const fase = typeof point.fase === "string" ? point.fase : null;

    const ihmArea = ihmParams?.params?.area_seccao ?? null;
    const ihmL0   = ihmParams?.params?.comprimento_inicial ?? null;

    const A  = ihmArea  != null ? Number(ihmArea)  : kpis.area_secao_mm2;
    const L0 = ihmL0    != null ? Number(ihmL0)    : kpis.comprimento_inicial_mm;

    const areaSource  = (ihmArea  != null ? "ihm" : kpis.area_secao_mm2   != null ? "calc" : "none") as "ihm" | "calc" | "none";
    const l0Source    = (ihmL0    != null ? "ihm" : kpis.comprimento_inicial_mm != null ? "calc" : "none") as "ihm" | "calc" | "none";

    // σ = F / A
    const sigma_calc = F != null && A ? F / A : null;

    // ε = ΔL / L₀
    const eps_calc = d != null && L0 ? d / L0 : null;

    // E local = σ / ε  (usa CSV σ e ε se disponíveis, senão os calculados)
    const sig_for_e = σ ?? sigma_calc;
    const eps_for_e = ε ?? eps_calc;
    const e_local   = sig_for_e != null && eps_for_e != null && eps_for_e > 0.0001
      ? sig_for_e / eps_for_e
      : null;

    // A% = (d / L₀) × 100  (apenas se for o ponto de maior força)
    const is_rupt = F != null && Math.abs(F - kpis.forca_max_N) < 0.5;
    const alonga  = d != null && L0 ? (d / L0) * 100 : null;

    return { F, d, σ, ε, E, t, fase, A, L0, areaSource, l0Source, sigma_calc, eps_calc, e_local, is_rupt, alonga };
  }, [point, kpis, ihmParams]);

  const sourceNode = (src: "ihm" | "calc" | "none") => {
    if (src === "ihm")  return <Badge color="green">IHM Modbus</Badge>;
    if (src === "calc") return <Badge color="amber">back-calc</Badge>;
    return <Badge color="blue">—</Badge>;
  };

  const faseLabel = calc.fase?.replace(/_/g, " ") ?? "—";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[#0d1020] border border-border rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-border/60">
          <div>
            <p className="text-sm font-semibold text-white">Inspeção do Ponto</p>
            <p className="text-xs text-muted font-mono mt-0.5">
              {calc.t != null ? `t = ${fmt(calc.t, 2)} s` : "t desconhecido"}
              {calc.fase ? ` · ${faseLabel}` : ""}
            </p>
          </div>
          <button onClick={onClose} className="text-muted/60 hover:text-white transition-colors mt-0.5">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-5">

          {/* ── Dados brutos (CSV) ──────────────────────── */}
          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">
              Dados Brutos
            </p>
            <table className="w-full">
              <tbody>
                <RawRow label="Forca_N"       value={calc.F  != null ? fmt(calc.F,  2) : null} unit="N"   source={<Badge color="blue">CSV</Badge>} />
                <RawRow label="Deslocamento"  value={calc.d  != null ? fmt(calc.d,  3) : null} unit="mm"  source={<Badge color="blue">CSV</Badge>} />
                <RawRow label="Tensao_Pa"     value={calc.σ  != null ? fmt(calc.σ,  4) : null} unit="MPa" source={<Badge color="blue">CSV</Badge>} />
                <RawRow label="Deform_Along"  value={calc.ε  != null ? fmt(calc.ε,  6) : null}            source={<Badge color="blue">CSV</Badge>} />
                {calc.E != null && (
                  <RawRow label="Modulo_Elast" value={fmt(calc.E, 2)} unit="MPa"               source={<Badge color="blue">CSV</Badge>} />
                )}
                <RawRow label="fase"          value={faseLabel}                                source={<Badge color="blue">CSV</Badge>} />
              </tbody>
            </table>
          </section>

          {/* ── Parâmetros do corpo de prova ────────────── */}
          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">
              Parâmetros do Corpo de Prova
            </p>
            <table className="w-full">
              <tbody>
                <RawRow
                  label="A — Área da Seção"
                  value={calc.A != null ? fmt(calc.A, 4) : null}
                  unit="mm²"
                  source={sourceNode(calc.areaSource)}
                />
                <RawRow
                  label="L₀ — Comp. Inicial"
                  value={calc.L0 != null ? fmt(calc.L0, 3) : null}
                  unit="mm"
                  source={sourceNode(calc.l0Source)}
                />
              </tbody>
            </table>
            {(calc.areaSource === "calc" || calc.l0Source === "calc") && (
              <p className="text-[9px] text-amber-400/60 font-mono mt-2 leading-relaxed">
                ⚠ Valores back-calculados da série CSV (IHM offline ou registradores não configurados).
                Configure os registradores area_seccao e comprimento_inicial para máxima precisão.
              </p>
            )}
          </section>

          {/* ── Cálculos ─────────────────────────────────── */}
          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">
              Cálculos
            </p>
            <div className="space-y-2.5">

              {/* σ = F / A */}
              {calc.F != null && calc.A != null ? (
                <CalcBlock
                  title="Tensão  σ = F ÷ A"
                  steps={[
                    { label: `F = ${fmt(calc.F, 2)} N  ÷  A = ${fmt(calc.A, 4)} mm²`, value: "" },
                    ...(calc.σ != null ? [{ label: `CSV reportou`, value: `${fmt(calc.σ, 4)} MPa` }] : []),
                  ]}
                  result={`${fmt(calc.sigma_calc!, 4)}`}
                  unit="MPa"
                  ok={calc.sigma_calc != null}
                />
              ) : (
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[10px] text-slate-500 font-mono">σ = F ÷ A — dados insuficientes neste ponto</p>
                </div>
              )}

              {/* ε = ΔL / L₀ */}
              {calc.d != null && calc.L0 != null ? (
                <CalcBlock
                  title="Deformação  ε = ΔL ÷ L₀"
                  steps={[
                    { label: `ΔL = ${fmt(calc.d, 3)} mm  ÷  L₀ = ${fmt(calc.L0, 3)} mm`, value: "" },
                    ...(calc.ε != null ? [{ label: `CSV reportou`, value: fmt(calc.ε, 6) }] : []),
                  ]}
                  result={`${fmt(calc.eps_calc!, 6)}`}
                  unit="(adimensional)"
                  ok={calc.eps_calc != null}
                />
              ) : (
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[10px] text-slate-500 font-mono">ε = ΔL ÷ L₀ — deslocamento não disponível neste ponto</p>
                </div>
              )}

              {/* E local = σ / ε */}
              {calc.e_local != null ? (
                <CalcBlock
                  title="Módulo de Elasticidade Local  E = σ ÷ ε"
                  steps={[
                    {
                      label: `σ = ${fmt(calc.σ ?? calc.sigma_calc!, 4)} MPa  ÷  ε = ${fmt(calc.ε ?? calc.eps_calc!, 6)}`,
                      value: "",
                    },
                  ]}
                  result={`${fmt(calc.e_local, 2)}`}
                  unit="MPa"
                  ok
                />
              ) : (
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[10px] text-slate-500 font-mono">E local = σ ÷ ε — ε insuficiente (&lt; 0.0001)</p>
                </div>
              )}

              {/* A% = (d / L₀) × 100 — só mostra perto da ruptura */}
              {calc.is_rupt && calc.alonga != null && calc.L0 != null && calc.d != null && (
                <CalcBlock
                  title="Alongamento na Ruptura  A% = (d ÷ L₀) × 100"
                  steps={[
                    { label: `d = ${fmt(calc.d, 3)} mm  ÷  L₀ = ${fmt(calc.L0, 3)} mm  × 100`, value: "" },
                  ]}
                  result={`${fmt(calc.alonga, 2)}`}
                  unit="%"
                  ok
                />
              )}

            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
