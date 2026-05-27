import {
  Area,
  CartesianGrid,
  ComposedChart,
  Customized,
  Legend,
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
          <span className="text-white font-semibold ml-auto pl-4">{Number(p.value).toFixed(0)} N</span>
        </div>
      ))}
    </div>
  );
};

interface Props {
  data: DataPoint[];
  rupture: RupturePoint;
  onPointClick?: (point: DataPoint) => void;
}

export default function ForceTimeChart({ data, rupture, onPointClick }: Props) {
  const groups = splitByStage(data);
  const active = ORDERED_STAGES.filter((s) => groups[s].length > 1);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart
        margin={{ top: 8, right: 24, left: 4, bottom: 20 }}
        onClick={(e: any) => { const pt = e?.activePayload?.[0]?.payload; if (pt && onPointClick) onPointClick(pt); }}
        style={{ cursor: onPointClick ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
        <XAxis
          dataKey="elapsed_seconds"
          type="number"
          domain={["auto", "auto"]}
          tickFormatter={(v) => `${Number(v).toFixed(0)}s`}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={{ value: "Tempo (s)", position: "insideBottom", offset: -12, fill: "#475569", fontSize: 10 }}
        />
        <YAxis
          tickFormatter={(v) => `${(Number(v) / 1000).toFixed(0)}k`}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={{ value: "F (N)", angle: -90, position: "insideLeft", offset: 10, fill: "#475569", fontSize: 10 }}
        />
        <Tooltip content={<Tooltip_ />} />
        <Legend wrapperStyle={{ fontSize: 10, color: "#64748b", paddingTop: 8 }} />

        {active.map((stage) => (
          <Area
            key={stage}
            data={groups[stage]}
            dataKey="Forca_N"
            name={STAGE_LABELS[stage]}
            stroke={STAGE_COLORS[stage]}
            strokeWidth={2}
            fill={STAGE_COLORS[stage]}
            fillOpacity={0.07}
            dot={false}
            type="monotone"
            animationDuration={600}
          />
        ))}

        <Customized
          component={(p: any) => (
            <RuptureMarker xAxisMap={p.xAxisMap} offset={p.offset} ruptureValue={rupture.elapsed_seconds} />
          )}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
