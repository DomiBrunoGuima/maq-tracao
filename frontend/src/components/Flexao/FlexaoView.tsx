import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
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
  Ruler,
  Square,
  Trash2,
  Unplug,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";
import {
  getFlexaoStatus,
  startFlexaoTest,
  stopFlexaoTest,
  zerarCelulaFlexao,
  zerarDeslocamentoFlexao,
} from "../../api/client";
import { useConfig } from "../../hooks/useConfig";
import { useCurvasFlexao, useDeleteEnsaioFlexao, useEnsaiosFlexao, useKPIsFlexao } from "../../hooks/useFlexao";
import type { AjusteElastico, FlexaoFrame, Norma } from "../../types";
import { BigValue, StatusEnsaioBar, fmtBig, fmtKgf, type StatusEnsaio } from "../Common/Status";
import FlexaoResultado from "./FlexaoResultado";
import CadastroTeste, { CADASTRO_VAZIO, type CadastroForm } from "../Common/CadastroTeste";

const CADASTRO_KEY = "maq-tracao.cadastro-flexao";

function cadastroSalvo(): CadastroForm {
  try {
    const raw = localStorage.getItem(CADASTRO_KEY);
    return raw ? { ...CADASTRO_VAZIO, ...JSON.parse(raw) } : { ...CADASTRO_VAZIO, norma: "ISO 178" };
  } catch {
    return { ...CADASTRO_VAZIO, norma: "ISO 178" };
  }
}

const MAX_BUFFER = 4000;
const DISPLAY_WINDOW = 600;
const RENDER_INTERVAL_MS = 200;

type Sentido = "cima" | "baixo";
type Tab = "controle" | "ensaios";

interface LivePoint {
  t_ms: number;
  forca: number;
  deslocamento: number;
}

interface SetupForm {
  largura: string;
  espessura: string;
  span: string;
  velocidade: string;
  deslocamento: string;
  limite_forca: string;
  norma: string;
  sentido: Sentido;
}


function fmtNum(v: number | null | undefined, dec = 2, unit = ""): string {
  if (v == null) return "—";
  return `${v.toFixed(dec)}${unit ? " " + unit : ""}`;
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
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} className={inputCls} />
    </div>
  );
}

