import { useState, useEffect } from "react";
import { Save, X, Plus, Trash2, FolderOpen, Info, Settings, SlidersHorizontal } from "lucide-react";
import { clsx } from "clsx";
import type { IHMRegister } from "../../types";
import { useConfig, useUpdateConfig } from "../../hooks/useConfig";
import RegisterProbe from "./RegisterProbe";

type Section = "geral" | "controle" | "sobre";

interface Props {
  onClose: () => void;
}

type FormState = {
  watch_directory: string;
  auto_load: boolean;
  refresh_interval_s: number;
  ihm_ip: string;
  ihm_port: number;
  ihm_timeout: number;
  ihm_registers: IHMRegister[];
  ftp_port: number;
  ftp_user: string;
  ftp_password: string;
  ftp_remote_dir: string;
  ftp_remote_filename: string;
  realtime_interval_ms: number;
  realtime_bit_name: string;
  realtime_stop_bit_name: string;
  realtime_forca_name: string;
  realtime_deslocamento_name: string;
  clp_ip: string;
  clp_port: number;
  clp_timeout: number;
  control_registers: IHMRegister[];
  control_pulse_ms: number;
  area_seccao_mm2: number;
  comprimento_inicial_mm: number;
  flexao_registers: IHMRegister[];
  flexao_largura_mm: number;
  flexao_espessura_mm: number;
  flexao_span_mm: number;
  flexao_norma: string;
};

const DEFAULT_FORM: FormState = {
  watch_directory: "",
  auto_load: true,
  refresh_interval_s: 5,
  ihm_ip: "",
  ihm_port: 502,
  ihm_timeout: 3,
  ihm_registers: [],
  ftp_port: 21,
  ftp_user: "",
  ftp_password: "",
  ftp_remote_dir: "/",
  ftp_remote_filename: "",
  realtime_interval_ms: 100,
  realtime_bit_name: "teste_ativo_bit",
  realtime_stop_bit_name: "teste_parada_bit",
  realtime_forca_name: "forca_atual",
  realtime_deslocamento_name: "deslocamento_atual",
  clp_ip: "",
  clp_port: 502,
  clp_timeout: 3,
  control_registers: [],
  control_pulse_ms: 300,
  area_seccao_mm2: 0,
  comprimento_inicial_mm: 0,
  flexao_registers: [],
  flexao_largura_mm: 0,
  flexao_espessura_mm: 0,
  flexao_span_mm: 0,
  flexao_norma: "ISO 178",
};

// ── primitives ────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return <span className="text-xs font-medium text-muted block mb-1.5">{children}</span>;
}

function Hint({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-muted/60 mt-1.5 leading-relaxed">{children}</p>;
}

function Field({
  label, hint, children, className = "",
}: {
  label: string; hint?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={className}>
      <Label>{label}</Label>
      {children}
      {hint && <Hint>{hint}</Hint>}
    </div>
  );
}

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors font-mono placeholder:text-muted/40";

const smallInputCls =
  "bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors font-mono";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-base font-semibold text-white mb-1">{children}</h2>;
}

function SectionDesc({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-muted/70 mb-6 leading-relaxed">{children}</p>;
}

function Divider() {
  return <hr className="border-border my-6" />;
}

// ── nav tab ───────────────────────────────────────────────────

function NavTab({
  icon, label, active, onClick,
}: {
  icon: React.ReactNode; label: string; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left",
        active
          ? "bg-accent/10 text-accent font-medium"
          : "text-muted hover:text-slate-300 hover:bg-border/40"
      )}
    >
      <span className={clsx("flex-shrink-0", active ? "text-accent" : "text-muted/60")}>{icon}</span>
      {label}
    </button>
  );
}

// ── sections ──────────────────────────────────────────────────

