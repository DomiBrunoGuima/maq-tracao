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
      <g transform={`translate(5, ${y1 + 6})`}>
        <rect width={58} height={16} rx={4} fill="#ff6b35" opacity={0.9} />
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
