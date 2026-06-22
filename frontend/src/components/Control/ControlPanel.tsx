import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Gauge,
  MoveHorizontal,
  OctagonX,
  Play,
  RotateCcw,
  ShieldCheck,
  Square,
  Unplug,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";
import { getControlStatus, startTest, stopTest, zerarCelula, zerarDeslocamento } from "../../api/client";
import { useConfig } from "../../hooks/useConfig";
import type { RealtimeFrame, RealtimePoint } from "../../types";

const MAX_BUFFER = 4000;
const DISPLAY_WINDOW = 600;
const RENDER_INTERVAL_MS = 200;

type Sentido = "cima" | "baixo";

interface SetupForm {
  deslocamento: string;
  velocidade: string;
  limite_forca: string;
  area_seccao: string;
  comprimento_inicial: string;
  sentido: Sentido;
}

function fmtNum(v: number | null | undefined, dec = 2, unit = ""): string {
  if (v == null) return "—";
  return `${v.toFixed(dec)}${unit ? " " + unit : ""}`;
}

// ── primitives ────────────────────────────────────────────────────────────

function KpiCard({
  icon, label, value, color = "text-white",
}: {
  icon: React.ReactNode; label: string; value: string; color?: string;
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

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors font-mono placeholder:text-muted/40";

function NumberField({
  label, value, onChange, placeholder, unit,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; unit?: string;
}) {
  return (
    <div>
      <span className="text-xs font-medium text-muted block mb-1.5">
        {label}{unit && <span className="text-muted/50"> ({unit})</span>}
      </span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputCls}
      />
    </div>
  );
}

function LiveChart({
  data, dataKey, color, unit, label, yLabel,
}: {
  data: RealtimePoint[]; dataKey: keyof RealtimePoint; color: string; unit: string; label: string; yLabel: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-muted mb-3">{label}</p>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
          <XAxis
            dataKey="t_ms" type="number" domain={["auto", "auto"]}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}s`}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435"
          />
          <YAxis
            domain={["auto", "auto"]} tickFormatter={(v) => Number(v).toFixed(1)}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435"
            label={{ value: yLabel, angle: -90, position: "insideLeft", offset: 12, fill: "#475569", fontSize: 9 }}
          />
          <Tooltip
            content={({ active, payload, label: l }: any) =>
              !active || !payload?.length ? null : (
                <div className="bg-[#0a0c14] border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
                  <p className="text-muted mb-1">t = <span className="text-white">{(Number(l) / 1000).toFixed(2)} s</span></p>
                  <p className="text-white">{Number(payload[0].value).toFixed(2)} {unit}</p>
                </div>
              )
            }
          />
          <Line dataKey={dataKey as string} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── main component ──────────────────────────────────────────────────────────

export default function ControlPanel({ onOpenEnsaio }: { onOpenEnsaio?: (id: number) => void }) {
  const { data: config } = useConfig();
  const qc = useQueryClient();

  const bufferRef = useRef<RealtimePoint[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const [form, setForm] = useState<SetupForm>({
    deslocamento: "", velocidade: "", limite_forca: "",
    area_seccao: "", comprimento_inicial: "", sentido: "cima",
  });
  const [chartData, setChartData] = useState<RealtimePoint[]>([]);
  const [frame, setFrame] = useState<RealtimeFrame | null>(null);
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [maxForca, setMaxForca] = useState(0);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Leitura ao vivo (força/deslocamento) mesmo com o ensaio parado, para conferir
  // as condições antes de iniciar. Não entra no gráfico — só nos indicadores.
  const [live, setLive] = useState<{ forca: number | null; desloc: number | null }>({ forca: null, desloc: null });

  // Pré-preenche área/L0 a partir da config
  useEffect(() => {
    if (!config) return;
    setForm((f) => ({
      ...f,
      area_seccao: f.area_seccao || (config.area_seccao_mm2 ? String(config.area_seccao_mm2) : ""),
      comprimento_inicial: f.comprimento_inicial || (config.comprimento_inicial_mm ? String(config.comprimento_inicial_mm) : ""),
    }));
  }, [config]);

  const stopStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setConnected(false);
  }, []);

  const startStream = useCallback(() => {
    esRef.current?.close();
    bufferRef.current = [];
    setChartData([]);
    setMaxForca(0);
    setSavedId(null);
    setFrame(null);

    const es = new EventSource("/api/control/stream");
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const msg: RealtimeFrame = JSON.parse(e.data);
        setFrame(msg);
        if (msg.error) { setError(msg.error); return; }
        if (msg.ruptura || msg.saved_ensaio_id != null) {
          if (msg.saved_ensaio_id != null) setSavedId(msg.saved_ensaio_id);
          setRunning(false);
          qc.invalidateQueries({ queryKey: ["ensaios"] });
          stopStream();
          return;
        }
        const f = msg.forca ?? 0;
        const d = msg.deslocamento ?? 0;
        setMaxForca((p) => Math.max(p, f));
        const buf = bufferRef.current;
        buf.push({ t_ms: msg.t_ms, forca: f, deslocamento: d });
        if (buf.length > MAX_BUFFER) buf.splice(0, buf.length - MAX_BUFFER);
      } catch { /* ignore */ }
    };
  }, [qc, stopStream]);

  // chart render loop
  useEffect(() => {
    const id = setInterval(() => {
      const buf = bufferRef.current;
      if (!buf.length) return;
      setChartData(buf.length > DISPLAY_WINDOW ? buf.slice(buf.length - DISPLAY_WINDOW) : [...buf]);
    }, RENDER_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => () => { esRef.current?.close(); }, []);

  // Polling da leitura ao vivo quando o ensaio NÃO está rodando (durante o ensaio,
  // o stream SSE já fornece os valores). Atualiza força/deslocamento e a força máxima.
  useEffect(() => {
    if (running) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await getControlStatus();
        if (cancelled) return;
        const forca = s.forca_atual ?? null;
        const desloc = s.deslocamento_atual ?? null;
        setLive({ forca, desloc });
        if (forca != null) setMaxForca((p) => Math.max(p, forca));
      } catch { /* offline: ignora */ }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [running]);

  const num = (s: string): number | null => (s.trim() === "" ? null : Number(s));

  const forcaShown = frame?.forca ?? live.forca;
  const deslocShown = frame?.deslocamento ?? live.desloc;

  async function handleStart() {
    setError(null);
    const limite = num(form.limite_forca);
    if (limite == null || limite <= 0) { setError("Informe um limite de força de ruptura maior que zero."); return; }
    try {
      await startTest({
        sentido: form.sentido,
        velocidade: num(form.velocidade),
        deslocamento: num(form.deslocamento),
        limite_forca: limite,
        area_seccao: num(form.area_seccao),
        comprimento_inicial: num(form.comprimento_inicial),
      });
      setRunning(true);
      startStream();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Falha ao iniciar o ensaio.");
    }
  }

  async function handleStop() {
    setError(null);
    try {
      await stopTest();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Falha ao enviar comando de parada.");
    } finally {
      setRunning(false);
      stopStream();
    }
  }

  async function handleZerarDeslocamento() {
    setError(null);
    try {
      await zerarDeslocamento();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Falha ao zerar o deslocamento.");
    }
  }

  async function handleZerarCelula() {
    setError(null);
    try {
      await zerarCelula();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Falha ao zerar a célula de carga.");
    } finally {
      // Zerar a célula de carga também encerra o ensaio em curso.
      setRunning(false);
      stopStream();
    }
  }

  const integro = frame?.material_integro ?? false;
  const ruptura = frame?.ruptura ?? false;

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Controle da Máquina</h1>
          <p className="text-xs text-muted mt-0.5">
            Comando direto do CLP via Modbus TCP — iniciar, parar e setpoints do ensaio
          </p>
        </div>
        <div className="flex items-center gap-3">
          {config?.simulator_enabled && (
            <div className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border border-amber-500/50 bg-amber-500/15 text-amber-300 font-semibold">
              SIMULADOR
            </div>
          )}
          <div className={clsx(
            "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border",
            connected ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
              : forcaShown != null ? "border-sky-500/40 bg-sky-500/10 text-sky-400"
              : "border-border bg-surface text-muted",
          )}>
            <span className={clsx("w-1.5 h-1.5 rounded-full",
              connected ? "bg-emerald-400 animate-pulse" : forcaShown != null ? "bg-sky-400 animate-pulse" : "bg-muted")} />
            {connected ? "Aquisição ativa" : forcaShown != null ? "Monitorando" : "Offline"}
          </div>
        </div>
      </div>

      {/* Setup + ações */}
      <div className="bg-surface border border-border rounded-xl p-5 space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <NumberField label="Deslocamento programado" unit="mm" value={form.deslocamento}
            onChange={(v) => setForm((f) => ({ ...f, deslocamento: v }))} placeholder="ex: 50" />
          <NumberField label="Velocidade" unit="mm/min" value={form.velocidade}
            onChange={(v) => setForm((f) => ({ ...f, velocidade: v }))} placeholder="ex: 5" />
          <NumberField label="Limite de força (ruptura)" unit="N" value={form.limite_forca}
            onChange={(v) => setForm((f) => ({ ...f, limite_forca: v }))} placeholder="ex: 5000" />
          <NumberField label="Área da seção" unit="mm²" value={form.area_seccao}
            onChange={(v) => setForm((f) => ({ ...f, area_seccao: v }))} placeholder="ex: 20" />
          <NumberField label="Comprimento inicial L₀" unit="mm" value={form.comprimento_inicial}
            onChange={(v) => setForm((f) => ({ ...f, comprimento_inicial: v }))} placeholder="ex: 50" />

          {/* Sentido */}
          <div>
            <span className="text-xs font-medium text-muted block mb-1.5">Sentido</span>
            <div className="grid grid-cols-2 gap-2">
              {(["cima", "baixo"] as Sentido[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setForm((f) => ({ ...f, sentido: s }))}
                  disabled={running}
                  className={clsx(
                    "flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium border transition-colors disabled:opacity-50",
                    form.sentido === s ? "border-accent bg-accent/10 text-accent" : "border-border bg-bg text-muted hover:text-white",
                  )}
                >
                  {s === "cima" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                  {s === "cima" ? "Cima" : "Baixo"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleStart}
            disabled={running}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-500 text-bg text-sm font-semibold
                       hover:bg-emerald-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play size={15} /> Iniciar ensaio
          </button>
          <button
            onClick={handleStop}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-red-500/90 text-white text-sm font-semibold
                       hover:bg-red-500 transition-colors ring-1 ring-red-400/30"
          >
            <Square size={14} /> Parar
          </button>
          <button
            onClick={handleZerarDeslocamento}
            title="Zera o deslocamento (limpa o resíduo antes de um novo ensaio)"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-bg text-sm font-medium
                       text-muted hover:text-white hover:border-accent transition-colors"
          >
            <RotateCcw size={14} /> Zerar deslocamento
          </button>
          <button
            onClick={handleZerarCelula}
            title="Zera a célula de carga — também para o ensaio em curso"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-amber-500/40 bg-amber-500/10 text-sm font-medium
                       text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            <OctagonX size={14} /> Zerar célula (para o teste)
          </button>
          {error && <p className="text-xs text-red-400 ml-2">{error}</p>}
        </div>
      </div>

      {/* Saved banner */}
      {savedId != null && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 flex items-center gap-3">
          <CheckCircle2 size={18} className="text-emerald-400 flex-shrink-0" />
          <p className="text-sm text-emerald-300">
            Ensaio gravado (ruptura detectada). {onOpenEnsaio && (
              <button onClick={() => onOpenEnsaio(savedId)} className="underline font-medium hover:text-emerald-200">
                Abrir ensaio #{savedId}
              </button>
            )}
          </p>
        </div>
      )}

      {/* Estado / KPIs ao vivo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={<Zap size={20} />} label="Força atual" value={fmtNum(forcaShown, 1, "N")}
          color={forcaShown != null ? "text-sky-300" : "text-muted"} />
        <KpiCard icon={<MoveHorizontal size={20} />} label="Deslocamento atual" value={fmtNum(deslocShown, 2, "mm")}
          color={deslocShown != null ? "text-violet-300" : "text-muted"} />
        <KpiCard icon={<Gauge size={20} />} label="Força máxima" value={maxForca > 0 ? `${maxForca.toFixed(1)} N` : "—"}
          color="text-amber-300" />
        <div className={clsx(
          "rounded-xl px-5 py-4 flex items-center gap-3 border",
          ruptura ? "border-red-500/40 bg-red-500/10" : integro ? "border-emerald-500/40 bg-emerald-500/10" : "border-border bg-surface",
        )}>
          <ShieldCheck size={20} className={ruptura ? "text-red-400" : integro ? "text-emerald-400" : "text-muted/50"} />
          <div>
            <p className="text-xs text-muted mb-0.5">Estado do material</p>
            <p className={clsx("text-sm font-semibold",
              ruptura ? "text-red-300" : integro ? "text-emerald-300" : "text-muted")}>
              {ruptura ? "Ruptura (M31)" : integro ? "Íntegro (M30)" : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Charts */}
      {chartData.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <LiveChart data={chartData} dataKey="forca" color="#38bdf8" unit="N" label="Força × Tempo" yLabel="F (N)" />
          <LiveChart data={chartData} dataKey="deslocamento" color="#a78bfa" unit="mm" label="Deslocamento × Tempo" yLabel="d (mm)" />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Unplug size={36} className="text-muted/30 mb-3" />
          <p className="text-sm text-muted">
            {running ? "Aguardando dados do CLP…" : "Configure os parâmetros e clique em Iniciar ensaio"}
          </p>
        </div>
      )}
    </div>
  );
}
