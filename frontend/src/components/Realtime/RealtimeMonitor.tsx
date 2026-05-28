import { useEffect, useRef, useState, useCallback } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Wifi, WifiOff, Timer, Zap, MoveHorizontal } from "lucide-react";
import type { RealtimeFrame, RealtimePoint } from "../../types";

const MAX_BUFFER = 3000;   // pontos no buffer interno
const DISPLAY_WINDOW = 600; // pontos exibidos no gráfico (~60s a 100ms)
const RENDER_INTERVAL_MS = 200; // taxa de atualização do gráfico

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtMs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return m > 0 ? `${m}m ${rem.toString().padStart(2, "0")}s` : `${s}s`;
}

function fmtNum(v: number | null | undefined, dec = 2, unit = ""): string {
  if (v == null) return "—";
  return `${v.toFixed(dec)}${unit ? " " + unit : ""}`;
}

// ── sub-components ───────────────────────────────────────────────────────────

function KpiCard({
  icon,
  label,
  value,
  color = "text-white",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl px-5 py-4 flex items-center gap-4">
      <span className="text-accent opacity-70">{icon}</span>
      <div>
        <p className="text-xs text-muted mb-0.5">{label}</p>
        <p className={`text-xl font-mono font-semibold tracking-tight ${color}`}>{value}</p>
      </div>
    </div>
  );
}

const ChartTooltip_ = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
      <p className="text-muted mb-1 pb-1 border-b border-border/60">
        t = <span className="text-white">{(Number(label) / 1000).toFixed(2)} s</span>
      </p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mt-1">
          <span className="w-2 h-0.5 rounded-full flex-shrink-0" style={{ background: p.stroke }} />
          <span className="text-slate-400">{p.name}</span>
          <span className="text-white font-semibold ml-auto pl-4">
            {Number(p.value).toFixed(2)} {p.unit}
          </span>
        </div>
      ))}
    </div>
  );
};

