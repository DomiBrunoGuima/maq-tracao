import { useState, useMemo, useEffect, useRef } from "react";
import { FileText, X as XIcon, MousePointerClick } from "lucide-react";
import { clsx } from "clsx";
import type { ChartData, DataPoint, RupturePoint } from "../../types";
import { useKPIs, useCurvas, useEnsaio, useParametrosIHM } from "../../hooks/useEnsaios";
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

function renderChart(
  key: ChartKey,
  curvas: ChartData,
  height: number,
  onPointClick?: (pt: DataPoint) => void,
  thumbnail = false,
) {
  const p = { height, onPointClick, thumbnail };
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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest mb-2.5">
      {children}
    </p>
  );
}

function Divider() {
  return <hr className="border-border/60 my-3" />;
}

function MiniStat({
  formula, label, value, note, highlight,
}: {
  formula: string; label: string; value: string; note?: string; highlight?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-[#0d1020] p-2.5 flex flex-col gap-0.5">
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
  const chartBodyRef                      = useRef<HTMLDivElement>(null);

  const { data: ensaio }                           = useEnsaio(ensaioId);
  const { data: kpis, isLoading: kpisLoading }     = useKPIs(ensaioId);
  const { data: curvas, isLoading: curvasLoading } = useCurvas(ensaioId);
  const { data: ihmParams }                        = useParametrosIHM(ensaioId);
  const { data: config }                           = useConfig();

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

  const fmt = (n: number, d = 2) => n.toFixed(d);

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
        </div>
        <button
          onClick={() => setShowReport(true)}
          className="flex-shrink-0 flex items-center gap-2 px-4 py-1.5 bg-accent/10
                     hover:bg-accent/20 text-accent rounded-lg text-xs font-medium transition-colors"
        >
          <FileText size={13} />
          Gerar Relatório
        </button>
      </header>

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
              {renderChart(activeChart, curvas, chartH, setSelectedPoint)}
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
                    className="flex items-center gap-2 bg-[#0d1020] border border-border/40
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
                value={`${(kpis.cv_modulo * 100).toFixed(2)} %`} />
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
