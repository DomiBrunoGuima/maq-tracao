import { useMemo } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Customized,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DataPoint, RupturePoint } from "../../types";
import { RuptureMarker } from "./RuptureMarker";
import { ORDERED_STAGES, STAGE_COLORS, STAGE_LABELS, stageRanges } from "./stageConfig";

const TooltipContent = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const hit = payload.find((p: any) => p.value !== null && p.value !== undefined);
  if (!hit) return null;
  const stage = hit.payload?.fase ? String(hit.payload.fase) : null;
  return (
    <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2.5 shadow-2xl text-xs font-mono">
      <p className="text-muted mb-1.5 pb-1.5 border-b border-border/60">
        ε = <span className="text-white">{Number(label).toFixed(4)}</span>
        {stage && (
          <span className="ml-2 font-sans" style={{ color: STAGE_COLORS[stage] ?? "#94a3b8" }}>
            {STAGE_LABELS[stage] ?? stage}
          </span>
        )}
      </p>
      <div className="flex items-center gap-2">
        <span className="w-4 h-[2px] rounded-full flex-shrink-0" style={{ background: hit.stroke }} />
        <span className="text-white font-semibold">{Number(hit.value).toFixed(2)} MPa</span>
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

export default function StressStrainChart({ data, rupture, height = 280, onPointClick, thumbnail = false }: Props) {
  const stagesInData = useMemo(() => new Set(data.map(pt => String(pt.fase ?? ""))), [data]);
  const active = ORDERED_STAGES.filter(s => stagesInData.has(s));
  const bands  = stageRanges(data, "Deform_Along");

  const chart = (
    <ResponsiveContainer width="100%" height={thumbnail ? height : "100%"}>
      <ComposedChart
        data={data}
        margin={thumbnail ? { top: 2, right: 2, left: 0, bottom: 2 } : { top: 6, right: 16, left: 0, bottom: 6 }}
        onClick={(e: any) => { const pt = e?.activePayload?.[0]?.payload; if (pt && onPointClick) onPointClick(pt); }}
        style={{ cursor: onPointClick ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
        <XAxis
          dataKey="Deform_Along"
          type="number"
          domain={[0, "auto"]}
          hide={thumbnail}
          tickFormatter={(v) => v.toFixed(3)}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          minTickGap={50}
        />
        <YAxis
          domain={[0, (dataMax: number) => dataMax * 1.08]}
          hide={thumbnail}
          width={50}
          tickFormatter={(v) => { const n = Number(v); if (n >= 10) return n.toFixed(0); if (n >= 1) return n.toFixed(1); return n.toFixed(2); }}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
        />
        {!thumbnail && bands.map((b, i) => (
          <ReferenceArea key={i} x1={b.x1} x2={b.x2}
            fill={STAGE_COLORS[b.stage] ?? "#fff"} fillOpacity={0.12} strokeOpacity={0} />
        ))}
        {!thumbnail && <Tooltip content={<TooltipContent />} />}
        {active.map((stage) => (
          <Line
            key={stage}
            dataKey={(pt: DataPoint, index: number) => {
              const mine = String(pt.fase ?? "") === stage;
              // Stitch: include the last point of the preceding phase so segments connect
              const stitch = !mine && index < data.length - 1 && String(data[index + 1]?.fase ?? "") === stage;
              if (!mine && !stitch) return null;
              const v = pt.Tensao_Pa;
              return typeof v === "number" ? v : null;
            }}
            name={STAGE_LABELS[stage]}
            stroke={STAGE_COLORS[stage]}
            strokeWidth={thumbnail ? 1.5 : 2}
            dot={false}
            activeDot={thumbnail ? false : { r: 4, strokeWidth: 0, fill: STAGE_COLORS[stage] }}
            type="monotone"
            connectNulls={false}
            isAnimationActive={!thumbnail}
            legendType="none"
          />
        ))}
        {!thumbnail && (
          <Customized component={(p: any) => (
            <RuptureMarker xAxisMap={p.xAxisMap} offset={p.offset} ruptureValue={rupture.Deform_Along} />
          )} />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );

  if (thumbnail) return chart;

  return (
    <div className="flex flex-col" style={{ height }}>
      {active.length > 0 && (
        <div className="flex gap-x-3 mb-1.5 pl-[50px] flex-shrink-0 overflow-x-auto">
          {active.map(s => (
            <span key={s} className="flex items-center gap-1.5 text-[10px] text-muted/70 whitespace-nowrap flex-shrink-0">
              <span className="w-5 h-[2px] rounded-full inline-block flex-shrink-0" style={{ background: STAGE_COLORS[s] }} />
              {STAGE_LABELS[s]}
            </span>
          ))}
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-hidden">{chart}</div>
    </div>
  );
}