function KpiCard({ icon, label, value, color = "text-white" }: {
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

function LiveChart({ data, dataKey, color, unit, label, yLabel }: {
  data: LivePoint[]; dataKey: keyof LivePoint; color: string; unit: string; label: string; yLabel: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-muted mb-3">{label}</p>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" vertical={false} />
          <XAxis dataKey="t_ms" type="number" domain={["auto", "auto"]}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}s`}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435" />
          <YAxis domain={["auto", "auto"]} tickFormatter={(v) => Number(v).toFixed(1)}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435"
            label={{ value: yLabel, angle: -90, position: "insideLeft", offset: 12, fill: "#475569", fontSize: 9 }} />
          <Tooltip content={({ active, payload, label: l }: any) =>
            !active || !payload?.length ? null : (
              <div className="bg-tooltip border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
                <p className="text-muted mb-1">t = <span className="text-white">{(Number(l) / 1000).toFixed(2)} s</span></p>
                <p className="text-white">{Number(payload[0].value).toFixed(2)} {unit}</p>
              </div>
            )} />
          <Line dataKey={dataKey as string} stroke={color} strokeWidth={2} dot={false}
            isAnimationActive={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function CurveChart({ data, xKey, yKey, xLabel, yLabel, color, label, fit, fitLegenda }: {
  data: any[]; xKey: string; yKey: string; xLabel: string; yLabel: string; color: string; label: string;
  fit?: AjusteElastico | null; fitLegenda?: (f: AjusteElastico) => string;
}) {
  // Reta do trecho elástico prolongada além do trecho, para mostrar onde a curva se afasta dela
  const xs = data.map((p) => p[xKey]).filter((v): v is number => typeof v === "number");
  const xMax = xs.length ? Math.max(...xs) : fit?.x_fim ?? 0;
  const x2 = fit ? Math.min(xMax, fit.x_ini + (fit.x_fim - fit.x_ini) * 1.6) : 0;
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-muted mb-1">{label}</p>
      <p className="text-[11px] font-mono text-muted/70 mb-2 min-h-[1rem]">
        {fit && fitLegenda ? <><span className="text-emerald-400">■</span> trecho elástico · <span className="text-rose-400">- -</span> {fitLegenda(fit)} · R² = {fit.r2.toFixed(4)}</> : null}
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 20, left: 8, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2e" />
          <XAxis dataKey={xKey} type="number" domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toFixed(2)}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435"
            label={{ value: xLabel, position: "insideBottom", offset: -8, fill: "#475569", fontSize: 10 }} />
          <YAxis domain={["auto", "auto"]} tickFormatter={(v) => Number(v).toFixed(0)}
            tick={{ fill: "#475569", fontSize: 9 }} stroke="#1e2435"
            label={{ value: yLabel, angle: -90, position: "insideLeft", offset: 8, fill: "#475569", fontSize: 10 }} />
          <Tooltip content={({ active, payload }: any) =>
            !active || !payload?.length ? null : (
              <div className="bg-tooltip border border-border rounded-xl px-3 py-2 shadow-2xl text-xs font-mono">
                <p className="text-muted">{xLabel}: <span className="text-white">{Number(payload[0].payload[xKey]).toFixed(4)}</span></p>
                <p className="text-white">{yLabel}: {Number(payload[0].payload[yKey]).toFixed(2)}</p>
              </div>
            )} />
          {fit && fit.x_fim > fit.x_ini && (
            <ReferenceArea x1={fit.x_ini} x2={fit.x_fim} ifOverflow="hidden"
              fill="#22c55e" fillOpacity={0.12} strokeOpacity={0} />
          )}
          <Line dataKey={yKey} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          {fit && (
            <ReferenceLine ifOverflow="hidden" stroke="#f43f5e" strokeWidth={1.5} strokeDasharray="6 4"
              segment={[
                { x: fit.x_ini, y: fit.inclinacao * fit.x_ini + fit.intercepto },
                { x: x2, y: fit.inclinacao * x2 + fit.intercepto },
              ]} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Aba de resultados: lista + KPIs + curvas ────────────────────────────────

function EnsaiosTab({ initialId }: { initialId?: number | null }) {
  const { data: ensaios, isLoading } = useEnsaiosFlexao();
  const [selected, setSelected] = useState<number | null>(initialId ?? null);
  const delMut = useDeleteEnsaioFlexao();

  // Clique num ensaio de flexão na barra lateral troca o ensaio mostrado
  useEffect(() => { if (initialId != null) setSelected(initialId); }, [initialId]);

  useEffect(() => {
    if (selected == null && ensaios && ensaios.length > 0) setSelected(ensaios[0].id);
  }, [ensaios, selected]);

  if (isLoading) return <p className="text-sm text-muted">Carregando ensaios de flexão…</p>;
  if (!ensaios || ensaios.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Ruler size={36} className="text-muted/30 mb-3" />
        <p className="text-sm text-muted">Nenhum ensaio de flexão gravado ainda.</p>
        <p className="text-xs text-muted mt-1">Use a aba "Controle & Aquisição" para realizar um ensaio.</p>
      </div>
    );
  }

  return (
    <FlexaoResultado
      ensaios={ensaios}
      selected={selected}
      onSelect={setSelected}
      onDelete={(id) => { delMut.mutate(id); if (selected === id) setSelected(null); }}
    />
  );
}

// ── Aba de controle ao vivo ─────────────────────────────────────────────────

function ControleTab({ onOpenEnsaios }: { onOpenEnsaios: () => void }) {
  const { data: config } = useConfig();
  const qc = useQueryClient();

  const bufferRef = useRef<LivePoint[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const [form, setForm] = useState<SetupForm>({
    largura: "", espessura: "", span: "", velocidade: "",
    deslocamento: "", limite_forca: "", norma: "ISO 178", sentido: "baixo",
  });
  const [chartData, setChartData] = useState<LivePoint[]>([]);
  const [frame, setFrame] = useState<FlexaoFrame | null>(null);
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [maxForca, setMaxForca] = useState(0);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Leitura ao vivo mesmo com o ensaio parado (conferir condições antes de iniciar).
  const [live, setLive] = useState<{ forca: number | null; desloc: number | null }>({ forca: null, desloc: null });
  const [status, setStatus] = useState<StatusEnsaio>("parado");
  const [cadastro, setCadastro] = useState<CadastroForm>(cadastroSalvo);

  useEffect(() => {
    try { localStorage.setItem(CADASTRO_KEY, JSON.stringify(cadastro)); } catch { /* ignore */ }
  }, [cadastro]);

  function aplicarNorma(n: Norma) {
    setForm((f) => ({
      ...f,
      norma: n.codigo,
      velocidade: n.velocidade_mm_min != null ? String(n.velocidade_mm_min) : f.velocidade,
      largura: n.largura_mm != null ? String(n.largura_mm) : f.largura,
      espessura: n.espessura_mm != null ? String(n.espessura_mm) : f.espessura,
      span: n.span_mm != null ? String(n.span_mm) : f.span,
    }));
  }

  useEffect(() => {
    if (!config) return;
    setForm((f) => ({
      ...f,
      largura: f.largura || (config.flexao_largura_mm ? String(config.flexao_largura_mm) : ""),
      espessura: f.espessura || (config.flexao_espessura_mm ? String(config.flexao_espessura_mm) : ""),
      span: f.span || (config.flexao_span_mm ? String(config.flexao_span_mm) : ""),
      norma: config.flexao_norma || f.norma,
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
    setChartData([]); setMaxForca(0); setSavedId(null); setFrame(null);

    const es = new EventSource("/api/flexao/control/stream");
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const msg: FlexaoFrame = JSON.parse(e.data);
        setFrame(msg);
        if (msg.error) {
          setError(msg.error);
          if (msg.error !== "reconnecting") setStatus("parado");
          return;
        }
        if (msg.fim_ensaio || msg.saved_ensaio_id != null) {
          if (msg.saved_ensaio_id != null) setSavedId(msg.saved_ensaio_id);
          setStatus("finalizado");
          setRunning(false);
          qc.invalidateQueries({ queryKey: ["flexao", "ensaios"] });
          stopStream();
          return;
        }
        if (msg.recording) setStatus((s) => (s === "preparando" ? "executando" : s));
        const f = msg.forca ?? 0;
        const d = msg.deslocamento ?? 0;
        setMaxForca((p) => Math.max(p, f));
        const buf = bufferRef.current;
        buf.push({ t_ms: msg.t_ms, forca: f, deslocamento: d });
        if (buf.length > MAX_BUFFER) buf.splice(0, buf.length - MAX_BUFFER);
      } catch { /* ignore */ }
    };
  }, [qc, stopStream]);

  useEffect(() => {
    const id = setInterval(() => {
      const buf = bufferRef.current;
      if (!buf.length) return;
      setChartData(buf.length > DISPLAY_WINDOW ? buf.slice(buf.length - DISPLAY_WINDOW) : [...buf]);
    }, RENDER_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => () => { esRef.current?.close(); }, []);

  // Polling da leitura ao vivo enquanto o ensaio NÃO roda (durante o ensaio o SSE provê).
  useEffect(() => {
    if (running) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await getFlexaoStatus();
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
    for (const [k, label] of [["largura", "largura b"], ["espessura", "espessura h"], ["span", "distância entre apoios L"]] as const) {
      const v = num(form[k]);
      if (v == null || v <= 0) { setError(`Informe a ${label} (mm) maior que zero.`); return; }
    }
    setStatus("preparando");
    try {
      await startFlexaoTest({
        sentido: form.sentido,
        velocidade: num(form.velocidade),
        deslocamento: num(form.deslocamento),
        limite_forca: num(form.limite_forca),
        largura_mm: num(form.largura),
        espessura_mm: num(form.espessura),
        span_mm: num(form.span),
        norma: cadastro.norma || form.norma,
        cliente_id: cadastro.cliente_id,
        amostra: cadastro.amostra,
        operador: cadastro.operador,
      });
      setRunning(true);
      startStream();
    } catch (e: any) {
      setStatus("parado");
      setError(e?.response?.data?.detail ?? "Falha ao iniciar o ensaio de flexão.");
    }
  }

  async function handleStop() {
    setError(null);
    try { await stopFlexaoTest(); }
    catch (e: any) { setError(e?.response?.data?.detail ?? "Falha ao enviar comando de parada."); }
    finally { if (running) setStatus("finalizado"); setRunning(false); stopStream(); }
  }

  async function handleZerarDeslocamento() {
    setError(null);
    try { await zerarDeslocamentoFlexao(); }
    catch (e: any) { setError(e?.response?.data?.detail ?? "Falha ao zerar o deslocamento."); }
  }

  async function handleZerarCelula() {
    setError(null);
    try { await zerarCelulaFlexao(); }
    catch (e: any) { setError(e?.response?.data?.detail ?? "Falha ao zerar a célula de carga."); }
    // Zerar a célula de carga também encerra o ensaio em curso.
    finally { if (running) setStatus("finalizado"); setRunning(false); stopStream(); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end gap-3">
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

      <StatusEnsaioBar status={status} />

      {/* Valores em tempo real */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <BigValue icon={<Zap size={18} />} label="Força atual" value={fmtKgf(forcaShown)} unit="kgf"
          alt={forcaShown != null ? `${fmtBig(forcaShown, 1)} N` : undefined}
          color={forcaShown != null ? "text-sky-300" : "text-muted"} />
        <BigValue icon={<MoveHorizontal size={18} />} label="Deflexão atual" value={fmtBig(deslocShown, 2)} unit="mm"
          color={deslocShown != null ? "text-violet-300" : "text-muted"} />
        <BigValue icon={<Gauge size={18} />} label="Força máxima" value={maxForca > 0 ? fmtKgf(maxForca) : "—"} unit="kgf"
          alt={maxForca > 0 ? `${maxForca.toFixed(1)} N` : undefined}
          color="text-amber-300" />
      </div>

      <div className="bg-surface border border-border rounded-xl p-5 space-y-5">
        <CadastroTeste value={cadastro} onChange={setCadastro} tipo="flexao" onNorma={aplicarNorma} disabled={running} />
        <hr className="border-border/60" />
        <p className="text-xs font-medium text-muted uppercase tracking-wide">Geometria do corpo de prova (flexão 3 pontos)</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <NumberField label="Largura b" unit="mm" value={form.largura}
            onChange={(v) => setForm((f) => ({ ...f, largura: v }))} placeholder="ex: 10" />
          <NumberField label="Espessura h" unit="mm" value={form.espessura}
            onChange={(v) => setForm((f) => ({ ...f, espessura: v }))} placeholder="ex: 4" />
          <NumberField label="Distância entre apoios L" unit="mm" value={form.span}
            onChange={(v) => setForm((f) => ({ ...f, span: v }))} placeholder="ex: 64" />
          <NumberField label="Velocidade" unit="mm/min" value={form.velocidade}
            onChange={(v) => setForm((f) => ({ ...f, velocidade: v }))} placeholder="ex: 2" />
          <NumberField label="Deflexão-alvo" unit="mm" value={form.deslocamento}
            onChange={(v) => setForm((f) => ({ ...f, deslocamento: v }))} placeholder="ex: 20" />
          <NumberField label="Limite de força" unit="N" value={form.limite_forca}
            onChange={(v) => setForm((f) => ({ ...f, limite_forca: v }))} placeholder="opcional" />
          <div>
            <span className="text-xs font-medium text-muted block mb-1.5">Sentido</span>
            <div className="grid grid-cols-2 gap-2">
              {(["baixo", "cima"] as Sentido[]).map((s) => (
                <button key={s} onClick={() => setForm((f) => ({ ...f, sentido: s }))} disabled={running}
                  className={clsx(
                    "flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium border transition-colors disabled:opacity-50",
                    form.sentido === s ? "border-accent bg-accent/10 text-accent" : "border-border bg-bg text-muted hover:text-white",
                  )}>
                  {s === "cima" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                  {s === "cima" ? "Cima" : "Baixo"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button onClick={handleStart} disabled={running}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-500 text-bg text-sm font-semibold
                       hover:bg-emerald-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            <Play size={15} /> Iniciar ensaio
          </button>
          <button onClick={handleStop}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-red-500/90 text-[#fff] text-sm font-semibold
                       hover:bg-red-500 transition-colors ring-1 ring-red-400/30">
            <Square size={14} /> Parar
          </button>
          <button onClick={handleZerarDeslocamento}
            title="Zera o deslocamento (limpa o resíduo antes de um novo ensaio)"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-bg text-sm font-medium
                       text-muted hover:text-white hover:border-accent transition-colors">
            <RotateCcw size={14} /> Zerar deslocamento
          </button>
          <button onClick={handleZerarCelula}
            title="Zera a célula de carga — também para o ensaio em curso"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-amber-500/40 bg-amber-500/10 text-sm font-medium
                       text-amber-300 hover:bg-amber-500/20 transition-colors">
            <OctagonX size={14} /> Zerar célula (para o teste)
          </button>
          {error && <p className="text-xs text-red-400 ml-2">{error}</p>}
        </div>
      </div>

      {savedId != null && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 flex items-center gap-3">
          <CheckCircle2 size={18} className="text-emerald-400 flex-shrink-0" />
          <p className="text-sm text-emerald-300">
            Ensaio de flexão gravado.{" "}
            <button onClick={onOpenEnsaios} className="underline font-medium hover:text-emerald-200">
              Ver resultados (#{savedId})
            </button>
          </p>
        </div>
      )}

      {chartData.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <LiveChart data={chartData} dataKey="forca" color="#38bdf8" unit="N" label="Força × Tempo" yLabel="F (N)" />
          <LiveChart data={chartData} dataKey="deslocamento" color="#a78bfa" unit="mm" label="Deflexão × Tempo" yLabel="δ (mm)" />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Unplug size={36} className="text-muted/30 mb-3" />
          <p className="text-sm text-muted">
            {running ? "Aguardando dados do CLP…" : "Configure a geometria e clique em Iniciar ensaio"}
          </p>
        </div>
      )}
    </div>
  );
}

// ── View principal ──────────────────────────────────────────────────────────

export default function FlexaoView({ initialEnsaioId }: { initialEnsaioId?: number | null }) {
  const [tab, setTab] = useState<Tab>(initialEnsaioId != null ? "ensaios" : "controle");

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div>
        <h1 className="text-xl font-semibold text-white">Ensaio de Flexão</h1>
        <p className="text-xs text-muted mt-0.5">Flexão a 3 pontos — ISO 178 / ASTM D790 · σf = 3FL/2bh², Ef</p>
      </div>

      <div className="flex gap-1 border-b border-border">
        {([["controle", "Controle & Aquisição"], ["ensaios", "Resultados"]] as [Tab, string][]).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              tab === t ? "border-accent text-accent" : "border-transparent text-muted hover:text-white",
            )}>
            {label}
          </button>
        ))}
      </div>

      {tab === "controle" ? <ControleTab onOpenEnsaios={() => setTab("ensaios")} /> : <EnsaiosTab initialId={initialEnsaioId} />}
    </div>
  );
}
