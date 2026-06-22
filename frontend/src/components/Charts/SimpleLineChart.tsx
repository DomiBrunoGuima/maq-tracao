import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DataPoint } from "../../types";

interface Props {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  xUnit?: string;
  yUnit?: string;
  xLabel?: string;
  yLabel?: string;
  color?: string;
  height?: number;
  thumbnail?: boolean;
  onPointClick?: (pt: DataPoint) => void;
  xDecimals?: number;
}

/**
 * Gráfico de linha simples — plota TODOS os pontos do ensaio (sem recorte e sem
 * separação por fase). Ponto de partida; refinamentos virão depois.
 */
export default function SimpleLineChart({
  data,
  xKey,
  yKey,
  xUnit = "",
  yUnit = "",
  xLabel,
  yLabel,
  color = "#38bdf8",
  height = 280,
  thumbnail = false,
  onPointClick,
  xDecimals = 2,
}: Props) {
  // Mantém apenas os pontos com x e y numéricos, na ordem original (cronológica).
  const rows = data.filter(
    (d) => typeof d[xKey] === "number" && typeof d[yKey] === "number",
  );

  return (
    <ResponsiveContainer width="100%" height={thumbnail ? height : "100%"}>
      <LineChart
        data={rows}
        margin={thumbnail ? { top: 4, right: 6, left: 0, bottom: 4 } : { top: 8, right: 18, left: 4, bottom: 8 }}
        onClick={(e: any) => {
          const pt = e?.activePayload?.[0]?.payload;
          if (pt && onPointClick) onPointClick(pt);
        }}
        style={{ cursor: onPointClick ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
        <XAxis
          dataKey={xKey}
          type="number"
          domain={["dataMin", "dataMax"]}
          hide={thumbnail}
          tickFormatter={(v) => Number(v).toFixed(xDecimals)}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          minTickGap={40}
          label={
            xLabel && !thumbnail
              ? { value: xLabel, position: "insideBottom", offset: -4, fill: "#475569", fontSize: 10 }
              : undefined
          }
        />
        <YAxis
          hide={thumbnail}
          width={52}
          domain={["auto", "auto"]}
          tickFormatter={(v) => {
            const n = Number(v);
            if (Math.abs(n) >= 100) return n.toFixed(0);
            if (Math.abs(n) >= 1) return n.toFixed(1);
            return n.toFixed(2);
          }}
          tick={{ fill: "#475569", fontSize: 10 }}
          stroke="#1e2435"
          label={
            yLabel && !thumbnail
              ? { value: yLabel, angle: -90, position: "insideLeft", offset: 14, fill: "#475569", fontSize: 10 }
              : undefined
          }
        />
        {!thumbnail && (
          <Tooltip
            content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload;
              return (
                <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
                  <p className="text-muted mb-0.5">
                    {(xLabel ?? xKey)}: <span className="text-white">{Number(p[xKey]).toFixed(xDecimals)}{xUnit ? ` ${xUnit}` : ""}</span>
                  </p>
                  <p className="text-white">
                    {Number(p[yKey]).toFixed(2)}{yUnit ? ` ${yUnit}` : ""}
                  </p>
                </div>
              );
            }}
          />
        )}
        <Line
          dataKey={yKey}
          stroke={color}
          strokeWidth={2}
          dot={false}
          type="linear"
          connectNulls
          isAnimationActive={!thumbnail}
          activeDot={thumbnail ? false : { r: 4, strokeWidth: 0, fill: color }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
