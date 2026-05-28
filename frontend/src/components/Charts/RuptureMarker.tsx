interface Props {
  xAxisMap?: Record<string, any>;
  offset?: { top: number; height: number };
  ruptureValue: number;
}

export function RuptureMarker({ xAxisMap, offset, ruptureValue }: Props) {
  if (!xAxisMap || !offset) return null;

  const axis = xAxisMap[0] ?? Object.values(xAxisMap)[0];
  if (!axis?.scale) return null;

  const x = axis.scale(ruptureValue);
  const y1 = offset.top;
  const y2 = offset.top + offset.height;

  // Flip badge to the left when rupture is past 55% of chart width to avoid clipping
  const range: [number, number] =
    typeof axis.scale.range === "function" ? axis.scale.range() : [0, 1];
  const chartWidth = Math.abs(range[1] - range[0]);
  const xRelative = x - Math.min(range[0], range[1]);
  const flipLeft = xRelative > chartWidth * 0.55;

  const BADGE_W = 58;
  const BADGE_H = 16;
  const badgeX = flipLeft ? -(BADGE_W + 5) : 5;
  // Place badge near the bottom of the chart area so it doesn't cover the curve peak
  const badgeY = y2 - BADGE_H - 8;

  return (
    <g
      style={{
        transform: `translateX(${x}px)`,
        transition: "transform 480ms cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {/* Glow */}
      <line
        x1={0} y1={y1} x2={0} y2={y2}
        stroke="#ff6b35"
        strokeWidth={6}
        opacity={0.08}
      />
      {/* Main dashed line */}
      <line
        x1={0} y1={y1} x2={0} y2={y2}
        stroke="#ff6b35"
        strokeWidth={1.5}
        strokeDasharray="5 3"
        strokeLinecap="round"
        opacity={0.75}
      />
      {/* Badge */}
      <g transform={`translate(${badgeX}, ${badgeY})`}>
        <rect width={BADGE_W} height={BADGE_H} rx={4} fill="#ff6b35" opacity={0.9} />
        <text
          x={6} y={12}
          fill="white"
          fontSize={9}
          fontWeight={700}
          fontFamily="system-ui, sans-serif"
          letterSpacing={0.5}
        >
          RUPTURA
        </text>
      </g>
    </g>
  );
}
