import { useState } from "react";
import { X } from "lucide-react";
import { clsx } from "clsx";
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
import { getCurvas, getCurvasFlexao, getEnsaio, getEnsaioFlexao, getKPIs, getKPIsFlexao } from "../../api/client";
import type { KPIs, KPIsFlexao, TipoEnsaio } from "../../types";

const PALETTE = [
  "#00d4ff", "#ff6b35", "#a78bfa", "#34d399",
  "#f59e0b", "#f472b6", "#60a5fa",
];

const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !Number.isFinite(n) ? "—" : n.toFixed(d);

/** Média, desvio padrão amostral (n−1) e coeficiente de variação. */
function estatisticas(vals: (number | null | undefined)[]) {
  const v = vals.filter((x): x is number => x != null && Number.isFinite(x));
  if (v.length === 0) return { media: null, dp: null, cv: null, n: 0 };
  const media = v.reduce((a, b) => a + b, 0) / v.length;
  const dp = v.length > 1 ? Math.sqrt(v.reduce((a, b) => a + (b - media) ** 2, 0) / (v.length - 1)) : null;
  const cv = dp != null && media !== 0 ? (dp / Math.abs(media)) * 100 : null;
  return { media, dp, cv, n: v.length };
}


// Colunas da tabela comparativa: [título, valor do KPI, casas decimais]
type Coluna<K> = [string, (k: K) => number | null | undefined, number];

const COLUNAS_TRACAO: Coluna<KPIs>[] = [
  ["Fmax (N)", (k) => k.forca_max_N, 0],
  // Mesmos valores do relatório: prefere Fmax/A e d/L₀ quando houver A e L₀
  ["σmax (MPa)", (k) => k.tensao_max_calc_MPa ?? k.tensao_max_MPa, 2],
  ["E (MPa)", (k) => k.modulo_trecho_elastico_MPa ?? k.modulo_elasticidade_MPa, 1],
  ["R²", (k) => k.r2_elastico, 4],
  ["Rp0,2 (MPa)", (k) => k.tensao_rp02_MPa, 2],
  ["δ (%)", (k) => k.alonga_calc_pct ?? k.alonga_ruptura_pct, 2],
  ["d (mm)", (k) => k.deslocamento_max_mm, 2],
  ["Energia (J)", (k) => k.energia_J, 2],
  ["k (N/mm)", (k) => k.rigidez_N_mm, 1],
  ["t Fmax (s)", (k) => k.tempo_ruptura_s, 1],
];

const COLUNAS_FLEXAO: Coluna<KPIsFlexao>[] = [
  ["Fmax (N)", (k) => k.forca_max_N, 0],
  ["σfM (MPa)", (k) => k.tensao_flexao_max_MPa, 2],
  ["Ef (MPa)", (k) => k.modulo_flexao_MPa, 1],
  ["Ef cordal (MPa)", (k) => k.modulo_cordal_MPa, 1],
  ["R²", (k) => k.r2_elastico, 4],
  ["εf máx. (%)", (k) => k.deform_flexao_max_pct, 2],
  ["δ pico (mm)", (k) => k.deflexao_pico_mm, 2],
  ["δ máx. (mm)", (k) => k.deflexao_max_mm, 2],
  ["Energia (J)", (k) => k.energia_J, 2],
  ["t Fmax (s)", (k) => k.tempo_pico_s, 1],
];

// O que muda entre tração e flexão: de onde vêm os dados, colunas das curvas e rótulos
const PERFIL = {
  tracao: {
    chave: "", getEnsaio, getCurvas: getCurvas as (id: number) => Promise<any>, getKPIs: getKPIs as (id: number) => Promise<any>,
    colunas: COLUNAS_TRACAO as Coluna<any>[], xSS: "Deform_Along", ySS: "Tensao_Pa",
    tituloSS: "Curvas Tensão × Deformação — σ-ε", xLabelSS: "Deformação ε (%)", yLabelSS: "σ (MPa)", eps: "ε",
    tituloFD: "Força × Deslocamento", d: "d",
  },
  flexao: {
    chave: "flexao", getEnsaio: getEnsaioFlexao, getCurvas: getCurvasFlexao as (id: number) => Promise<any>, getKPIs: getKPIsFlexao as (id: number) => Promise<any>,
    colunas: COLUNAS_FLEXAO as Coluna<any>[], xSS: "Deform_Flexao", ySS: "Tensao_Flexao",
    tituloSS: "Curvas Tensão × Deformação de flexão — σf-εf", xLabelSS: "Deformação εf (%)", yLabelSS: "σf (MPa)", eps: "εf",
    tituloFD: "Força × Deflexão", d: "δ",
  },
};

