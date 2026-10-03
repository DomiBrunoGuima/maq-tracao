import { X } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { getCurvas, getEnsaio, getKPIs } from "../../api/client";

const PALETTE = [
  "#00d4ff", "#ff6b35", "#a78bfa", "#34d399",
  "#f59e0b", "#f472b6", "#60a5fa",
];

const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !Number.isFinite(n) ? "—" : n.toFixed(d);

interface Props {
  ids: number[];
  onRemove: (id: number) => void;
}

function useComparisonData(ids: number[]) {
  const ensaios = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["ensaio", id],
      queryFn: () => getEnsaio(id),
      enabled: id !== null,
    })),
  });

  const curvas = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["curvas", id],
      queryFn: () => getCurvas(id),
      enabled: id !== null,
    })),
  });

  const kpis = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["kpis", id],
      queryFn: () => getKPIs(id),
      enabled: id !== null,
    })),
  });

  return { ensaios, curvas, kpis };
}

export default function ComparisonView({ ids, onRemove }: Props) {
  const { ensaios, curvas, kpis } = useComparisonData(ids);

  if (ids.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <p className="text-lg font-semibold text-white mb-2">Comparação de Ensaios</p>
        <p className="text-sm text-muted max-w-xs">
          Selecione ensaios na barra lateral clicando em "+ Comparar" para adicioná-los à comparação.
        </p>
      </div>
    );
  }

  const isLoading = [...ensaios, ...curvas, ...kpis].some((q) => q.isLoading);

  // Build series list from fetched data
  const series = ids.map((id, i) => {
    const ensaio = ensaios[i]?.data ?? null;
    const curva = curvas[i]?.data ?? null;
    return {
      id,
      color: PALETTE[i % PALETTE.length],
      label: ensaio?.nome || ensaio?.filename || `#${id}`,
      failed: Boolean(ensaios[i]?.isError || curvas[i]?.isError || kpis[i]?.isError),
      // ε vem adimensional; o gráfico (e o relatório) mostram em %
      stressStrain: curva?.stress_strain.map((p) => ({
        ...p,
        Deform_pct: typeof p.Deform_Along === "number" ? p.Deform_Along * 100 : null,
      })) ?? null,
      curva,
      kpi: kpis[i]?.data ?? null,
    };
  });
  const failed = series.filter((s) => s.failed);

  return (
    <div className="p-6 space-y-6 overflow-auto">
      <h1 className="text-xl font-semibold text-white">Comparação de Ensaios</h1>

      {/* Legend tags */}
      <div className="flex flex-wrap gap-2">
        {series.map(({ id, color, label }) => (
          <div
            key={id}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm"
            style={{ borderColor: color, backgroundColor: `${color}18` }}
          >
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span style={{ color }}>{label}</span>
            <button
              onClick={() => onRemove(id)}
              className="text-muted hover:text-white ml-1 transition-colors"
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>

      {isLoading && (
        <p className="text-sm text-muted animate-pulse">Carregando dados...</p>
      )}

      {failed.length > 0 && (
        <p className="text-sm text-red-400">
          Não foi possível carregar: {failed.map((s) => s.label).join(", ")}. Verifique se o ensaio
          ainda existe ou tente reimportá-lo.
        </p>
      )}

      {/* Stress-strain chart */}
      {!isLoading && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-1">
            Curvas Tensão × Deformação — σ-ε
          </h2>
          <p className="text-xs text-muted mb-4">Sobreposição de todos os ensaios selecionados</p>
          <ResponsiveContainer width="100%" height={380}>
            <LineChart margin={{ top: 5, right: 24, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2435" />
              <XAxis
                dataKey="Deform_pct"
                type="number"
                domain={["auto", "auto"]}
                tickFormatter={(v) => Number(v).toFixed(1)}
                tick={{ fill: "#64748b", fontSize: 10 }}
                stroke="#2a2d3e"
                label={{
                  value: "Deformação ε (%)",
                  position: "insideBottom",
                  offset: -12,
                  fill: "#64748b",
                  fontSize: 11,
                }}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 10 }}
                stroke="#2a2d3e"
                label={{
                  value: "σ (MPa)",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#64748b",
                  fontSize: 11,
                }}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1d27",
                  border: "1px solid #2a2d3e",
                  borderRadius: 8,
                  fontFamily: "monospace",
                  fontSize: 11,
                }}
                labelFormatter={(v) => `ε = ${Number(v).toFixed(2)} %`}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#94a3b8", paddingTop: 8 }}
              />
              {series.map(({ id, color, label, stressStrain }) => {
                if (!stressStrain) return null;
                return (
                  <Line
                    key={id}
                    data={stressStrain}
                    dataKey="Tensao_Pa"
                    name={label}
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                    type="monotone"
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Force-displacement chart */}
      {!isLoading && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Força × Deslocamento
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart margin={{ top: 5, right: 24, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2435" />
              <XAxis
                dataKey="Deslocamento"
                type="number"
                domain={["auto", "auto"]}
                tickFormatter={(v) => `${Number(v).toFixed(1)}`}
                tick={{ fill: "#64748b", fontSize: 10 }}
                stroke="#2a2d3e"
                label={{ value: "d (mm)", position: "insideBottom", offset: -12, fill: "#64748b", fontSize: 11 }}
              />
              <YAxis
                tickFormatter={(v) => (Math.abs(Number(v)) >= 1000 ? `${(Number(v) / 1000).toFixed(1)}k` : Number(v).toFixed(0))}
                tick={{ fill: "#64748b", fontSize: 10 }}
                stroke="#2a2d3e"
                label={{ value: "F (N)", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3e", borderRadius: 8, fontFamily: "monospace", fontSize: 11 }}
                labelFormatter={(v) => `d = ${Number(v).toFixed(2)} mm`}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8", paddingTop: 8 }} />
              {series.map(({ id, color, label, curva }) => {
                if (!curva) return null;
                return (
                  <Line
                    key={id}
                    data={curva.force_displacement}
                    dataKey="Forca_N"
                    name={label}
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    type="monotone"
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* KPI comparison table */}
      {!isLoading && (
        <div className="rounded-xl border border-border bg-surface p-5 overflow-x-auto">
          <h2 className="text-sm font-semibold text-white mb-4">Tabela Comparativa de KPIs</h2>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-3 py-2 text-muted font-medium">Ensaio</th>
                <th className="px-3 py-2 text-muted font-medium text-right">Fmax (N)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">σmax (MPa)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">E (MPa)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">δ (%)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">d (mm)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">Energia (J)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">k (N/mm)</th>
                <th className="px-3 py-2 text-muted font-medium text-right">t Fmax (s)</th>
              </tr>
            </thead>
            <tbody>
              {series.map(({ id, color, label, kpi }) => {
                if (!kpi) return null;
                // Mesmos valores do relatório: prefere Fmax/A e d/L₀ quando houver A e L₀
                const tensao = kpi.tensao_max_calc_MPa ?? kpi.tensao_max_MPa;
                const along = kpi.alonga_calc_pct ?? kpi.alonga_ruptura_pct;
                return (
                  <tr key={id} className="border-t border-border/50 hover:bg-border/20 transition-colors">
                    <td className="px-3 py-2 font-mono font-semibold" style={{ color }}>
                      {label}
                    </td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.forca_max_N, 0)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(tensao)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.modulo_elasticidade_MPa, 1)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(along)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.deslocamento_max_mm)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.energia_J, 2)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.rigidez_N_mm, 1)}</td>
                    <td className="px-3 py-2 font-mono text-right text-slate-300">{fmt(kpi.tempo_ruptura_s, 1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
