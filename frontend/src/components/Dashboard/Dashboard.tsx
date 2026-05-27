import { useState, useMemo, useEffect } from "react";
import { FileText, X as XIcon } from "lucide-react";
import type { DataPoint } from "../../types";
import { useKPIs, useCurvas, useEnsaio, useParametrosIHM } from "../../hooks/useEnsaios";
import KPICard from "./KPICard";
import StressStrainChart from "../Charts/StressStrainChart";
import ForceDisplacementChart from "../Charts/ForceDisplacementChart";
import ForceTimeChart from "../Charts/ForceTimeChart";
import ElasticModulusChart from "../Charts/ElasticModulusChart";
import StressTimeChart from "../Charts/StressTimeChart";
import ReportGenerator from "../Reports/ReportGenerator";

function SpecimenParam({
  formula,
  label,
  value,
  note,
}: {
  formula: string;
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-[#0d1020] p-3 flex flex-col gap-1">
      <span className="text-[9px] font-mono text-accent/70 tracking-wide">{formula}</span>
      <span className="text-[10px] font-semibold text-muted uppercase tracking-widest leading-none">
        {label}
      </span>
      <span className="text-lg font-mono font-bold text-white leading-none mt-0.5">{value}</span>
      {note && <span className="text-[10px] text-muted/70 font-mono mt-0.5">{note}</span>}
    </div>
  );
}

interface Props {
  ensaioId: number | null;
}

function num(pt: DataPoint, key: string): number | null {
  const v = pt[key];
  return typeof v === "number" ? v : null;
}

export default function Dashboard({ ensaioId }: Props) {
  const [showReport, setShowReport] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<DataPoint | null>(null);
  const { data: ensaio } = useEnsaio(ensaioId);
  const { data: kpis, isLoading: kpisLoading } = useKPIs(ensaioId);
  const { data: curvas, isLoading: curvasLoading } = useCurvas(ensaioId);
  const { data: ihmParams } = useParametrosIHM(ensaioId);

  useEffect(() => { setSelectedPoint(null); }, [ensaioId]);

  const pointParams = useMemo(() => {
    if (!selectedPoint) return null;
    const sigma = num(selectedPoint, "Tensao_Pa");
    const eps   = num(selectedPoint, "Deform_Along");
    const desl  = num(selectedPoint, "Deslocamento");
    const forca = num(selectedPoint, "Forca_N");
    const t     = num(selectedPoint, "elapsed_seconds");
    const eLocal = sigma != null && eps != null && eps > 0.001 ? sigma / eps : null;
    const stage = typeof selectedPoint.fase === "string" ? selectedPoint.fase : null;
    return { sigma, eps, desl, forca, t, eLocal, stage };
  }, [selectedPoint]);

  if (!ensaioId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
          <FileText className="text-accent" size={28} />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">
          Nenhum ensaio selecionado
        </h2>
        <p className="text-sm text-muted max-w-xs">
          Selecione um ensaio na barra lateral ou use "Escanear" para carregar
          arquivos do diretório monitorado.
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

  const fmt = (n: number, d = 2) => n.toFixed(d);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">{ensaio?.nome}</h1>
          <p className="text-sm text-muted mt-0.5">
            {ensaio?.num_amostras} amostras · {ensaio?.data_ensaio} ·{" "}
            {ensaio?.metadata_equipment_id}
          </p>
        </div>
        <button
          onClick={() => setShowReport(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent/10 hover:bg-accent/20
                     text-accent rounded-lg text-sm font-medium transition-colors"
        >
          <FileText size={15} />
          Gerar Relatório
        </button>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        <KPICard
          label="Força Máxima"
          value={`${fmt(kpis.forca_max_kN, 3)} kN`}
          sub={`${fmt(kpis.forca_max_N)} N`}
          highlight
        />
        <KPICard
          label="Tensão Máx."
          value={`${fmt(kpis.tensao_max_MPa)} MPa`}
          highlight
        />
        <KPICard
          label="Módulo E"
          value={`${fmt(kpis.modulo_elasticidade_MPa)} MPa`}
          sub={`${fmt(kpis.modulo_elasticidade_GPa, 4)} GPa`}
        />
        <KPICard
          label="Alongamento"
          value={`${fmt(kpis.alonga_ruptura_pct)} %`}
        />
        <KPICard
          label="Deslocamento"
          value={`${fmt(kpis.deslocamento_max_mm)} mm`}
        />
        <KPICard
          label="Tempo Ruptura"
          value={`${fmt(kpis.tempo_ruptura_s, 1)} s`}
        />
        <KPICard
          label="Energia Absorv."
          value={`${fmt(kpis.energia_J)} J`}
          sub={`k = ${fmt(kpis.rigidez_N_mm)} N/mm`}
        />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <KPICard
          label="Taxa Carregamento"
          value={`${fmt(kpis.taxa_carregamento_N_s)} N/s`}
        />
        <KPICard
          label="Tensão Escoamento (est.)"
          value={
            kpis.tensao_escoamento_MPa != null
              ? `${fmt(kpis.tensao_escoamento_MPa)} MPa`
              : "—"
          }
        />
        <KPICard
          label="CV do Módulo (elástico)"
          value={`${(kpis.cv_modulo * 100).toFixed(2)} %`}
        />
      </div>

      {/* Specimen parameters section */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <div className="flex items-center justify-between mb-0.5">
          <h2 className="text-sm font-semibold text-white">Parâmetros do Corpo de Prova</h2>
          {pointParams && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                ponto selecionado{pointParams.t != null ? ` · t=${pointParams.t.toFixed(1)}s` : ""}
                {pointParams.stage ? ` · ${pointParams.stage.replace(/_/g, " ")}` : ""}
              </span>
              <button
                onClick={() => setSelectedPoint(null)}
                className="text-muted hover:text-white transition-colors"
              >
                <XIcon size={13} />
              </button>
            </div>
          )}
        </div>
        <p className="text-xs text-muted mb-4">
          {pointParams
            ? "Valores no ponto clicado · clique em outro ponto ou × para limpar"
            : "Retrocálculo a partir dos dados medidos · clique em qualquer ponto dos gráficos"}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <SpecimenParam
            formula="σ = F / A"
            label="Área da seção"
            value={kpis.area_secao_mm2 != null ? `${fmt(kpis.area_secao_mm2, 2)} mm²` : "—"}
          />
          <SpecimenParam
            formula="ε = ΔL / L₀"
            label="Comprimento inicial"
            value={kpis.comprimento_inicial_mm != null ? `${fmt(kpis.comprimento_inicial_mm, 2)} mm` : "—"}
          />

          {pointParams ? (
            <SpecimenParam
              formula="σ(ponto)"
              label="Tensão no ponto"
              value={pointParams.sigma != null ? `${fmt(pointParams.sigma, 2)} MPa` : "—"}
              note={
                pointParams.forca != null && kpis.area_secao_mm2 != null
                  ? `F/A = ${fmt(pointParams.forca / kpis.area_secao_mm2, 2)} MPa`
                  : pointParams.t != null ? `t = ${fmt(pointParams.t, 1)} s` : undefined
              }
            />
          ) : (
            <SpecimenParam
              formula="σmáx = Fmáx / A"
              label="Tensão máx. (calc.)"
              value={kpis.tensao_max_calc_MPa != null ? `${fmt(kpis.tensao_max_calc_MPa, 2)} MPa` : "—"}
              note={
                kpis.tensao_max_calc_MPa != null
                  ? `IHM: ${fmt(kpis.tensao_max_MPa, 2)} MPa (Δ ${fmt(Math.abs(kpis.tensao_max_calc_MPa - kpis.tensao_max_MPa), 2)})`
                  : undefined
              }
            />
          )}

          {pointParams ? (
            <SpecimenParam
              formula="ε(ponto)"
              label="Deformação no ponto"
              value={pointParams.eps != null ? fmt(pointParams.eps, 4) : pointParams.desl != null ? `${fmt(pointParams.desl, 2)} mm` : "—"}
              note={
                pointParams.eps != null && pointParams.desl != null
                  ? `d = ${fmt(pointParams.desl, 2)} mm`
                  : pointParams.forca != null ? `F = ${fmt(pointParams.forca, 0)} N` : undefined
              }
            />
          ) : (
            <SpecimenParam
              formula="A% = (Lf−L₀)/L₀×100"
              label="Alongamento (calc.)"
              value={kpis.alonga_calc_pct != null ? `${fmt(kpis.alonga_calc_pct, 2)} %` : "—"}
              note={
                kpis.alonga_calc_pct != null
                  ? `IHM: ${fmt(kpis.alonga_ruptura_pct, 2)} % (Δ ${fmt(Math.abs(kpis.alonga_calc_pct - kpis.alonga_ruptura_pct), 2)})`
                  : undefined
              }
            />
          )}

          {pointParams ? (
            <SpecimenParam
              formula="E = σ/ε (local)"
              label="Módulo local"
              value={pointParams.eLocal != null ? `${fmt(pointParams.eLocal, 1)} MPa` : "—"}
              note={pointParams.eLocal != null ? "válido na região elástica" : "ε insuficiente"}
            />
          ) : (
            <SpecimenParam
              formula="E = σ / ε (regressão)"
              label="Módulo E (regressão)"
              value={kpis.modulo_regressao_MPa != null ? `${fmt(kpis.modulo_regressao_MPa, 1)} MPa` : "—"}
              note={
                kpis.modulo_regressao_MPa != null
                  ? `IHM médio: ${fmt(kpis.modulo_elasticidade_MPa, 1)} MPa`
                  : undefined
              }
            />
          )}
        </div>
      </div>

      {/* IHM process parameters */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold text-white mb-0.5">
          Parâmetros da IHM
        </h2>
        <p className="text-xs text-muted mb-4">
          Capturados via Modbus no momento do ensaio · parâmetros iniciais do processo
        </p>
        {ihmParams ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(ihmParams.params).map(([key, val]) => {
              const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              return (
                <SpecimenParam
                  key={key}
                  formula={key}
                  label={label}
                  value={val !== null ? String(val) : "—"}
                />
              );
            })}
            <div className="col-span-full text-[10px] text-muted/60 font-mono mt-1">
              IHM: {ihmParams.ihm_ip} · capturado em {new Date(ihmParams.captured_at).toLocaleString("pt-BR")}
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted/60 font-mono">
            Nenhum parâmetro capturado — configure o IP da IHM em Configurações.
          </p>
        )}
      </div>

      {/* Main chart: Stress-Strain (large) */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold text-white mb-1">
          Curva Tensão × Deformação — σ-ε
        </h2>
        <p className="text-xs text-muted mb-4">Gráfico principal do ensaio</p>
        <StressStrainChart data={curvas.stress_strain} rupture={curvas.rupture} height={360} onPointClick={setSelectedPoint} />
      </div>

      {/* Secondary charts grid */}
      <div className="grid grid-cols-2 gap-5">
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Força × Deslocamento
          </h2>
          <ForceDisplacementChart data={curvas.force_displacement} rupture={curvas.rupture} onPointClick={setSelectedPoint} />
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Força × Tempo
          </h2>
          <ForceTimeChart data={curvas.force_time} rupture={curvas.rupture} onPointClick={setSelectedPoint} />
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Módulo de Elasticidade × Tempo
          </h2>
          <ElasticModulusChart data={curvas.elastic_modulus_time} rupture={curvas.rupture} onPointClick={setSelectedPoint} />
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Tensão × Tempo (σ e σmax)
          </h2>
          <StressTimeChart data={curvas.stress_time} rupture={curvas.rupture} onPointClick={setSelectedPoint} />
        </div>
      </div>

      {/* Report modal */}
      {showReport && ensaioId && (
        <ReportGenerator
          ensaioId={ensaioId}
          onClose={() => setShowReport(false)}
        />
      )}
    </div>
  );
}
