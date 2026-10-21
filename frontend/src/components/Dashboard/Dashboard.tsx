import { useState, useMemo, useEffect, useRef } from "react";
import { FileText, X as XIcon, MousePointerClick, ClipboardList, Layers } from "lucide-react";
import { clsx } from "clsx";
import { ReferenceArea, ReferenceLine } from "recharts";
import type { ChartData, DataPoint } from "../../types";
import { useKPIs, useCurvas, useEnsaio, useParametrosIHM, useQualidade } from "../../hooks/useEnsaios";
import QualidadePanel from "./QualidadePanel";
import DadosTesteModal from "./DadosTesteModal";
import { useConfig } from "../../hooks/useConfig";
import KPICard from "./KPICard";
import SimpleLineChart from "../Charts/SimpleLineChart";
import ReportGenerator from "../Reports/ReportGenerator";
import PointInspectorModal from "../Charts/PointInspectorModal";

// ── chart registry ────────────────────────────────────────────

type ChartKey = "ss" | "fd" | "ft" | "em" | "st";

const CHARTS: { key: ChartKey; label: string; sub: string }[] = [
  { key: "ss", label: "σ-ε",   sub: "Tensão × Deformação" },
  { key: "fd", label: "F × d", sub: "Força × Deslocamento" },
  { key: "ft", label: "F × t", sub: "Força × Tempo" },
  { key: "em", label: "E × t", sub: "Módulo × Tempo" },
  { key: "st", label: "σ × t", sub: "Tensão × Tempo" },
];

export const FASE_CORES: Record<string, string> = {
  acomodacao: "#94a3b8",
  elastico_linear: "#22c55e",
  escoamento_superior: "#eab308",
  patamar_escoamento: "#f59e0b",
  encruamento: "#3b82f6",
  estriccao: "#a855f7",
  ruptura: "#ef4444",
  pos_ruptura: "#64748b",
};

// Em que coluna cada gráfico tem o eixo x — para posicionar as faixas de estágio
const FASE_X: Record<ChartKey, ["eps" | "d" | "t"]> = {
  ss: ["eps"], fd: ["d"], ft: ["t"], em: ["t"], st: ["t"],
};

/** Faixas coloridas dos estágios e reta de regressão do trecho elástico. */
function chartExtras(key: ChartKey, curvas: ChartData, mostrarFases: boolean): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  if (mostrarFases) {
    const eixo = FASE_X[key][0];
    curvas.fases?.forEach((f, i) => {
      const x1 = f[`${eixo}_ini` as const];
      const x2 = f[`${eixo}_fim` as const];
      if (x1 == null || x2 == null || x1 === x2) return;
      out.push(
        <ReferenceArea key={`fase-${i}`} x1={x1} x2={x2} ifOverflow="hidden"
          fill={FASE_CORES[f.fase] ?? "#64748b"} fillOpacity={0.1} strokeOpacity={0} />,
      );
    });
  }
  const fit = curvas.elastic_fit;
  if (key === "ss" && fit) {
    // Prolonga a reta além do trecho para mostrar onde a curva se afasta dela
    const xs = curvas.stress_strain.map((p) => p.Deform_Along).filter((v): v is number => typeof v === "number");
    const xMax = xs.length ? Math.max(...xs) : fit.eps_fim;
    const x2 = Math.min(xMax, fit.eps_ini + (fit.eps_fim - fit.eps_ini) * 1.6);
    out.push(
      <ReferenceLine key="reg" ifOverflow="hidden" stroke="#f43f5e" strokeWidth={1.5} strokeDasharray="6 4"
        segment={[
          { x: fit.eps_ini, y: fit.inclinacao * fit.eps_ini + fit.intercepto },
          { x: x2, y: fit.inclinacao * x2 + fit.intercepto },
        ]} />,
    );
  }
  return out;
}

