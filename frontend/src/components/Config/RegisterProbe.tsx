import { useState } from "react";
import { clsx } from "clsx";
import { ArrowDownToLine, ArrowUpFromLine, FlaskConical, Loader2 } from "lucide-react";
import { probeRegister } from "../../api/client";
import type { IHMRegister, ModbusDataType, RegisterProbeResult } from "../../types";

const DATA_TYPES: ModbusDataType[] = ["coil", "uint16", "decimal", "int32", "decimal32", "float32"];
const WORD2 = ["int32", "decimal32", "float32"];

const inp =
  "bg-bg border border-border rounded px-2 py-1.5 text-xs font-mono text-white " +
  "focus:outline-none focus:border-accent transition-colors w-full";
const lbl = "text-[10px] font-medium text-muted/60 uppercase tracking-wider block mb-1";

const hex = (ws: number[] | null) =>
  ws == null ? "—" : "[" + ws.map((w) => `0x${w.toString(16).toUpperCase().padStart(4, "0")}`).join(", ") + "]";

export default function RegisterProbe({ registers }: { registers: IHMRegister[] }) {
  const [address, setAddress] = useState<number>(40004);
  const [name, setName] = useState("");
  const [dataType, setDataType] = useState<ModbusDataType>("float32");
  const [wordOrder, setWordOrder] = useState<"big" | "little">("little");
  const [scale, setScale] = useState<number>(1);
  const [direction, setDirection] = useState<"read" | "write">("read");
  const [value, setValue] = useState<string>("100");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RegisterProbeResult | null>(null);

  function prefill(r: IHMRegister) {
    setAddress(r.address);
    setName(r.name);
    setDataType(r.data_type);
    setWordOrder((r.word_order as "big" | "little") ?? "big");
    setScale(r.scale ?? 1);
    setDirection(r.writable ? "write" : "read");
    setResult(null);
  }

  async function run() {
    setBusy(true);
    setResult(null);
    try {
      const res = await probeRegister({
        address, name, data_type: dataType, scale, word_order: wordOrder, direction,
        value: direction === "write" ? Number(value) : null,
      });
      setResult(res);
    } catch (e: any) {
      setResult({
        ok: false, direction, address, name, data_type: dataType, word_order: wordOrder, scale,
        ip: "", port: 0, sent_words: null, read_words: null, decoded: null, as_float: null, as_int: null,
        error: e?.response?.data?.detail ?? "Falha na requisição (backend rodando na porta 8000?).",
      });
    } finally {
      setBusy(false);
    }
  }

  const is32 = WORD2.includes(dataType);

  return (
    <div className="rounded-xl border border-border bg-surface/40 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <FlaskConical size={15} className="text-accent" />
        <h4 className="text-sm font-semibold text-white">Diagnóstico de registrador</h4>
      </div>
      <p className="text-xs text-muted/70 -mt-2">
        Testa um endereço isolado contra a IHM/CLP sem mexer no mapa salvo. Em <b>escrita</b>, envia o valor e relê;
        em <b>leitura</b>, mostra o valor cru interpretado como float <i>e</i> como int.
      </p>

      {/* Pré-preencher a partir de um registrador do mapa */}
      {registers.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {registers.map((r, i) => (
            <button key={i} onClick={() => prefill(r)}
              className="text-[10px] font-mono px-2 py-1 rounded border border-border bg-bg text-muted hover:text-white hover:border-accent transition-colors">
              {r.name || `@${r.address}`}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <span className={lbl}>Endereço</span>
          <input type="number" value={address} onChange={(e) => setAddress(Number(e.target.value))} className={inp} />
        </div>
        <div>
          <span className={lbl}>Nome</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="opcional" className={inp} />
        </div>
        <div>
          <span className={lbl}>Tipo</span>
          <select value={dataType} onChange={(e) => setDataType(e.target.value as ModbusDataType)} className={inp}>
            {DATA_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <span className={lbl}>Ordem (32 bits)</span>
          <select value={wordOrder} disabled={!is32}
            onChange={(e) => setWordOrder(e.target.value as "big" | "little")}
            className={clsx(inp, !is32 && "opacity-40")}>
            <option value="big">big</option>
            <option value="little">little</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <div>
          <span className={lbl}>Escala</span>
          <input type="number" step="0.001" value={scale} onChange={(e) => setScale(Number(e.target.value))} className={inp} />
        </div>
        <div>
          <span className={lbl}>Sentido</span>
          <div className="grid grid-cols-2 gap-1.5">
            {(["read", "write"] as const).map((d) => (
              <button key={d} onClick={() => setDirection(d)}
                className={clsx("flex items-center justify-center gap-1 py-1.5 rounded text-xs font-medium border transition-colors",
                  direction === d ? "border-accent bg-accent/10 text-accent" : "border-border bg-bg text-muted hover:text-white")}>
                {d === "read" ? <ArrowDownToLine size={12} /> : <ArrowUpFromLine size={12} />}
                {d === "read" ? "Entrada" : "Saída"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className={lbl}>Valor (escrita)</span>
          <input type="number" value={value} disabled={direction !== "write"}
            onChange={(e) => setValue(e.target.value)}
            className={clsx(inp, direction !== "write" && "opacity-40")} />
        </div>
        <button onClick={run} disabled={busy}
          className="flex items-center justify-center gap-2 py-2 rounded-lg bg-accent text-bg text-sm font-semibold
                     hover:bg-accent/90 transition-colors disabled:opacity-50">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <FlaskConical size={14} />}
          Testar
        </button>
      </div>

      {/* Resultado */}
      {result && (
        <div className={clsx("rounded-lg border px-3 py-3 text-xs font-mono space-y-1.5",
          result.ok ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/40 bg-red-500/5")}>
          {result.error ? (
            <p className="text-red-300">⚠ {result.error}</p>
          ) : (
            <>
              <Row k="enviado (write)" v={hex(result.sent_words)} />
              <Row k="lido (raw)" v={hex(result.read_words)} />
              <Row k={`decodificado (${result.data_type}, ${result.word_order})`} v={String(result.decoded)} highlight />
              {result.as_float != null && <Row k="se for FLOAT" v={String(result.as_float)} />}
              {result.as_int != null && <Row k="se for INT" v={String(result.as_int)} />}
              <p className="text-[10px] text-muted/50 pt-1">
                {result.ip}:{result.port} · compare o "decodificado" com o que a IHM mostra. Se bater, tipo+ordem certos.
                Se não, troque tipo (float/int) ou ordem (big/little) e teste de novo.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ k, v, highlight }: { k: string; v: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted/60">{k}</span>
      <span className={highlight ? "text-emerald-300 font-semibold" : "text-white"}>{v}</span>
    </div>
  );
}
