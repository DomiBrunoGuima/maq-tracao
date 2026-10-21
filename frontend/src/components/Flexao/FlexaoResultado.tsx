import { useState } from "react";
import { Layers, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import { ReferenceArea, ReferenceLine } from "recharts";
import type { AjusteElastico, EnsaioFlexaoSummary, FlexaoChartData, KPIsFlexao } from "../../types";
import { useCurvasFlexao, useKPIsFlexao, useQualidadeFlexao } from "../../hooks/useFlexao";
import SimpleLineChart from "../Charts/SimpleLineChart";
import KPICard from "../Dashboard/KPICard";
import QualidadePanel from "../Dashboard/QualidadePanel";
import { FASE_CORES, HeroValue, MiniStat, SectionLabel } from "../Dashboard/Dashboard";

// Mesmo layout do resultado da tração (Dashboard): valores em destaque, gráfico
// principal com miniaturas e, à direita, qualidade, trecho elástico, estágios e resultados.

const CORES: Record<string, string> = {
  ...FASE_CORES,
  pos_escoamento: "#f59e0b",
  fim_ensaio: "#64748b",
};

type ChartKey = "ss" | "fd" | "ft" | "em" | "st";

const CHARTS: { key: ChartKey; label: string; sub: string }[] = [
  { key: "ss", label: "σf-εf", sub: "Tensão × Deformação de flexão" },
  { key: "fd", label: "F × δ", sub: "Força × Deflexão" },
  { key: "ft", label: "F × t", sub: "Força × Tempo" },
  { key: "em", label: "Ef × t", sub: "Módulo × Tempo" },
  { key: "st", label: "σf × t", sub: "Tensão × Tempo" },
];

const FASE_X: Record<ChartKey, "eps" | "d" | "t"> = { ss: "eps", fd: "d", ft: "t", em: "t", st: "t" };

function reta(fit: AjusteElastico, xMax: number) {
  // Prolonga a reta além do trecho para mostrar onde a curva se afasta dela
  const x2 = Math.min(xMax, fit.x_ini + (fit.x_fim - fit.x_ini) * 1.6);
  return (
    <ReferenceLine key="reg" ifOverflow="hidden" stroke="#f43f5e" strokeWidth={1.5} strokeDasharray="6 4"
      segment={[
        { x: fit.x_ini, y: fit.inclinacao * fit.x_ini + fit.intercepto },
        { x: x2, y: fit.inclinacao * x2 + fit.intercepto },
      ]} />
  );
}

function extras(key: ChartKey, c: FlexaoChartData, mostrarFases: boolean): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  if (mostrarFases) {
    const eixo = FASE_X[key];
    c.fases?.forEach((f, i) => {
      const x1 = f[`${eixo}_ini` as const];
      const x2 = f[`${eixo}_fim` as const];
      if (x1 == null || x2 == null || x1 === x2) return;
      out.push(
        <ReferenceArea key={`fase-${i}`} x1={x1} x2={x2} ifOverflow="hidden"
          fill={CORES[f.fase] ?? "#64748b"} fillOpacity={0.1} strokeOpacity={0} />,
      );
    });
  }
  const maxX = (pts: any[], k: string) => {
    const xs = pts.map((p) => p[k]).filter((v): v is number => typeof v === "number");
    return xs.length ? Math.max(...xs) : 0;
  };
  const fit = c.trecho_elastico;
  if (key === "ss" && fit?.ss) out.push(reta(fit.ss, maxX(c.stress_strain, "Deform_Flexao")));
  if (key === "fd" && fit?.fd) out.push(reta(fit.fd, maxX(c.force_displacement, "Deslocamento")));
  return out;
}

function renderChart(key: ChartKey, c: FlexaoChartData, height: number, thumbnail = false, mostrarFases = false) {
  const p = { height, thumbnail, extras: thumbnail ? [] : extras(key, c, mostrarFases) };
  switch (key) {
    case "ss": return <SimpleLineChart data={c.stress_strain} xKey="Deform_Flexao" yKey="Tensao_Flexao" yUnit="MPa" xLabel="εf" yLabel="σf (MPa)" color="#38bdf8" xDecimals={4} {...p} />;
    case "fd": return <SimpleLineChart data={c.force_displacement} xKey="Deslocamento" yKey="Forca_N" xUnit="mm" yUnit="N" xLabel="δ (mm)" yLabel="F (N)" color="#a78bfa" {...p} />;
    case "ft": return <SimpleLineChart data={c.force_time} xKey="elapsed_seconds" yKey="Forca_N" xUnit="s" yUnit="N" xLabel="t (s)" yLabel="F (N)" color="#38bdf8" {...p} />;
    case "em": return <SimpleLineChart data={c.flexural_modulus_time} xKey="elapsed_seconds" yKey="Modulo_Flexao" xUnit="s" yUnit="MPa" xLabel="t (s)" yLabel="Ef (MPa)" color="#f59e0b" {...p} />;
    case "st": return <SimpleLineChart data={c.stress_time} xKey="elapsed_seconds" yKey="Tensao_Flexao" xUnit="s" yUnit="MPa" xLabel="t (s)" yLabel="σf (MPa)" color="#10b981" {...p} />;
  }
}