function renderChart(
  key: ChartKey,
  curvas: ChartData,
  height: number,
  onPointClick?: (pt: DataPoint) => void,
  thumbnail = false,
  mostrarFases = false,
) {
  const p = { height, onPointClick, thumbnail, extras: thumbnail ? [] : chartExtras(key, curvas, mostrarFases) };
  switch (key) {
    case "ss": return <SimpleLineChart data={curvas.stress_strain}        xKey="Deform_Along"     yKey="Tensao_Pa"   xUnit="" yUnit="MPa" xLabel="ε" yLabel="σ (MPa)" color="#38bdf8" xDecimals={3} {...p} />;
    case "fd": return <SimpleLineChart data={curvas.force_displacement}   xKey="Deslocamento"     yKey="Forca_N"     xUnit="mm" yUnit="N" xLabel="d (mm)" yLabel="F (N)" color="#a78bfa" {...p} />;
    case "ft": return <SimpleLineChart data={curvas.force_time}           xKey="elapsed_seconds"  yKey="Forca_N"     xUnit="s" yUnit="N" xLabel="t (s)" yLabel="F (N)" color="#38bdf8" {...p} />;
    case "em": return <SimpleLineChart data={curvas.elastic_modulus_time} xKey="elapsed_seconds"  yKey="Modulo_Elast" xUnit="s" yUnit="MPa" xLabel="t (s)" yLabel="E (MPa)" color="#f59e0b" {...p} />;
    case "st": return <SimpleLineChart data={curvas.stress_time}          xKey="elapsed_seconds"  yKey="Tensao_Pa"   xUnit="s" yUnit="MPa" xLabel="t (s)" yLabel="σ (MPa)" color="#10b981" {...p} />;
  }
}

// ── helpers ───────────────────────────────────────────────────

function num(pt: DataPoint, key: string): number | null {
  const v = pt[key];
  return typeof v === "number" ? v : null;
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-2.5">
      {children}
    </p>
  );
}

function Divider() {
  return <hr className="border-border/60 my-3" />;
}

export function MiniStat({
  formula, label, value, note, highlight,
}: {
  formula: string; label: string; value: string; note?: string; highlight?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-panel p-2.5 flex flex-col gap-0.5">
      <span className="text-[8px] font-mono text-accent/50 tracking-wide leading-none">{formula}</span>
      <span className="text-[9px] font-semibold text-muted/60 uppercase tracking-wider leading-none mt-0.5">
        {label}
      </span>
      <span className={clsx(
        "text-sm font-mono font-bold leading-none mt-1",
        highlight ? "text-accent" : "text-white"
      )}>
        {value}
      </span>
      {note && <span className="text-[9px] text-muted/50 font-mono leading-tight mt-0.5">{note}</span>}
    </div>
  );
}

export function HeroValue({ label, value, unit, sub, cor }: {
  label: string; value: string; unit: string; sub?: string; cor: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <p className="text-[10px] font-semibold text-muted uppercase tracking-widest">{label}</p>
      <p className={clsx("font-mono font-bold leading-none mt-1.5", cor)}>
        <span className="text-3xl tabular-nums">{value}</span>
        <span className="text-sm ml-1.5 opacity-70">{unit}</span>
      </p>
      {sub && <p className="text-[10px] text-muted font-mono mt-1 truncate">{sub}</p>}
    </div>
  );
}

// ── thumbnail ─────────────────────────────────────────────────

const THUMB_H = 110;

function Thumbnail({
  chartKey, label, sub, curvas, onClick,
}: {
  chartKey: ChartKey;
  label: string;
  sub: string;
  curvas: ChartData;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group rounded-xl border border-border bg-surface hover:border-accent/50
                 hover:bg-surface/80 transition-all text-left overflow-hidden flex flex-col"
    >
      <div className="pointer-events-none select-none p-3 flex-1">
        {renderChart(chartKey, curvas, THUMB_H, undefined, true)}
      </div>
      <div className="px-3 py-2 border-t border-border/50 flex-shrink-0">
        <p className="text-xs font-semibold text-muted group-hover:text-white transition-colors leading-tight">
          {label}
        </p>
        <p className="text-[10px] text-muted/50 group-hover:text-muted/80 transition-colors leading-tight mt-0.5">
          {sub}
        </p>
      </div>
    </button>
  );
}

// ── main component ────────────────────────────────────────────

interface Props {
  ensaioId: number | null;
}

