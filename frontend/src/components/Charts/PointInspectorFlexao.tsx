import { X } from "lucide-react";
import type { DataPoint, KPIsFlexao } from "../../types";
import { N_POR_KGF } from "../Common/Status";
import { Badge, CalcBlock, RawRow } from "./PointInspectorModal";

// Inspeção de um ponto da curva de flexão (3 pontos): mostra os dados gravados e
// refaz σf = 3FL/(2bh²), εf = 6δh/L² e o módulo local com a geometria do ensaio.

function n(pt: DataPoint, key: string): number | null {
  const v = pt[key];
  return typeof v === "number" ? v : null;
}

const fmt = (v: number, d = 4) => v.toFixed(d);

export default function PointInspectorFlexao({ point, kpis, onClose }: {
  point: DataPoint; kpis: KPIsFlexao; onClose: () => void;
}) {
  const F = n(point, "Forca_N");
  const d = n(point, "Deslocamento");
  const sig = n(point, "Tensao_Flexao");
  const eps = n(point, "Deform_Flexao");
  const t = n(point, "elapsed_seconds");
  const fase = typeof point.fase === "string" ? point.fase.replace(/_/g, " ") : null;
  const b = kpis.largura_mm || null;
  const h = kpis.espessura_mm || null;
  const L = kpis.span_mm || null;
  const geomOk = b != null && h != null && L != null;

  const sigCalc = F != null && geomOk ? (3 * F * L!) / (2 * b! * h! * h!) : null;
  const epsCalc = d != null && geomOk ? (6 * d * h!) / (L! * L!) : null;
  const sigE = sig ?? sigCalc;
  const epsE = eps ?? epsCalc;
  const eLocal = sigE != null && epsE != null && epsE > 0.0001 ? sigE / epsE : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-panel border border-border rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-border/60">
          <div>
            <p className="text-sm font-semibold text-white">Inspeção do Ponto · Flexão</p>
            <p className="text-xs text-muted font-mono mt-0.5">
              {t != null ? `t = ${fmt(t, 2)} s` : "t desconhecido"}{fase ? ` · ${fase}` : ""}
            </p>
          </div>
          <button onClick={onClose} className="text-muted/60 hover:text-white transition-colors mt-0.5"><X size={16} /></button>
        </div>

        <div className="p-5 space-y-5">
          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">Dados Gravados</p>
            <table className="w-full"><tbody>
              <RawRow label="Força" value={F != null ? fmt(F / N_POR_KGF, 2) : null} unit="kgf" source={<Badge color="blue">CLP</Badge>} />
              <RawRow label="Força (N)" value={F != null ? fmt(F, 2) : null} unit="N" source={<Badge color="green">kgf × 9,80665</Badge>} />
              <RawRow label="Deflexão δ" value={d != null ? fmt(d, 3) : null} unit="mm" source={<Badge color="blue">CLP</Badge>} />
              <RawRow label="Tensao_Flexao" value={sig != null ? fmt(sig, 4) : null} unit="MPa" source={<Badge color="blue">gravado</Badge>} />
              <RawRow label="Deform_Flexao" value={eps != null ? fmt(eps, 6) : null} source={<Badge color="blue">gravado</Badge>} />
              <RawRow label="fase" value={fase ?? "—"} source={<Badge color="blue">gravado</Badge>} />
            </tbody></table>
          </section>

          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">Corpo de Prova · {kpis.norma}</p>
            <table className="w-full"><tbody>
              <RawRow label="b — Largura" value={b != null ? fmt(b, 2) : null} unit="mm" source={<Badge color="green">setup</Badge>} />
              <RawRow label="h — Espessura" value={h != null ? fmt(h, 2) : null} unit="mm" source={<Badge color="green">setup</Badge>} />
              <RawRow label="L — Entre apoios" value={L != null ? fmt(L, 2) : null} unit="mm" source={<Badge color="green">setup</Badge>} />
            </tbody></table>
            {!geomOk && (
              <p className="text-[9px] text-amber-400/70 font-mono mt-2">
                ⚠ Ensaio gravado sem largura, espessura ou distância entre apoios: σf e εf não podem ser calculados.
              </p>
            )}
          </section>

          <section>
            <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-3">Cálculos</p>
            <div className="space-y-2.5">
              {sigCalc != null && (
                <CalcBlock title="Tensão de flexão  σf = 3FL ÷ 2bh²"
                  steps={[
                    { label: `3 × ${fmt(F!, 2)} N × ${fmt(L!, 2)} mm ÷ (2 × ${fmt(b!, 2)} × ${fmt(h!, 2)}²)`, value: "" },
                    ...(sig != null ? [{ label: "gravado", value: `${fmt(sig, 4)} MPa` }] : []),
                  ]}
                  result={fmt(sigCalc, 4)} unit="MPa" ok />
              )}
              {epsCalc != null && (
                <CalcBlock title="Deformação de flexão  εf = 6δh ÷ L²"
                  steps={[
                    { label: `6 × ${fmt(d!, 3)} mm × ${fmt(h!, 2)} mm ÷ ${fmt(L!, 2)}²`, value: "" },
                    ...(eps != null ? [{ label: "gravado", value: fmt(eps, 6) }] : []),
                  ]}
                  result={fmt(epsCalc, 6)} unit="(adimensional)" ok />
              )}
              {eLocal != null ? (
                <CalcBlock title="Módulo local  Ef = σf ÷ εf"
                  steps={[{ label: `σf = ${fmt(sigE!, 4)} MPa ÷ εf = ${fmt(epsE!, 6)}`, value: "" }]}
                  result={fmt(eLocal, 2)} unit="MPa" ok />
              ) : (
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[10px] text-slate-500 font-mono">Ef local = σf ÷ εf — εf insuficiente (&lt; 0.0001)</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