const fmt = (n: number | null | undefined, d = 2) => (n == null || !Number.isFinite(n) ? "—" : n.toFixed(d));

export default function FlexaoResultado({
  ensaios, selected, onSelect, onDelete,
}: {
  ensaios: EnsaioFlexaoSummary[];
  selected: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const { data: kpis } = useKPIsFlexao(selected);
  const { data: curvas } = useCurvasFlexao(selected);
  const { data: qualidade } = useQualidadeFlexao(selected);
  const [ativo, setAtivo] = useState<ChartKey>("ss");
  const [mostrarFases, setMostrarFases] = useState(true);
  const ensaio = ensaios.find((e) => e.id === selected);

  return (
    <div className="space-y-4">
      {/* Cabeçalho com o ensaio escolhido */}
      <div className="flex items-center gap-3">
        <select value={selected ?? ""} onChange={(e) => onSelect(Number(e.target.value))}
          className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent min-w-0 max-w-md">
          {ensaios.map((e) => (
            <option key={e.id} value={e.id}>{e.filename.replace(".csv", "")} · {e.data_ensaio}</option>
          ))}
        </select>
        {ensaio && <span className="text-xs text-muted">{ensaio.num_amostras} amostras</span>}
        {selected != null && (
          <button onClick={() => onDelete(selected)} title="Excluir ensaio"
            className="ml-auto text-muted hover:text-red-400 transition-colors p-1.5">
            <Trash2 size={14} />
          </button>
        )}
      </div>

      {kpis && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <HeroValue label="Força máxima" value={fmt(kpis.forca_max_kN, 2)} unit="kN" sub={`${fmt(kpis.forca_max_N, 0)} N`} cor="text-rupture" />
          <HeroValue label="Resistência à flexão σfM" value={fmt(kpis.tensao_flexao_max_MPa, 1)} unit="MPa" cor="text-sky-300" />
          <HeroValue label="Módulo de flexão Ef" value={fmt(kpis.modulo_flexao_GPa, 2)} unit="GPa"
            sub={kpis.r2_elastico != null ? `R² = ${kpis.r2_elastico.toFixed(4)}` : undefined} cor="text-emerald-300" />
          <HeroValue label="Deflexão máxima" value={fmt(kpis.deflexao_max_mm, 2)} unit="mm"
            sub={kpis.ruptura_detectada ? "ruptura detectada" : "sem ruptura"} cor="text-violet-300" />
        </div>
      )}

      {kpis && curvas && (
        <div className="flex gap-4 items-start">
          {/* Gráfico principal + miniaturas */}
          <div className="flex-1 min-w-0 space-y-3">
            <div className="rounded-xl border border-border bg-surface px-4 pt-3 pb-3">
              <div className="flex items-baseline gap-3 mb-2 flex-wrap">
                <p className="text-sm font-semibold text-white">{CHARTS.find((c) => c.key === ativo)!.label}</p>
                <p className="text-xs text-muted">{CHARTS.find((c) => c.key === ativo)!.sub}</p>
                {ativo === "ss" && curvas.trecho_elastico?.ss && (
                  <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full">
                    - - reta elástica: Ef = {fmt(curvas.trecho_elastico.ss.inclinacao, 0)} MPa · R² = {curvas.trecho_elastico.ss.r2.toFixed(4)}
                  </span>
                )}
                {ativo === "fd" && curvas.trecho_elastico?.fd && (
                  <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full">
                    - - reta elástica: k = {fmt(curvas.trecho_elastico.fd.inclinacao, 1)} N/mm · R² = {curvas.trecho_elastico.fd.r2.toFixed(4)}
                  </span>
                )}
                <button onClick={() => setMostrarFases((v) => !v)}
                  className={clsx(
                    "ml-auto flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border transition-colors",
                    mostrarFases ? "border-accent/40 text-accent bg-accent/10" : "border-border text-muted",
                  )}>
                  <Layers size={10} /> Estágios
                </button>
              </div>
              <div style={{ height: 420 }}>{renderChart(ativo, curvas, 420, false, mostrarFases)}</div>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {CHARTS.filter((c) => c.key !== ativo).map((c) => (
                <button key={c.key} onClick={() => setAtivo(c.key)}
                  className="group rounded-xl border border-border bg-surface hover:border-accent/50 transition-all text-left overflow-hidden flex flex-col">
                  <div className="pointer-events-none select-none p-3 flex-1">{renderChart(c.key, curvas, 110, true)}</div>
                  <div className="px-3 py-2 border-t border-border/50">
                    <p className="text-xs font-semibold text-muted group-hover:text-white transition-colors leading-tight">{c.label}</p>
                    <p className="text-[10px] text-muted/50 leading-tight mt-0.5">{c.sub}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Coluna direita */}
          <div className="w-[276px] flex-shrink-0 flex flex-col gap-3">
            {qualidade && <QualidadePanel qualidade={qualidade} />}

            <div className="rounded-xl border border-border bg-surface p-3">
              <SectionLabel>Trecho elástico · regressão</SectionLabel>
              <div className="grid grid-cols-2 gap-2">
                <KPICard compact highlight label="Ef (reta)"
                  value={curvas.trecho_elastico?.ss ? `${fmt(curvas.trecho_elastico.ss.inclinacao, 0)} MPa` : "—"} />
                <KPICard compact label="R²"
                  value={kpis.r2_elastico != null ? kpis.r2_elastico.toFixed(4) : "—"}
                  sub={kpis.pontos_trecho_elastico != null ? `${kpis.pontos_trecho_elastico} pontos` : undefined} />
                <KPICard compact label="Rigidez k"
                  value={curvas.trecho_elastico?.fd ? `${fmt(curvas.trecho_elastico.fd.inclinacao, 1)} N/mm` : "—"} />
                <KPICard compact label="Trecho εf"
                  value={curvas.trecho_elastico?.ss ? `${fmt(curvas.trecho_elastico.ss.x_ini, 4)}–${fmt(curvas.trecho_elastico.ss.x_fim, 4)}` : "—"} />
              </div>
            </div>

            {(curvas.fases?.length ?? 0) > 0 && (
              <div className="rounded-xl border border-border bg-surface p-3">
                <SectionLabel>Estágios do ensaio</SectionLabel>
                <div className="space-y-1">
                  {curvas.fases!.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-[11px]">
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: CORES[f.fase] ?? "#64748b" }} />
                      <span className="text-slate-300 flex-1 truncate">{f.rotulo}</span>
                      <span className="font-mono text-muted">
                        {f.t_ini != null && f.t_fim != null ? `${fmt(f.t_ini, 1)}–${fmt(f.t_fim, 1)} s` : `${f.n_pontos} pts`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Resultados kpis={kpis} />
          </div>
        </div>
      )}
    </div>
  );
}

function Resultados({ kpis }: { kpis: KPIsFlexao }) {
  return (
    <>
      <div className="rounded-xl border border-border bg-surface p-3">
        <SectionLabel>Resultados</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <KPICard compact highlight label="Força Máx." value={`${fmt(kpis.forca_max_kN, 2)} kN`} sub={`${fmt(kpis.forca_max_N, 0)} N`} />
          <KPICard compact highlight label="σfM" value={`${fmt(kpis.tensao_flexao_max_MPa)} MPa`} />
          <KPICard compact label="Módulo Ef" value={`${fmt(kpis.modulo_flexao_MPa, 0)} MPa`} sub={`${fmt(kpis.modulo_flexao_GPa, 2)} GPa`} />
          <KPICard compact label="Ef cordal" value={kpis.modulo_cordal_MPa != null ? `${fmt(kpis.modulo_cordal_MPa, 0)} MPa` : "—"} />
          <KPICard compact label="Deflexão máx." value={`${fmt(kpis.deflexao_max_mm)} mm`} sub={`no pico ${fmt(kpis.deflexao_pico_mm)} mm`} />
          <KPICard compact label="εf máx." value={`${fmt(kpis.deform_flexao_max_pct)} %`} />
          <KPICard compact label="Energia" value={`${fmt(kpis.energia_J)} J`} />
          <KPICard compact label="Tempo" value={`${fmt(kpis.tempo_ensaio_s, 1)} s`} sub={`pico em ${fmt(kpis.tempo_pico_s, 1)} s`} />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-3">
        <SectionLabel>Corpo de prova · {kpis.norma}</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <MiniStat formula="b" label="Largura" value={kpis.largura_mm != null ? `${fmt(kpis.largura_mm, 1)} mm` : "—"} />
          <MiniStat formula="h" label="Espessura" value={kpis.espessura_mm != null ? `${fmt(kpis.espessura_mm, 1)} mm` : "—"} />
          <MiniStat formula="L" label="Entre apoios" value={kpis.span_mm != null ? `${fmt(kpis.span_mm, 1)} mm` : "—"} />
          <MiniStat formula="dF/dt" label="Taxa carg." value={`${fmt(kpis.taxa_carregamento_N_s, 1)} N/s`} />
        </div>
      </div>
    </>
  );
}