interface Props {
  ids: number[];
  flexaoIds?: number[];
  onRemove: (id: number) => void;
  onRemoveFlexao?: (id: number) => void;
}

function useComparisonData(ids: number[], modo: TipoEnsaio) {
  const p = PERFIL[modo];
  // Mesmas chaves de cache das telas de resultado de cada tipo
  const key = (k: string, id: number) => (p.chave ? [p.chave, k, id] : [k, id]);
  const ensaios = useQueries({
    queries: ids.map((id) => ({ queryKey: key("ensaio", id), queryFn: () => p.getEnsaio(id) })),
  });
  const curvas = useQueries({
    queries: ids.map((id) => ({ queryKey: key("curvas", id), queryFn: () => p.getCurvas(id) })),
  });
  const kpis = useQueries({
    queries: ids.map((id) => ({ queryKey: key("kpis", id), queryFn: () => p.getKPIs(id) })),
  });
  return { ensaios, curvas, kpis };
}

export default function ComparisonView({ ids, flexaoIds = [], onRemove, onRemoveFlexao }: Props) {
  const [aba, setAba] = useState<TipoEnsaio>(ids.length === 0 && flexaoIds.length > 0 ? "flexao" : "tracao");
  const modo: TipoEnsaio = flexaoIds.length === 0 ? "tracao" : ids.length === 0 ? "flexao" : aba;

  if (ids.length === 0 && flexaoIds.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <p className="text-lg font-semibold text-white mb-2">Comparação de Ensaios</p>
        <p className="text-sm text-muted max-w-xs">
          Selecione ensaios na barra lateral clicando em "+ Comparar" para adicioná-los à comparação.
          Ensaios de tração e de flexão são comparados separadamente.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div className="flex items-center gap-4 flex-wrap">
        <h1 className="text-xl font-semibold text-white">Comparação de Ensaios</h1>
        {ids.length > 0 && flexaoIds.length > 0 && (
          <div className="flex rounded-lg border border-border overflow-hidden text-xs">
            {(["tracao", "flexao"] as const).map((m) => (
              <button key={m} onClick={() => setAba(m)}
                className={clsx("px-3 py-1.5 transition-colors",
                  modo === m ? "bg-accent text-bg font-semibold" : "text-muted hover:text-white")}>
                {m === "tracao" ? `Tração (${ids.length})` : `Flexão (${flexaoIds.length})`}
              </button>
            ))}
          </div>
        )}
      </div>
      {modo === "flexao"
        ? <Comparacao key="flexao" modo="flexao" ids={flexaoIds} onRemove={onRemoveFlexao ?? (() => {})} />
        : <Comparacao key="tracao" modo="tracao" ids={ids} onRemove={onRemove} />}
    </div>
  );
}