function GeralSection({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  return (
    <div>
      <SectionTitle>Geral</SectionTitle>
      <SectionDesc>Diretório de monitoramento e comportamento de carregamento automático.</SectionDesc>

      <Field
        label="Diretório monitorado"
        hint="O software detecta arquivos .csv no formato HISTORY V1.0 inseridos nesta pasta."
      >
        <input
          value={form.watch_directory}
          onChange={(e) => setForm((f) => ({ ...f, watch_directory: e.target.value }))}
          placeholder="ex: C:\IHM_Exports\"
          className={inputCls}
        />
      </Field>

      <Divider />

      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-white font-medium">Monitoramento automático</p>
            <p className="text-xs text-muted/70 mt-0.5">
              Detecta e importa novos arquivos em segundo plano.
            </p>
          </div>
          <button
            onClick={() => setForm((f) => ({ ...f, auto_load: !f.auto_load }))}
            className={clsx(
              "relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent",
              "transition-colors duration-200 focus:outline-none",
              form.auto_load ? "bg-accent" : "bg-border"
            )}
          >
            <span
              className={clsx(
                "inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200",
                form.auto_load ? "translate-x-4" : "translate-x-0"
              )}
            />
          </button>
        </div>

        <Field label="Intervalo de verificação (segundos)">
          <input
            type="number"
            min={1}
            max={60}
            value={form.refresh_interval_s}
            onChange={(e) => setForm((f) => ({ ...f, refresh_interval_s: Number(e.target.value) }))}
            className={clsx(smallInputCls, "w-24")}
          />
        </Field>
      </div>
    </div>
  );
}


const DATA_TYPE_OPTIONS = ["uint16", "decimal", "int32", "decimal32", "float32", "coil"] as const;
const WORD2_TYPES = ["int32", "decimal32", "float32"]; // tipos com escala numérica (float32 sem escala)

function RegisterTable({
  registers, onAdd, onUpdate, onRemove, showRole = false, addLabel = "Adicionar",
}: {
  registers: IHMRegister[];
  onAdd: () => void;
  onUpdate: (i: number, patch: Partial<IHMRegister>) => void;
  onRemove: (i: number) => void;
  showRole?: boolean;
  addLabel?: string;
}) {
  const cols = showRole
    ? "grid-cols-[76px_96px_96px_1fr_84px_60px_72px_32px]"
    : "grid-cols-[88px_116px_1fr_96px_72px_72px_32px]";
  const headers = showRole
    ? ["Endereço", "Role", "Nome", "Descrição", "Tipo", "Escala", "Ordem", ""]
    : ["Endereço", "Nome", "Descrição", "Tipo", "Escala", "Ordem", ""];
  const inputCell =
    "bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white " +
    "focus:outline-none focus:border-accent transition-colors w-full";

  return (
    <div>
      <div className="flex justify-end mb-2">
        <button
          onClick={onAdd}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                     bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
        >
          <Plus size={12} />
          {addLabel}
        </button>
      </div>

      {registers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border py-10 text-center">
          <p className="text-sm text-muted/60">Nenhum registrador configurado.</p>
          <p className="text-xs text-muted/40 mt-1">Clique em "{addLabel}" para mapear um endereço Modbus.</p>
        </div>
      ) : (
        <>
          <div className={clsx("grid gap-2 px-3 mb-1.5", cols)}>
            {headers.map((h, idx) => (
              <span key={idx} className="text-[10px] font-medium text-muted/50 uppercase tracking-wider">{h}</span>
            ))}
          </div>

          <div className="space-y-2">
            {registers.map((r, i) => (
              <div key={i} className={clsx("grid gap-2 items-center bg-surface border border-border rounded-lg px-3 py-2.5", cols)}>
                <input type="number" value={r.address} placeholder="40000"
                  onChange={(e) => onUpdate(i, { address: Number(e.target.value) })} className={inputCell} />
                {showRole && (
                  <input value={r.role ?? ""} placeholder="role"
                    onChange={(e) => onUpdate(i, { role: e.target.value })} className={inputCell} />
                )}
                <input value={r.name} placeholder="chave"
                  onChange={(e) => onUpdate(i, { name: e.target.value })} className={inputCell} />
                <input value={r.description} placeholder="Descrição"
                  onChange={(e) => onUpdate(i, { description: e.target.value })} className={inputCell} />
                <select value={r.data_type}
                  onChange={(e) => onUpdate(i, { data_type: e.target.value as IHMRegister["data_type"] })} className={inputCell}>
                  {DATA_TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                {r.data_type !== "float32" && r.data_type !== "coil" ? (
                  <input type="number" step="0.001" value={r.scale ?? 1}
                    onChange={(e) => onUpdate(i, { scale: Number(e.target.value) })} className={inputCell} />
                ) : (
                  <span className="text-xs text-muted/30 font-mono text-center">—</span>
                )}
                {WORD2_TYPES.includes(r.data_type) ? (
                  <select value={r.word_order ?? "big"}
                    onChange={(e) => onUpdate(i, { word_order: e.target.value as "big" | "little" })} className={inputCell}>
                    <option value="big">big</option>
                    <option value="little">little</option>
                  </select>
                ) : (
                  <span className="text-xs text-muted/30 font-mono text-center">—</span>
                )}
                <button onClick={() => onRemove(i)}
                  className="text-muted hover:text-red-400 transition-colors flex items-center justify-center">
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-3 space-y-1">
            <p className="text-[10px] font-mono text-muted/50">
              float32 / int32 / decimal32 — 2 registradores (N + N+1). Ordem: big = HI 1º (ABCD) · little = LO 1º (CDAB, ex.: Mitsubishi/registradores D)
            </p>
            {registers.some((r) => WORD2_TYPES.includes(r.data_type) || r.data_type === "decimal") && (
              <p className="text-[10px] font-mono text-muted/50">decimal/int32/decimal32 — valor_real = raw × escala</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function makeRegHandlers(
  key: "ihm_registers" | "control_registers",
  setForm: React.Dispatch<React.SetStateAction<FormState>>,
  defaults: Partial<IHMRegister>,
) {
  return {
    add: () => setForm((f) => ({
      ...f,
      [key]: [...f[key], { name: "", address: 0, description: "", data_type: "uint16", scale: 1.0, word_order: "big", ...defaults }],
    })),
    update: (i: number, patch: Partial<IHMRegister>) => setForm((f) => {
      const regs = [...f[key]];
      regs[i] = { ...regs[i], ...patch };
      return { ...f, [key]: regs };
    }),
    remove: (i: number) => setForm((f) => ({ ...f, [key]: f[key].filter((_, j) => j !== i) })),
  };
}

function ControleSection({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  const h = makeRegHandlers("control_registers", setForm, { writable: true, role: "" });
  return (
    <div>
      <SectionTitle>Controle (CLP)</SectionTitle>
      <SectionDesc>
        Conexão Modbus TCP direta com o CLP e mapeamento dos registradores de comando/leitura.
        Roles esperados: <span className="text-slate-300 font-mono">iniciar, parar, sentido_cima, sentido_baixo,
        deslocamento_programado, velocidade, limite_forca, forca_atual, deslocamento_atual,
        material_integro_bit, ruptura_bit</span>.
      </SectionDesc>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <Field label="IP do CLP" hint="Se vazio, usa o IP da Conexão IHM.">
          <input value={form.clp_ip} onChange={(e) => setForm((f) => ({ ...f, clp_ip: e.target.value }))}
            placeholder="192.168.11.10" className={inputCls} />
        </Field>
        <Field label="Porta Modbus">
          <input type="number" value={form.clp_port}
            onChange={(e) => setForm((f) => ({ ...f, clp_port: Number(e.target.value) }))} className={inputCls} />
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-5">
        <Field label="Timeout (s)">
          <input type="number" min={1} max={30} value={form.clp_timeout}
            onChange={(e) => setForm((f) => ({ ...f, clp_timeout: Number(e.target.value) }))} className={smallInputCls + " w-full"} />
        </Field>
        <Field label="Pulso comando (ms)" hint="Duração do pulso em coils iniciar/parar.">
          <input type="number" min={50} max={2000} step={10} value={form.control_pulse_ms}
            onChange={(e) => setForm((f) => ({ ...f, control_pulse_ms: Number(e.target.value) }))} className={smallInputCls + " w-full"} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-2">
        <Field label="Área da seção padrão (mm²)" hint="Usada para derivar tensão σ = F/A.">
          <input type="number" step="0.01" value={form.area_seccao_mm2}
            onChange={(e) => setForm((f) => ({ ...f, area_seccao_mm2: Number(e.target.value) }))} className={inputCls} />
        </Field>
        <Field label="Comprimento inicial L₀ (mm)" hint="Usado para derivar deformação ε = ΔL/L₀.">
          <input type="number" step="0.01" value={form.comprimento_inicial_mm}
            onChange={(e) => setForm((f) => ({ ...f, comprimento_inicial_mm: Number(e.target.value) }))} className={inputCls} />
        </Field>
      </div>

      <Divider />

      <div className="mb-2">
        <SectionTitle>Registradores de controle</SectionTitle>
        <SectionDesc>Endereços Modbus de escrita (comandos/setpoints) e leitura (força/deslocamento/flags).</SectionDesc>
      </div>
      <RegisterTable
        registers={form.control_registers}
        onAdd={h.add} onUpdate={h.update} onRemove={h.remove}
        showRole addLabel="Adicionar registrador"
      />

      <Divider />
      <RegisterProbe registers={form.control_registers} />
    </div>
  );
}

function SobreSection() {
  const items = [
    { label: "Software", value: "Analisador de Ensaios de Tração" },
    { label: "Versão", value: "1.0.0" },
    { label: "Banco de dados", value: "SQLite — tracao.db" },
    { label: "Formato suportado", value: "HISTORY V1.0 (UTF-16 LE, TAB)" },
    { label: "Backend", value: "FastAPI + Uvicorn" },
    { label: "Frontend", value: "React 18 + Vite + Tailwind" },
  ];
  return (
    <div>
      <SectionTitle>Sobre</SectionTitle>
      <SectionDesc>Informações da aplicação.</SectionDesc>
      <div className="space-y-3">
        {items.map(({ label, value }) => (
          <div key={label} className="flex items-baseline gap-4 py-2.5 border-b border-border/50 last:border-0">
            <span className="w-36 flex-shrink-0 text-xs text-muted">{label}</span>
            <span className="text-sm font-mono text-slate-300">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────

const NAV_ITEMS: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: "geral",          label: "Geral",           icon: <FolderOpen size={15} /> },
  { id: "controle",       label: "Controle (CLP)",   icon: <SlidersHorizontal size={15} /> },
];

export default function ConfigPanel({ onClose }: Props) {
  const { data: config, isLoading } = useConfig();
  const updateMut = useUpdateConfig();
  const [section, setSection] = useState<Section>("geral");
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);

  useEffect(() => {
    if (config) setForm((prev) => ({
      ...prev,
      ...config,
      ihm_registers: config.ihm_registers ?? [],
      control_registers: config.control_registers ?? [],
      flexao_registers: config.flexao_registers ?? [],
    }));
  }, [config]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted text-sm">Carregando configurações...</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* ── Left nav ── */}
      <aside className="w-52 flex-shrink-0 flex flex-col border-r border-border bg-surface">
        <div className="flex items-center justify-between px-4 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Settings size={15} className="text-accent" />
            <span className="font-semibold text-sm text-white">Configurações</span>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white transition-colors p-0.5">
            <X size={15} />
          </button>
        </div>

        <nav className="flex-1 p-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavTab
              key={item.id}
              icon={item.icon}
              label={item.label}
              active={section === item.id}
              onClick={() => setSection(item.id)}
            />
          ))}
        </nav>

        <div className="p-2 border-t border-border">
          <NavTab
            icon={<Info size={15} />}
            label="Sobre"
            active={section === "sobre"}
            onClick={() => setSection("sobre")}
          />
        </div>
      </aside>

      {/* ── Right content ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        <div className="flex-1 overflow-auto">
          <div className="p-8 max-w-2xl">
            {section === "geral"         && <GeralSection         form={form} setForm={setForm} />}
            {section === "controle"      && <ControleSection      form={form} setForm={setForm} />}
            {section === "sobre"         && <SobreSection />}
          </div>
        </div>

        {/* ── Save bar ── */}
        {section !== "sobre" && (
          <div className="flex-shrink-0 border-t border-border bg-bg px-8 py-3 flex items-center gap-4">
            <button
              onClick={() => updateMut.mutate(form)}
              disabled={updateMut.isPending}
              className="flex items-center gap-2 px-5 py-2 bg-accent text-bg rounded-lg
                         font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              <Save size={14} />
              {updateMut.isPending ? "Salvando..." : "Salvar e Aplicar"}
            </button>
            {updateMut.isSuccess && (
              <span className="text-sm text-green-400">Configurações salvas.</span>
            )}
            {updateMut.isError && (
              <span className="text-sm text-red-400">Erro ao salvar.</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