function LiveChart({
  data,
  dataKey,
  color,
  unit,
  label,
  yLabel,
}: {
  data: RealtimePoint[];
  dataKey: keyof RealtimePoint;
  color: string;
  unit: string;
  label: string;
  yLabel: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-muted mb-3">{label}</p>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
          <XAxis
            dataKey="t_ms"
            type="number"
            domain={["auto", "auto"]}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}s`}
            tick={{ fill: "#475569", fontSize: 9 }}
            stroke="#1e2435"
            label={{ value: "Tempo (s)", position: "insideBottom", offset: -10, fill: "#475569", fontSize: 9 }}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toFixed(1)}
            tick={{ fill: "#475569", fontSize: 9 }}
            stroke="#1e2435"
            label={{ value: yLabel, angle: -90, position: "insideLeft", offset: 12, fill: "#475569", fontSize: 9 }}
          />
          <Tooltip content={<ChartTooltip_ />} />
          <Line
            dataKey={dataKey as string}
            name={label}
            unit={unit}
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function FvDChart({ data }: { data: RealtimePoint[] }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-muted mb-3">Força × Deslocamento</p>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
          <XAxis
            dataKey="deslocamento"
            type="number"
            domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toFixed(1)}
            tick={{ fill: "#475569", fontSize: 9 }}
            stroke="#1e2435"
            label={{ value: "Deslocamento (mm)", position: "insideBottom", offset: -10, fill: "#475569", fontSize: 9 }}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toFixed(0)}
            tick={{ fill: "#475569", fontSize: 9 }}
            stroke="#1e2435"
            label={{ value: "F (N)", angle: -90, position: "insideLeft", offset: 12, fill: "#475569", fontSize: 9 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as RealtimePoint;
              return (
                <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
                  <div className="text-white">d = {d.deslocamento.toFixed(2)} mm</div>
                  <div className="text-white">F = {d.forca.toFixed(1)} N</div>
                </div>
              );
            }}
          />
          <Line
            dataKey="forca"
            name="F(d)"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function RealtimeMonitor() {
  const bufferRef = useRef<RealtimePoint[]>([]);
  const esRef     = useRef<EventSource | null>(null);

  const [chartData, setChartData]     = useState<RealtimePoint[]>([]);
  const [frame, setFrame]             = useState<RealtimeFrame | null>(null);
  const [connected, setConnected]     = useState(false);
  const [maxForca, setMaxForca]       = useState(0);
  const [maxDesl, setMaxDesl]         = useState(0);

  const startStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }
    bufferRef.current = [];
    setChartData([]);
    setMaxForca(0);
    setMaxDesl(0);
    setFrame(null);

    const es = new EventSource("/api/realtime/stream");
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (e) => {
      try {
        const msg: RealtimeFrame = JSON.parse(e.data);
        setFrame(msg);

        if (msg.stopped) { stopStream(); return; }
        if (msg.error) return;
        if (!msg.recording) return;

        const f = msg.forca ?? 0;
        const d = msg.deslocamento ?? 0;

        setMaxForca((prev) => Math.max(prev, f));
        setMaxDesl((prev) => Math.max(prev, d));

        const pt: RealtimePoint = { t_ms: msg.t_ms, forca: f, deslocamento: d };
        const buf = bufferRef.current;
        buf.push(pt);
        if (buf.length > MAX_BUFFER) buf.splice(0, buf.length - MAX_BUFFER);
      } catch {
        // ignore parse errors
      }
    };
  }, []);

  const stopStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setConnected(false);
  }, []);

  // Chart render loop — decoupled from SSE message rate
  useEffect(() => {
    const id = setInterval(() => {
      const buf = bufferRef.current;
      if (!buf.length) return;
      const slice = buf.length > DISPLAY_WINDOW ? buf.slice(buf.length - DISPLAY_WINDOW) : [...buf];
      setChartData(slice);
    }, RENDER_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => { esRef.current?.close(); };
  }, []);

  const recording = frame?.recording ?? false;
  const bit       = frame?.bit ?? false;
  const elapsed   = frame?.t_ms ?? 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Monitor em Tempo Real</h1>
          <p className="text-xs text-muted mt-0.5">
            Leitura contínua dos registradores Modbus da IHM
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Connection state badge */}
          <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
            connected
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
              : "border-border bg-surface text-muted"
          }`}>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? "Conectado" : "Desconectado"}
          </div>

          {/* Recording / waiting badge */}
          {connected && (
            <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
              recording
                ? "border-accent/50 bg-accent/10 text-accent"
                : bit
                ? "border-yellow-500/40 bg-yellow-500/10 text-yellow-400"
                : "border-border bg-surface text-muted"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${recording ? "bg-accent animate-ping" : bit ? "bg-yellow-400" : "bg-muted"}`} />
              {recording ? "Gravando" : "Aguardando início"}
            </div>
          )}

          {/* Start / Stop buttons */}
          {!connected ? (
            <button
              onClick={startStream}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-bg text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              <Activity size={14} />
              Iniciar monitor
            </button>
          ) : (
            <button
              onClick={stopStream}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-surface border border-border text-muted hover:text-white text-sm font-medium transition-colors"
            >
              Parar
            </button>
          )}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          icon={<Zap size={20} />}
          label="Força atual"
          value={fmtNum(frame?.forca, 1, "N")}
          color={recording ? "text-sky-300" : "text-muted"}
        />
        <KpiCard
          icon={<MoveHorizontal size={20} />}
          label="Deslocamento atual"
          value={fmtNum(frame?.deslocamento, 2, "mm")}
          color={recording ? "text-violet-300" : "text-muted"}
        />
        <KpiCard
          icon={<Zap size={20} />}
          label="Força máxima"
          value={maxForca > 0 ? `${maxForca.toFixed(1)} N` : "—"}
          color="text-amber-300"
        />
        <KpiCard
          icon={<Timer size={20} />}
          label="Tempo decorrido"
          value={recording && elapsed > 0 ? fmtMs(elapsed) : "—"}
        />
      </div>

      {/* Idle state */}
      {!connected && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Activity size={40} className="text-muted/30 mb-4" />
          <p className="text-sm text-muted">Monitor parado</p>
          <p className="text-xs text-muted/60 mt-1">
            Clique em "Iniciar monitor" para começar a leitura da IHM
          </p>
        </div>
      )}

      {/* Waiting for test */}
      {connected && !recording && chartData.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-12 h-12 rounded-full border-2 border-border flex items-center justify-center mb-4">
            <span className="w-3 h-3 rounded-full bg-muted/40" />
          </div>
          <p className="text-sm text-muted">Aguardando início do ensaio</p>
          <p className="text-xs text-muted/60 mt-1">
            O gráfico será preenchido quando o bit de início for ativado na IHM
          </p>
        </div>
      )}

      {/* Charts — shown once there's data */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <LiveChart
            data={chartData}
            dataKey="forca"
            color="#38bdf8"
            unit="N"
            label="Força × Tempo"
            yLabel="F (N)"
          />
          <LiveChart
            data={chartData}
            dataKey="deslocamento"
            color="#a78bfa"
            unit="mm"
            label="Deslocamento × Tempo"
            yLabel="d (mm)"
          />
          <div className="lg:col-span-2">
            <FvDChart data={chartData} />
          </div>
        </div>
      )}

      {/* Error state */}
      {frame?.error === "ihm_offline" && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">
          IHM inacessível — verifique o IP e os registradores configurados.
        </div>
      )}
    </div>
  );
}