export default function Dashboard({ ensaioId }: Props) {
  const [showReport, setShowReport]       = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<DataPoint | null>(null);
  const [activeChart, setActiveChart]     = useState<ChartKey>("ss");
  const [chartH, setChartH]               = useState(380);
  const [mostrarFases, setMostrarFases]   = useState(true);
  const [editarDados, setEditarDados]     = useState(false);
  const chartBodyRef                      = useRef<HTMLDivElement>(null);

  const { data: ensaio }                           = useEnsaio(ensaioId);
  const { data: kpis, isLoading: kpisLoading }     = useKPIs(ensaioId);
  const { data: curvas, isLoading: curvasLoading } = useCurvas(ensaioId);
  const { data: ihmParams }                        = useParametrosIHM(ensaioId);
  const { data: config }                           = useConfig();
  const { data: qualidade }                        = useQualidade(ensaioId);

  useEffect(() => { setSelectedPoint(null); }, [ensaioId]);

  useEffect(() => {
    const el = chartBodyRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setChartH(Math.max(380, el.clientHeight)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const pt = useMemo(() => {
    if (!selectedPoint) return null;
    const sigma  = num(selectedPoint, "Tensao_Pa");
    const eps    = num(selectedPoint, "Deform_Along");
    const desl   = num(selectedPoint, "Deslocamento");
    const forca  = num(selectedPoint, "Forca_N");
    const t      = num(selectedPoint, "elapsed_seconds");
    const eLocal = sigma != null && eps != null && eps > 0.001 ? sigma / eps : null;
    const stage  = typeof selectedPoint.fase === "string" ? selectedPoint.fase : null;
    return { sigma, eps, desl, forca, t, eLocal, stage };
  }, [selectedPoint]);

  const fmt = (n: number | null | undefined, d = 2) => (n == null || !Number.isFinite(n) ? "—" : n.toFixed(d));

  // ── empty / loading ──

  if (!ensaioId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
          <FileText className="text-accent" size={28} />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">Nenhum ensaio selecionado</h2>
        <p className="text-sm text-muted max-w-xs">
          Selecione um ensaio na barra lateral. Os ensaios são carregados da pasta monitorada.
        </p>
      </div>
    );
  }

  if (kpisLoading || curvasLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted text-sm animate-pulse">Carregando dados...</div>
      </div>
    );
  }

  if (!kpis || !curvas) return null;

  const activeConfig = CHARTS.find((c) => c.key === activeChart)!;
  const thumbCharts  = CHARTS.filter((c) => c.key !== activeChart);

  const realtimeNames = new Set([
    config?.realtime_bit_name,
    config?.realtime_stop_bit_name,
    config?.realtime_forca_name,
    config?.realtime_deslocamento_name,
  ].filter(Boolean) as string[]);

  const ihmParamsFiltered = ihmParams
    ? Object.fromEntries(
        Object.entries(ihmParams.params).filter(([k]) => !realtimeNames.has(k))
      )
    : null;

  // ── render ──

  return (
    // Root: flex column, full viewport height, no overflow
    <div className="h-full flex flex-col overflow-hidden">

      {/* ── Header ──────────────────────────────────────────── */}
      <header className="flex-shrink-0 bg-bg/95 backdrop-blur-sm border-b border-border
                         px-6 py-3 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-white truncate">{ensaio?.nome}</h1>
          <p className="text-xs text-muted mt-0.5">
            {ensaio?.num_amostras} amostras
            {ensaio?.data_ensaio ? ` · ${ensaio.data_ensaio}` : ""}
            {ensaio?.metadata_equipment_id ? ` · ${ensaio.metadata_equipment_id}` : ""}
          </p>
          <p className="text-xs mt-0.5 truncate">
            <span className="text-muted">Cliente </span><span className="text-slate-300">{ensaio?.cliente_nome || "—"}</span>
            <span className="text-muted"> · Amostra </span><span className="text-slate-300">{ensaio?.amostra || "—"}</span>
            <span className="text-muted"> · Norma </span><span className="text-slate-300">{ensaio?.norma || "—"}</span>
            {ensaio?.operador ? <><span className="text-muted"> · Operador </span><span className="text-slate-300">{ensaio.operador}</span></> : null}
          </p>
        </div>
        <button
          onClick={() => setEditarDados(true)}
          className="flex-shrink-0 flex items-center gap-2 px-3 py-1.5 border border-border hover:border-accent
                     text-muted hover:text-white rounded-lg text-xs font-medium transition-colors ml-auto"
        >
          <ClipboardList size={13} />
          Dados do teste
        </button>
        <button
          onClick={() => setShowReport(true)}
          className="flex-shrink-0 flex items-center gap-2 px-4 py-1.5 bg-accent/10
                     hover:bg-accent/20 text-accent rounded-lg text-xs font-medium transition-colors"
        >
          <FileText size={13} />
          Gerar Relatório
        </button>
      </header>

      {/* ── Valores principais em destaque ── */}
      <div className="flex-shrink-0 grid grid-cols-2 lg:grid-cols-4 gap-3 px-4 pt-4">
        <HeroValue label="Força máxima" value={fmt(kpis.forca_max_kN, 2)} unit="kN" sub={`${fmt(kpis.forca_max_N, 0)} N`} cor="text-rupture" />
        <HeroValue label="Tensão máxima" value={fmt(kpis.tensao_max_calc_MPa ?? kpis.tensao_max_MPa, 1)} unit="MPa"
          sub={kpis.tensao_rp02_MPa != null ? `Rp0,2 = ${fmt(kpis.tensao_rp02_MPa, 1)} MPa` : undefined} cor="text-sky-300" />
        <HeroValue label="Módulo de elasticidade"
          value={fmt((kpis.modulo_trecho_elastico_MPa ?? kpis.modulo_elasticidade_MPa) / 1000, 2)} unit="GPa"
          sub={kpis.r2_elastico != null ? `R² = ${kpis.r2_elastico.toFixed(4)}` : undefined} cor="text-emerald-300" />
        <HeroValue label="Alongamento" value={fmt(kpis.alonga_calc_pct ?? kpis.alonga_ruptura_pct, 1)} unit="%"
          sub={kpis.ruptura_detectada ? "na força máxima · ruptura detectada" : "na força máxima"} cor="text-violet-300" />
      </div>

      {/* ── Content area: flex row, fills remaining height ── */}
      <div className="flex-1 min-h-0 flex gap-4 p-4 overflow-hidden">

        {/* ── Left column: chart + thumbnails + IHM params ── */}
        <div className="flex-1 min-w-0 min-h-0 flex flex-col gap-3">

          {/* Active chart card — grows to fill all available space */}
          <div className="flex-1 min-h-[380px] rounded-xl border border-border bg-surface
                          px-4 pt-3 pb-3 flex flex-col overflow-hidden">

            {/* Chart header */}
            <div className="flex items-baseline gap-3 mb-1 flex-shrink-0">
              <p className="text-sm font-semibold text-white">{activeConfig.label}</p>
              <p className="text-xs text-muted">{activeConfig.sub}</p>
              {activeChart === "ss" && curvas.elastic_fit && (
                <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full">
                  - - reta elástica: E = {fmt(curvas.elastic_fit.inclinacao, 0)} MPa · R² = {curvas.elastic_fit.r2.toFixed(4)}
                </span>
              )}
              <button
                onClick={() => setMostrarFases((v) => !v)}
                className={clsx(
                  "flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border transition-colors",
                  mostrarFases ? "border-accent/40 text-accent bg-accent/10" : "border-border text-muted",
                  !pt && "ml-auto",
                )}
              >
                <Layers size={10} /> Estágios
              </button>
              {pt && (
                <div className="ml-auto flex items-center gap-2">
                  <span className="text-[10px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                    {pt.t != null ? `t = ${pt.t.toFixed(1)} s` : "ponto selecionado"}
                    {pt.stage ? ` · ${pt.stage.replace(/_/g, " ")}` : ""}
                  </span>
                  <button onClick={() => setSelectedPoint(null)}
                    className="text-muted/60 hover:text-white transition-colors">
                    <XIcon size={13} />
                  </button>
                </div>
              )}
            </div>

            {/* Interaction hint */}
            <p className="text-[10px] text-muted/50 mb-2 flex items-center gap-1.5 flex-shrink-0">
              <MousePointerClick size={10} className="flex-shrink-0" />
              {pt
                ? "Clique em outro ponto · × para limpar"
                : "Clique em qualquer ponto para ver os cálculos detalhados."}
            </p>

            {/* Chart body — measured by ResizeObserver, height drives ResponsiveContainer */}
            <div ref={chartBodyRef} className="flex-1 min-h-0 overflow-hidden">
              {renderChart(activeChart, curvas, chartH, setSelectedPoint, false, mostrarFases)}
            </div>
          </div>

          {/* Thumbnail row — fixed height, never shrinks */}
          <div className="flex-shrink-0 grid grid-cols-4 gap-2">
            {thumbCharts.map((c) => (
              <Thumbnail
                key={c.key}
                chartKey={c.key}
                label={c.label}
                sub={c.sub}
                curvas={curvas}
                onClick={() => { setActiveChart(c.key); setSelectedPoint(null); }}
              />
            ))}
          </div>

          {/* IHM params bar — fixed height, never shrinks */}
          {ihmParamsFiltered && Object.keys(ihmParamsFiltered).length > 0 && (
            <div className="flex-shrink-0 rounded-xl border border-border bg-surface px-4 py-3">
              <SectionLabel>Parâmetros IHM</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {Object.entries(ihmParamsFiltered).map(([key, val]) => (
                  <div
                    key={key}
                    className="flex items-center gap-2 bg-panel border border-border/40
                               rounded-lg px-3 py-1.5 text-xs font-mono"
                  >
                    <span className="text-muted/60">{key.replace(/_/g, " ")}</span>
                    <span className="text-white font-semibold">{val !== null ? String(val) : "—"}</span>
                  </div>
                ))}
              </div>
              <p className="text-[9px] text-muted/40 font-mono mt-2">
                {ihmParams!.ihm_ip} · {new Date(ihmParams!.captured_at).toLocaleString("pt-BR")}
              </p>
            </div>
          )}
        </div>

        {/* ── Right column: scrolls independently, stretches full height ── */}
        <div className="w-[276px] flex-shrink-0 flex flex-col gap-3 overflow-y-auto pr-0.5">

          {qualidade && <QualidadePanel qualidade={qualidade} />}

          {/* Trecho elástico / regressão */}
          <div className="rounded-xl border border-border bg-surface p-3 flex-shrink-0">
            <SectionLabel>Trecho elástico · regressão</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <KPICard compact highlight label="E (reta)"
                value={kpis.modulo_trecho_elastico_MPa != null ? `${fmt(kpis.modulo_trecho_elastico_MPa, 0)} MPa` : "—"} />
              <KPICard compact label="R²"
                value={kpis.r2_elastico != null ? kpis.r2_elastico.toFixed(4) : "—"}
                sub={kpis.pontos_trecho_elastico != null ? `${kpis.pontos_trecho_elastico.toFixed(0)} pontos` : undefined} />
              <KPICard compact label="Rp0,2"
                value={kpis.tensao_rp02_MPa != null ? `${fmt(kpis.tensao_rp02_MPa)} MPa` : "—"} />
              <KPICard compact label="Trecho ε"
                value={curvas.elastic_fit ? `${fmt(curvas.elastic_fit.eps_ini, 4)}–${fmt(curvas.elastic_fit.eps_fim, 4)}` : "—"} />
            </div>
          </div>

          {/* Estágios do ensaio */}
          {curvas.fases?.length > 0 && (
            <div className="rounded-xl border border-border bg-surface p-3 flex-shrink-0">
              <SectionLabel>Estágios do ensaio</SectionLabel>
              <div className="space-y-1">
                {curvas.fases.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px]">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: FASE_CORES[f.fase] ?? "#64748b" }} />
                    <span className="text-slate-300 flex-1 truncate">{f.rotulo}</span>
                    <span className="font-mono text-muted">
                      {f.t_ini != null && f.t_fim != null ? `${fmt(f.t_ini, 1)}–${fmt(f.t_fim, 1)} s` : `${f.n_pontos.toFixed(0)} pts`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* KPIs card */}
          <div className="rounded-xl border border-border bg-surface p-3 flex-shrink-0">
            <SectionLabel>Resultados</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <KPICard compact highlight label="Força Máx."
                value={`${fmt(kpis.forca_max_kN, 2)} kN`}
                sub={`${fmt(kpis.forca_max_N, 0)} N`} />
              <KPICard compact highlight label="Tensão Máx."
                value={`${fmt(kpis.tensao_max_MPa)} MPa`} />
              <KPICard compact label="Módulo E"
                value={`${fmt(kpis.modulo_elasticidade_MPa, 0)} MPa`}
                sub={`${fmt(kpis.modulo_elasticidade_GPa, 2)} GPa`} />
              <KPICard compact label="Alongamento"
                value={`${fmt(kpis.alonga_ruptura_pct)} %`} />
              <KPICard compact label="Deslocamento"
                value={`${fmt(kpis.deslocamento_max_mm)} mm`} />
              <KPICard compact label="Tempo Ruptura"
                value={`${fmt(kpis.tempo_ruptura_s, 1)} s`} />
              <KPICard compact label="Energia"
                value={`${fmt(kpis.energia_J)} J`}
                sub={`k = ${fmt(kpis.rigidez_N_mm)} N/mm`} />
              <KPICard compact label="Taxa Carg."
                value={`${fmt(kpis.taxa_carregamento_N_s, 1)} N/s`} />
            </div>

            <Divider />

            <SectionLabel>Análise elástica</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <KPICard compact label="σ Escoamento"
                value={kpis.tensao_escoamento_MPa != null
                  ? `${fmt(kpis.tensao_escoamento_MPa)} MPa` : "—"} />
              <KPICard compact label="CV Módulo"
                value={`${fmt(kpis.cv_modulo != null ? kpis.cv_modulo * 100 : null)} %`} />
            </div>
          </div>

          {/* Specimen params card */}
          <div className="rounded-xl border border-border bg-surface p-3 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <SectionLabel>Corpo de prova</SectionLabel>
              {pt && (
                <div className="flex items-center gap-1.5 -mt-1">
                  <span className="text-[9px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded-full">
                    {pt.t != null ? `t=${pt.t.toFixed(1)}s` : "ponto"}
                  </span>
                  <button onClick={() => setSelectedPoint(null)}
                    className="text-muted/60 hover:text-white transition-colors">
                    <XIcon size={10} />
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <MiniStat formula="F/σ" label="Área seção"
                value={kpis.area_secao_mm2 != null ? `${fmt(kpis.area_secao_mm2)} mm²` : "—"} />
              <MiniStat formula="ΔL/ε" label="Comp. inicial"
                value={kpis.comprimento_inicial_mm != null ? `${fmt(kpis.comprimento_inicial_mm)} mm` : "—"} />
              {pt ? (
                <MiniStat formula="σ(pt)" label="Tensão" highlight
                  value={pt.sigma != null ? `${fmt(pt.sigma)} MPa` : "—"}
                  note={pt.forca != null && kpis.area_secao_mm2 != null
                    ? `F/A=${fmt(pt.forca / kpis.area_secao_mm2)} MPa` : undefined} />
              ) : (
                <MiniStat formula="Fmax/A" label="σmax calc."
                  value={kpis.tensao_max_calc_MPa != null ? `${fmt(kpis.tensao_max_calc_MPa)} MPa` : "—"}
                  note={kpis.tensao_max_calc_MPa != null
                    ? `Δ ${fmt(Math.abs(kpis.tensao_max_calc_MPa - kpis.tensao_max_MPa))} MPa` : undefined} />
              )}
              {pt ? (
                <MiniStat formula="ε(pt)" label="Deformação" highlight
                  value={pt.eps != null ? fmt(pt.eps, 4) : pt.desl != null ? `${fmt(pt.desl)} mm` : "—"}
                  note={pt.desl != null ? `d=${fmt(pt.desl)} mm` : undefined} />
              ) : (
                <MiniStat formula="ΔL/L₀" label="A% calc."
                  value={kpis.alonga_calc_pct != null ? `${fmt(kpis.alonga_calc_pct)} %` : "—"}
                  note={kpis.alonga_calc_pct != null
                    ? `Δ ${fmt(Math.abs(kpis.alonga_calc_pct - kpis.alonga_ruptura_pct))} %` : undefined} />
              )}
              {pt ? (
                <MiniStat formula="σ/ε" label="E local" highlight
                  value={pt.eLocal != null ? `${fmt(pt.eLocal, 0)} MPa` : "—"}
                  note={pt.eLocal == null ? "ε insuficiente" : "elástico"} />
              ) : (
                <MiniStat formula="reg." label="E regressão"
                  value={kpis.modulo_regressao_MPa != null ? `${fmt(kpis.modulo_regressao_MPa, 0)} MPa` : "—"}
                  note={kpis.modulo_regressao_MPa != null
                    ? `IHM: ${fmt(kpis.modulo_elasticidade_MPa, 0)} MPa` : undefined} />
              )}
            </div>

            {!pt && (
              <p className="flex items-center gap-1.5 text-[10px] text-muted/40 mt-2">
                <MousePointerClick size={10} />
                clique no gráfico para inspecionar um ponto
              </p>
            )}
          </div>

        </div>
      </div>

      {editarDados && ensaio && (
        <DadosTesteModal ensaio={ensaio} onClose={() => setEditarDados(false)} />
      )}

      {showReport && ensaioId && (
        <ReportGenerator ensaioId={ensaioId} onClose={() => setShowReport(false)} />
      )}

      {selectedPoint && kpis && (
        <PointInspectorModal
          point={selectedPoint}
          kpis={kpis}
          ihmParams={ihmParams}
          onClose={() => setSelectedPoint(null)}
        />
      )}
    </div>
  );
}