function Comparacao({ ids, modo, onRemove }: { ids: number[]; modo: TipoEnsaio; onRemove: (id: number) => void }) {
  const p = PERFIL[modo];
  const COLUNAS = p.colunas;
  const { ensaios, curvas, kpis } = useComparisonData(ids, modo);

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
      stressStrain: curva?.stress_strain.map((pt: Record<string, any>) => ({
        ...pt,
        Deform_pct: typeof pt[p.xSS] === "number" ? pt[p.xSS] * 100 : null,
      })) ?? null,
      curva,
      kpi: kpis[i]?.data ?? null,
    };
  });
  const failed = series.filter((s) => s.failed);
  const kpisOk = series.map((s) => s.kpi).filter((k) => k != null);
  const stats = kpisOk.length > 1 ? COLUNAS.map(([, get]) => estatisticas(kpisOk.map(get))) : null;

  return (
    <>
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
            {p.tituloSS}
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
                  value: p.xLabelSS,
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
                  value: p.yLabelSS,
                  angle: -90,
                  position: "insideLeft",
                  fill: "#64748b",
                  fontSize: 11,
                }}
              />
              <Tooltip
                contentStyle={{
                  background: "rgb(var(--surface))",
                  border: "1px solid rgb(var(--border))",
                  borderRadius: 8,
                  fontFamily: "monospace",
                  fontSize: 11,
                }}
                labelFormatter={(v) => `${p.eps} = ${Number(v).toFixed(2)} %`}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "rgb(var(--slate-400))", paddingTop: 8 }}
              />
              {series.map(({ id, color, label, stressStrain }) => {
                if (!stressStrain) return null;
                return (
                  <Line
                    key={id}
                    data={stressStrain}
                    dataKey={p.ySS}
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
            {p.tituloFD}
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
                label={{ value: `${p.d} (mm)`, position: "insideBottom", offset: -12, fill: "#64748b", fontSize: 11 }}
              />
              <YAxis
                tickFormatter={(v) => (Math.abs(Number(v)) >= 1000 ? `${(Number(v) / 1000).toFixed(1)}k` : Number(v).toFixed(0))}
                tick={{ fill: "#64748b", fontSize: 10 }}
                stroke="#2a2d3e"
                label={{ value: "F (N)", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: "rgb(var(--surface))", border: "1px solid rgb(var(--border))", borderRadius: 8, fontFamily: "monospace", fontSize: 11 }}
                labelFormatter={(v) => `${p.d} = ${Number(v).toFixed(2)} mm`}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "rgb(var(--slate-400))", paddingTop: 8 }} />
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
          <h2 className="text-sm font-semibold text-white mb-4">Tabela Comparativa · Média e Desvio Padrão</h2>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-3 py-2 text-muted font-medium">Ensaio</th>
                {COLUNAS.map(([t]) => (
                  <th key={t} className="px-3 py-2 text-muted font-medium text-right">{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {series.map(({ id, color, label, kpi }) => {
                if (!kpi) return null;
                return (
                  <tr key={id} className="border-t border-border/50 hover:bg-border/20 transition-colors">
                    <td className="px-3 py-2 font-mono font-semibold" style={{ color }}>
                      {label}
                    </td>
                    {COLUNAS.map(([t, get, d]) => (
                      <td key={t} className="px-3 py-2 font-mono text-right text-slate-300">{fmt(get(kpi), d)}</td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
            {stats && (
              <tfoot className="border-t-2 border-border">
                <tr className="bg-accent/5">
                  <td className="px-3 py-2 font-semibold text-accent">Média (n = {kpisOk.length})</td>
                  {stats.map((st, i) => (
                    <td key={i} className="px-3 py-2 font-mono text-right font-bold text-white">{fmt(st.media, COLUNAS[i][2])}</td>
                  ))}
                </tr>
                <tr>
                  <td className="px-3 py-2 font-semibold text-slate-300">Desvio padrão</td>
                  {stats.map((st, i) => (
                    <td key={i} className="px-3 py-2 font-mono text-right text-slate-300">{fmt(st.dp, COLUNAS[i][2])}</td>
                  ))}
                </tr>
                <tr>
                  <td className="px-3 py-2 font-semibold text-muted">CV (%)</td>
                  {stats.map((st, i) => (
                    <td key={i} className="px-3 py-2 font-mono text-right text-muted">{fmt(st.cv, 1)}</td>
                  ))}
                </tr>
              </tfoot>
            )}
          </table>
          {kpisOk.length === 1 && (
            <p className="text-xs text-muted mt-3">Adicione mais ensaios para ver média e desvio padrão.</p>
          )}
        </div>
      )}
    </>
  );
}
