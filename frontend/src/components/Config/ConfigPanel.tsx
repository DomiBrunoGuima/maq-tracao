import { useState, useEffect } from "react";
import { Save, X, Plus, Trash2, Download, Cpu, FolderOpen, Info, Sliders, Settings } from "lucide-react";
import { clsx } from "clsx";
import type { IHMRegister } from "../../types";
import { useConfig, useUpdateConfig, useFetchFtpCsv } from "../../hooks/useConfig";

type Section = "geral" | "ihm" | "ftp" | "registradores" | "sobre";

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

function IHMSection({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  return (
    <div>
      <SectionTitle>Conexão IHM</SectionTitle>
      <SectionDesc>
        Parâmetros de rede para comunicação Modbus TCP com a IHM. O IP configurado aqui é
        compartilhado com o módulo FTP.
      </SectionDesc>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <Field label="Endereço IP">
          <input
            value={form.ihm_ip}
            onChange={(e) => setForm((f) => ({ ...f, ihm_ip: e.target.value }))}
            placeholder="192.168.8.10"
            className={inputCls}
          />
        </Field>
        <Field label="Porta Modbus">
          <input
            type="number"
            value={form.ihm_port}
            onChange={(e) => setForm((f) => ({ ...f, ihm_port: Number(e.target.value) }))}
            className={inputCls}
          />
        </Field>
      </div>

      <Field
        label="Timeout de conexão (segundos)"
        hint="Tempo máximo aguardado para cada leitura Modbus antes de considerar a IHM inacessível."
      >
        <input
          type="number"
          min={1}
          max={30}
          value={form.ihm_timeout}
          onChange={(e) => setForm((f) => ({ ...f, ihm_timeout: Number(e.target.value) }))}
          className={clsx(smallInputCls, "w-24")}
        />
      </Field>

      <Divider />

      <div className="rounded-lg bg-accent/5 border border-accent/20 px-4 py-3">
        <p className="text-xs text-accent/80 font-medium mb-0.5">Captura automática</p>
        <p className="text-xs text-muted/70 leading-relaxed">
          Os registradores configurados na aba <span className="text-slate-300">Registradores</span> são
          lidos via Modbus sempre que um novo ensaio é detectado.
        </p>
      </div>
    </div>
  );
}

function FTPSection({
  form, setForm, fetchFtpMut, updateMut,
}: {
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
  fetchFtpMut: ReturnType<typeof useFetchFtpCsv>;
  updateMut: ReturnType<typeof useUpdateConfig>;
}) {
  return (
    <div>
      <SectionTitle>Transferência FTP</SectionTitle>
      <SectionDesc>
        Credenciais e caminho para baixar o arquivo CSV diretamente da IHM via FTP.
        O endereço IP é o mesmo configurado em Conexão IHM.
      </SectionDesc>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <Field label="Usuário">
          <input
            value={form.ftp_user}
            onChange={(e) => setForm((f) => ({ ...f, ftp_user: e.target.value }))}
            placeholder="ihm"
            className={inputCls}
          />
        </Field>
        <Field label="Senha">
          <input
            type="password"
            value={form.ftp_password}
            onChange={(e) => setForm((f) => ({ ...f, ftp_password: e.target.value }))}
            placeholder="••••••"
            className={inputCls}
          />
        </Field>
      </div>

      <div className="grid grid-cols-[1fr_auto] gap-4 mb-5">
        <Field label="Diretório remoto">
          <input
            value={form.ftp_remote_dir}
            onChange={(e) => setForm((f) => ({ ...f, ftp_remote_dir: e.target.value }))}
            placeholder="/HMI/HMI-000/History/CSV"
            className={inputCls}
          />
        </Field>
        <Field label="Porta FTP">
          <input
            type="number"
            value={form.ftp_port}
            onChange={(e) => setForm((f) => ({ ...f, ftp_port: Number(e.target.value) }))}
            className={clsx(smallInputCls, "w-24")}
          />
        </Field>
      </div>

      <Field
        label="Nome do arquivo remoto"
        hint="Nome exato do arquivo CSV na IHM. ex: H0001.csv"
      >
        <input
          value={form.ftp_remote_filename}
          onChange={(e) => setForm((f) => ({ ...f, ftp_remote_filename: e.target.value }))}
          placeholder="H0001.csv"
          className={inputCls}
        />
      </Field>

      <Divider />

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <p className="text-xs font-semibold text-white">Buscar agora</p>
        <p className="text-xs text-muted/70 leading-relaxed">
          Salva as configurações acima e baixa o arquivo imediatamente.
        </p>
        <div className="flex items-center gap-4">
          <button
            onClick={() => updateMut.mutate(form, { onSuccess: () => fetchFtpMut.mutate() })}
            disabled={fetchFtpMut.isPending || !form.ihm_ip || !form.ftp_remote_filename}
            title={
              !form.ihm_ip ? "Configure o IP da IHM primeiro" :
              !form.ftp_remote_filename ? "Informe o nome do arquivo" : ""
            }
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              "bg-accent text-bg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            <Download size={14} />
            {fetchFtpMut.isPending ? "Baixando..." : "Buscar CSV da IHM"}
          </button>
          {fetchFtpMut.isSuccess && (
            <p className="text-xs text-green-400">
              ✓ {fetchFtpMut.data.filename} — {fetchFtpMut.data.bytes_received} bytes
            </p>
          )}
          {fetchFtpMut.isError && (
            <p className="text-xs text-red-400">
              {(fetchFtpMut.error as any)?.response?.data?.detail ?? "Erro ao conectar via FTP"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function RegistradoresSection({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  function addReg() {
    setForm((f) => ({
      ...f,
      ihm_registers: [
        ...f.ihm_registers,
        { name: "", address: 0, description: "", data_type: "uint16", scale: 1.0 },
      ],
    }));
  }

  function updateReg(i: number, patch: Partial<IHMRegister>) {
    setForm((f) => {
      const regs = [...f.ihm_registers];
      regs[i] = { ...regs[i], ...patch };
      return { ...f, ihm_registers: regs };
    });
  }

  function removeReg(i: number) {
    setForm((f) => ({ ...f, ihm_registers: f.ihm_registers.filter((_, j) => j !== i) }));
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-1">
        <div>
          <SectionTitle>Registradores Modbus</SectionTitle>
          <SectionDesc>
            Mapeamento de endereços Modbus lidos da IHM. Suporta uint16, decimal (com escala) e
            float32 IEEE 754 big-endian (dois registradores consecutivos).
          </SectionDesc>
        </div>
        <button
          onClick={addReg}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                     bg-accent/10 text-accent hover:bg-accent/20 transition-colors mt-1"
        >
          <Plus size={12} />
          Adicionar
        </button>
      </div>

      {form.ihm_registers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border py-10 text-center">
          <p className="text-sm text-muted/60">Nenhum registrador configurado.</p>
          <p className="text-xs text-muted/40 mt-1">Clique em "Adicionar" para mapear um endereço Modbus.</p>
        </div>
      ) : (
        <>
          {/* Table header */}
          <div className="grid grid-cols-[90px_120px_1fr_100px_80px_32px] gap-2 px-3 mb-1.5">
            {["Endereço", "Nome", "Descrição", "Tipo", "Escala", ""].map((h) => (
              <span key={h} className="text-[10px] font-medium text-muted/50 uppercase tracking-wider">{h}</span>
            ))}
          </div>

          <div className="space-y-2">
            {form.ihm_registers.map((r, i) => (
              <div
                key={i}
                className="grid grid-cols-[90px_120px_1fr_100px_80px_32px] gap-2 items-center
                           bg-surface border border-border rounded-lg px-3 py-2.5"
              >
                <input
                  type="number"
                  value={r.address}
                  onChange={(e) => updateReg(i, { address: Number(e.target.value) })}
                  placeholder="40000"
                  className="bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white
                             focus:outline-none focus:border-accent transition-colors w-full"
                />
                <input
                  value={r.name}
                  onChange={(e) => updateReg(i, { name: e.target.value })}
                  placeholder="chave"
                  className="bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white
                             focus:outline-none focus:border-accent transition-colors w-full"
                />
                <input
                  value={r.description}
                  onChange={(e) => updateReg(i, { description: e.target.value })}
                  placeholder="Descrição"
                  className="bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white
                             focus:outline-none focus:border-accent transition-colors w-full"
                />
                <select
                  value={r.data_type}
                  onChange={(e) => updateReg(i, { data_type: e.target.value as IHMRegister["data_type"] })}
                  className="bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white
                             focus:outline-none focus:border-accent transition-colors w-full"
                >
                  <option value="uint16">uint16</option>
                  <option value="decimal">decimal</option>
                  <option value="float32">float32</option>
                </select>
                {r.data_type !== "float32" ? (
                  <input
                    type="number"
                    step="0.001"
                    value={r.scale ?? 1}
                    onChange={(e) => updateReg(i, { scale: Number(e.target.value) })}
                    className="bg-bg border border-border rounded px-2 py-1 text-xs font-mono text-white
                               focus:outline-none focus:border-accent transition-colors w-full"
                  />
                ) : (
                  <span className="text-xs text-muted/30 font-mono text-center">—</span>
                )}
                <button
                  onClick={() => removeReg(i)}
                  className="text-muted hover:text-red-400 transition-colors flex items-center justify-center"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          {(form.ihm_registers.some((r) => r.data_type === "float32") ||
            form.ihm_registers.some((r) => r.data_type !== "float32" && (r.scale ?? 1) !== 1)) && (
            <div className="mt-3 space-y-1">
              {form.ihm_registers.some((r) => r.data_type === "float32") && (
                <p className="text-[10px] font-mono text-muted/50">
                  float32 — lê registradores N (HI) + N+1 (LO), IEEE 754 big-endian
                </p>
              )}
              {form.ihm_registers.some((r) => r.data_type !== "float32" && (r.scale ?? 1) !== 1) && (
                <p className="text-[10px] font-mono text-muted/50">
                  decimal — valor_real = raw × escala
                </p>
              )}
            </div>
          )}
        </>
      )}
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
  { id: "ihm",            label: "Conexão IHM",      icon: <Cpu size={15} /> },
  { id: "ftp",            label: "FTP",              icon: <Download size={15} /> },
  { id: "registradores",  label: "Registradores",    icon: <Sliders size={15} /> },
];

export default function ConfigPanel({ onClose }: Props) {
  const { data: config, isLoading } = useConfig();
  const updateMut = useUpdateConfig();
  const fetchFtpMut = useFetchFtpCsv();
  const [section, setSection] = useState<Section>("geral");
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);

  useEffect(() => {
    if (config) setForm((prev) => ({ ...prev, ...config, ihm_registers: config.ihm_registers ?? [] }));
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
            {section === "ihm"           && <IHMSection           form={form} setForm={setForm} />}
            {section === "ftp"           && <FTPSection           form={form} setForm={setForm} fetchFtpMut={fetchFtpMut} updateMut={updateMut} />}
            {section === "registradores" && <RegistradoresSection form={form} setForm={setForm} />}
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
