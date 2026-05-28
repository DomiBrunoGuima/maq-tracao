import {
  CartesianGrid,
  ComposedChart,
  Customized,
  Legend,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DataPoint, RupturePoint } from "../../types";
import { RuptureMarker } from "./RuptureMarker";
import { ORDERED_STAGES, STAGE_COLORS, STAGE_LABELS, splitByStage, stageRanges } from "./stageConfig";

const Tooltip_ = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2.5 shadow-2xl text-xs font-mono">
      <p className="text-muted mb-1.5 pb-1.5 border-b border-border/60">
        t = <span className="text-white">{Number(label).toFixed(1)} s</span>
      </p>
      <div className="flex items-center gap-2">
        <span className="w-2 h-0.5 rounded-full flex-shrink-0" style={{ background: p.stroke }} />
        <span className="text-slate-400">{p.name}</span>
        <span className="text-white font-semibold ml-auto pl-4">
          {Number(p.value).toFixed(0)} N
        </span>
      </div>
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

export default function ForceTimeChart({ data, rupture, height = 240, onPointClick, thumbnail = false }: Props) {
  const groups = splitByStage(data);
  const active = ORDERED_STAGES.filter((s) => groups[s].length > 2);
  const bands  = stageRanges(data, "elapsed_seconds");

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart
        margin={thumbnail ? { top: 2, right: 2, left: 0, bottom: 2 } : { top: 8, right: 24, left: 8, bottom: 24 }}
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
          label={thumbnail ? undefined : {
            value: "Tempo (s)",
            position: "insideBottom", offset: -14,
            fill: "#475569", fontSize: 10,
          }}
        />
        <YAxis
          domain={[0, "auto"]}
          hide={thumbnail}
          tickFormatter={(v) => `${(Number(v) / 1000).toFixed(1)}k`}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={thumbnail ? undefined : {
            value: "F (N)", angle: -90,
            position: "insideLeft", offset: 14,
            fill: "#475569", fontSize: 10,
          }}
        />

        {!thumbnail && bands.map((b, i) => (
          <ReferenceArea
            key={i}
            x1={b.x1} x2={b.x2}
            fill={STAGE_COLORS[b.stage] ?? "#fff"}
            fillOpacity={0.04}
            strokeOpacity={0}
          />
        ))}

        {!thumbnail && <Tooltip content={<Tooltip_ />} />}
        {!thumbnail && (
          <Legend
            verticalAlign="top" align="right"
            wrapperStyle={{ fontSize: 10, paddingBottom: 8 }}
            formatter={(value) => <span style={{ color: "#94a3b8" }}>{value}</span>}
          />
        )}

        {active.map((stage) => (
          <Line
            key={stage}
            data={groups[stage]}
            dataKey="Forca_N"
            name={STAGE_LABELS[stage]}
            stroke={STAGE_COLORS[stage]}
            strokeWidth={thumbnail ? 1.5 : 2}
            dot={false}
            activeDot={thumbnail ? false : { r: 4, strokeWidth: 0, fill: STAGE_COLORS[stage] }}
            type="monotone"
            isAnimationActive={!thumbnail}
            legendType="plainline"
          />
        ))}

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
