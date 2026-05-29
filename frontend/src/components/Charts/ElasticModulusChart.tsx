import {
  CartesianGrid,
  ComposedChart,
  Customized,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Line,
} from "recharts";
import { useMemo } from "react";
import type { DataPoint, RupturePoint } from "../../types";
import { RuptureMarker } from "./RuptureMarker";

const Tooltip_ = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2.5 shadow-2xl text-xs font-mono">
      <p className="text-muted mb-1.5 pb-1.5 border-b border-border/60">
        t = <span className="text-white">{Number(label).toFixed(1)} s</span>
      </p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mt-1">
          <span className="w-2 h-0.5 rounded-full flex-shrink-0" style={{ background: p.stroke }} />
          <span className="text-slate-400">{p.name}</span>
          <span className="text-white font-semibold ml-auto pl-4">
            {Number(p.value).toFixed(0)} MPa
          </span>
        </div>
      ))}
    </div>
  );
};

interface Props {
  data: DataPoint[];
  rupture: RupturePoint;
  height?: number;
  onPointClick?: (point: DataPoint) => void;
  thumbnail?: boolean;
  eRegressao?: number | null;
}

export default function ElasticModulusChart({ data, rupture, height = 240, onPointClick, thumbnail = false, eRegressao }: Props) {
  const { filtered, median, yMin, yMax } = useMemo(() => {
    // Extract valid numeric E values from the loading phases only
    const loadingPhases = new Set(["elastico_linear", "escoamento_superior", "patamar_escoamento", "encruamento", "carregamento"]);
    const vals = data
      .filter(pt => loadingPhases.has(String(pt.fase ?? "")))
      .map(pt => typeof pt.Modulo_Elast === "number" ? pt.Modulo_Elast : null)
      .filter((v): v is number => v !== null && v > 0);

    if (!vals.length) return { filtered: data, median: null, yMin: 0, yMax: undefined };

    // IQR-based outlier filter: keep values within [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
    const sorted = [...vals].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    const lo  = Math.max(0, q1 - 1.5 * iqr);
    const hi  = q3 + 1.5 * iqr;
    const med = sorted[Math.floor(sorted.length / 2)];

    const filtered = data.map(pt => {
      const v = typeof pt.Modulo_Elast === "number" ? pt.Modulo_Elast : null;
      if (v === null || v < lo || v > hi) return { ...pt, Modulo_Elast: null };
      return pt;
    });

    return { filtered, median: med, yMin: lo > 0 ? lo * 0.9 : 0, yMax: hi * 1.1 };
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart
        data={filtered}
        margin={thumbnail ? { top: 2, right: 2, left: 0, bottom: 2 } : { top: 6, right: 16, left: 0, bottom: 6 }}
        onClick={(e: any) => { const pt = e?.activePayload?.[0]?.payload; if (pt && onPointClick) onPointClick(pt); }}
        style={{ cursor: onPointClick ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />

        <XAxis
          dataKey="elapsed_seconds"
          type="number"
          domain={[0, "auto"]}
          hide={thumbnail}
          tickFormatter={(v) => `${Number(v).toFixed(0)}s`}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          minTickGap={50}
        />
        <YAxis
          domain={[yMin ?? 0, yMax ?? "auto"]}
          hide={thumbnail}
          width={50}
          tickFormatter={(v) => {
            const n = Number(v);
            if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
            if (n >= 1) return n.toFixed(0);
            return n.toFixed(2);
          }}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
        />

        {/* E regression reference line (preferred) or median fallback */}
        {!thumbnail && (eRegressao != null || median != null) && (
          <ReferenceLine
            y={eRegressao ?? median!}
            stroke="#38bdf8"
            strokeDasharray="6 3"
            strokeWidth={1}
            label={{
              value: eRegressao != null
                ? `E reg. ${eRegressao.toFixed(0)} MPa`
                : `E̅ ${median!.toFixed(0)} MPa`,
              position: "insideTopLeft",
              fill: "#38bdf8",
              fontSize: 9,
            }}
          />
        )}

        {!thumbnail && <Tooltip content={<Tooltip_ />} />}

        <Line
          dataKey="Modulo_Elast"
          name="Módulo de Elasticidade"
          stroke="#38bdf8"
          strokeWidth={thumbnail ? 1.5 : 2}
          dot={false}
          activeDot={thumbnail ? false : { r: 4, strokeWidth: 0, fill: "#38bdf8" }}
          type="monotone"
          connectNulls={true}
          isAnimationActive={!thumbnail}
          legendType="plainline"
        />

        {!thumbnail && (
          <Customized
            component={(p: any) => (
              <RuptureMarker xAxisMap={p.xAxisMap} offset={p.offset} ruptureValue={rupture.elapsed_seconds} />
            )}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
