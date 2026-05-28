import {
  Area,
  CartesianGrid,
  ComposedChart,
  Customized,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DataPoint, RupturePoint } from "../../types";
import { RuptureMarker } from "./RuptureMarker";
import { ORDERED_STAGES, STAGE_COLORS, STAGE_LABELS, splitByStage } from "./stageConfig";

const Tooltip_ = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2.5 shadow-2xl text-xs font-mono">
      <p className="text-muted mb-2 pb-1.5 border-b border-border/60">
        t = <span className="text-white">{Number(label).toFixed(0)} s</span>
      </p>
      {payload.map((p: any) => (
        <div key={p.dataKey + p.name} className="flex items-center gap-2 mt-1">
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: p.stroke ?? p.color }} />
          <span className="text-slate-400">{p.name}</span>
          <span className="text-white font-semibold ml-auto pl-4">{Number(p.value).toFixed(2)} MPa</span>
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
}

export default function StressTimeChart({ data, rupture, height = 240, onPointClick, thumbnail = false }: Props) {
  const groups = splitByStage(data);
  const active = ORDERED_STAGES.filter((s) => groups[s].length > 1);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart
        margin={thumbnail ? { top: 4, right: 4, left: 0, bottom: 4 } : { top: 8, right: 24, left: 4, bottom: 20 }}
        onClick={(e: any) => { const pt = e?.activePayload?.[0]?.payload; if (pt && onPointClick) onPointClick(pt); }}
        style={{ cursor: onPointClick ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
        <XAxis
          dataKey="elapsed_seconds"
          type="number"
          domain={["auto", "auto"]}
          hide={thumbnail}
          tickFormatter={(v) => `${Number(v).toFixed(0)}s`}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={thumbnail ? undefined : { value: "Tempo (s)", position: "insideBottom", offset: -12, fill: "#475569", fontSize: 10 }}
        />
        <YAxis
          hide={thumbnail}
          tickFormatter={(v) => Number(v).toFixed(0)}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={thumbnail ? undefined : { value: "σ (MPa)", angle: -90, position: "insideLeft", offset: 10, fill: "#475569", fontSize: 10 }}
        />
        {!thumbnail && <Tooltip content={<Tooltip_ />} />}
        {!thumbnail && <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: 10, color: "#64748b", paddingBottom: 6 }} />}

        {active.map((stage) => (
          <Area
            key={stage}
            data={groups[stage]}
            dataKey="Tensao_Pa"
            name={STAGE_LABELS[stage]}
            stroke={STAGE_COLORS[stage]}
            strokeWidth={2}
            fill={STAGE_COLORS[stage]}
            fillOpacity={0.07}
            dot={false}
            type="monotone"
            isAnimationActive={!thumbnail}
          />
        ))}

        {!thumbnail && (
          <Line
            data={data}
            dataKey="Tensao_Max"
            name="σmax envelope"
            stroke="#64748b"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
            type="monotone"
            isAnimationActive={false}
            legendType="plainline"
          />
        )}

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
