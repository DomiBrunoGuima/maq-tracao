import { useState, useRef, useEffect } from "react";
import { useUsuarioOpcional } from "../../hooks/useAuth";
import { useQueryClient } from "@tanstack/react-query";
import { X, FileText, Loader2, ChevronDown, Upload, Trash2, BarChart2, Sparkles, Plus } from "lucide-react";
import { generateReport, getCamposRelatorio } from "../../api/client";
import { useClientes, useEnsaios } from "../../hooks/useEnsaios";
import { useEnsaiosFlexao } from "../../hooks/useFlexao";
import type {
  ReportRequest, DadosEmpresa, DadosCliente, DadosAmostra,
  CondicoesEnsaio, Assinatura, TipoEnsaio, GraficoRelatorio, Requisito,
} from "../../types";

interface Props {
  ensaioId: number;
  tipo?: TipoEnsaio;
  onClose: () => void;
}

const DEFAULT_OBS = `Os resultados aqui apresentados referem-se exclusivamente às amostras analisadas, nas condições em que foram realizados os ensaios, não sendo extensivos a quaisquer lotes, mesmo que similares.
O laboratório não é responsável em caso de interpretação ou uso indevido que se possa fazer deste documento.
A reprodução deste documento deve ser realizada na íntegra.`;

const EMPTY_EMPRESA: DadosEmpresa = { nome: "", endereco: "", telefone: "", email: "", site: "", numero_relatorio: "", logo_data_url: "" };
const EMPTY_CLIENTE: DadosCliente = { nome: "", os: "", contato: "", email_cliente: "", telefone_cliente: "", endereco: "", bairro: "", cidade_uf: "", cep: "", data_recebimento: "", periodo_realizacao: "" };
const EMPTY_AMOSTRA: DadosAmostra = { id_interno: "", id_cliente: "", imagem_data_url: "" };
const EMPTY_CONDICOES: CondicoesEnsaio = {
  temp_laboratorio: "", umidade_laboratorio: "", temp_ensaio: "",
  num_corpos_prova: "1", celula_carga: "", celula_carga_unidade: "kN",
  comprimento_inicial_mm: "", velocidade_ensaio: "", velocidade_ensaio_unidade: "mm/min",
  tipo_corpo_prova: "", distancia_garras_mm: "", extensometro: "",
  largura_cp_mm: "", espessura_cp_mm: "", preparacao_cp: [],
  data_realizacao: "", equipamentos: "", norma_referencia: "ISO 527-1:2019",
  metodo_ensaio: "", certificado_calibracao: "",
};

// Requisito padrão da qualidade (editável e removível na tela)
const REQUISITOS_PADRAO: Requisito[] = [
  { propriedade: "alongamento", criterio: ">=", valor: "350", referencia: "NBR 15561" },
];

const TITULO_TRACAO = "Relatório de Resistência ao Alongamento (Tração)";

// Deformação usa L₀ (base de medida); alongamento usa a distância entre garras.
const GRAFICOS: [GraficoRelatorio, string][] = [
  ["tensao_alongamento", "Tensão × Alongamento (%) — base: distância entre garras"],
  ["tensao_deformacao", "Tensão × Deformação (%) — base: L₀"],
  ["tensao_deslocamento", "Tensão × Deslocamento (mm)"],
  ["forca_deslocamento", "Força × Deslocamento (mm)"],
];

const PROPRIEDADES: [Requisito["propriedade"], string, string][] = [
  ["tensao_max", "Tensão máxima", "MPa"],
  ["alongamento", "Alongamento final", "%"],
  ["forca_max", "Força máxima", "N"],
];

const PREPARACAO_OPCOES = ["Injeção", "Usinagem", "Prensagem", "Estampagem", "Recorte", "Enviados pelo Cliente"];

// ── helpers ──────────────────────────────────────────────────

const INPUT_CLS = "bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white \
focus:outline-none focus:border-accent transition-colors font-mono";

function Field({ label, value, onChange, placeholder, type = "text", className = "" }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs text-muted">{label}</span>
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={INPUT_CLS} />
    </label>
  );
}

function FieldWithSuffix({ label, value, onChange, placeholder, suffix, className = "" }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; suffix: string; className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs text-muted">{label}</span>
      <div className="flex items-center gap-0">
        <input type="text" value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="bg-bg border border-border rounded-l-lg px-3 py-1.5 text-sm text-white
                     focus:outline-none focus:border-accent transition-colors font-mono flex-1 min-w-0" />
        <span className="bg-surface border border-l-0 border-border rounded-r-lg
                         px-2.5 py-1.5 text-xs text-muted font-mono whitespace-nowrap shrink-0">
          {suffix}
        </span>
      </div>
    </label>
  );
}

function FieldWithUnitSelect({ label, value, onChange, unit, onUnit, units, placeholder, className = "" }: {
  label: string; value: string; onChange: (v: string) => void;
  unit: string; onUnit: (u: string) => void; units: string[];
  placeholder?: string; className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs text-muted">{label}</span>
      <div className="flex items-center gap-0">
        <input type="text" value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="bg-bg border border-border rounded-l-lg px-3 py-1.5 text-sm text-white
                     focus:outline-none focus:border-accent transition-colors font-mono flex-1 min-w-0" />
        <select
          value={unit}
          onChange={e => onUnit(e.target.value)}
          className="bg-surface border border-l-0 border-border rounded-r-lg
                     px-2 py-1.5 text-xs text-muted font-mono focus:outline-none
                     focus:border-accent transition-colors cursor-pointer shrink-0"
        >
          {units.map(u => <option key={u} value={u}>{u}</option>)}
        </select>
      </div>
    </label>
  );
}

function ImageUpload({ label, value, onChange }: {
  label: string; value: string; onChange: (v: string) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange(reader.result as string);
    reader.readAsDataURL(file);
  }
  return (
    <div>
      <span className="text-xs text-muted block mb-1.5">{label}</span>
      <div className="flex items-center gap-3">
        <button type="button" onClick={() => ref.current?.click()}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border
                     rounded text-xs text-white hover:border-accent transition-colors">
          <Upload size={12} /> Selecionar imagem
        </button>
        <input ref={ref} type="file" accept="image/*" onChange={handle} className="hidden" />
        {value && (
          <div className="flex items-center gap-2">
            <img src={value} alt={label} className="h-10 w-10 object-contain border border-border rounded" />
            <button type="button" onClick={() => onChange("")} className="text-muted hover:text-red-400 transition-colors">
              <Trash2 size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SectionCard({ title, enabled, onToggle, children }: {
  title: string; enabled: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="flex items-center gap-2.5 px-4 py-3 bg-surface cursor-pointer select-none"
           onClick={onToggle}>
        <input type="checkbox" checked={enabled}
          onChange={onToggle} onClick={e => e.stopPropagation()}
          className="w-4 h-4 accent-accent shrink-0" />
        <span className="text-sm font-medium text-white flex-1">{title}</span>
        <ChevronDown size={14} className={`text-muted transition-transform ${enabled ? "" : "-rotate-90"}`} />
      </div>
      {enabled && (
        <div className="p-4 bg-bg border-t border-border">
          {children}
        </div>
      )}
    </div>
  );
}

// ── main component ────────────────────────────────────────────

export default function ReportGenerator({ ensaioId, tipo = "tracao", onClose }: Props) {
  const usuario = useUsuarioOpcional();
  const flexao = tipo === "flexao";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: ensaiosTracao } = useEnsaios();
  const { data: ensaiosFlexao } = useEnsaiosFlexao();
  // Comparativo só entre ensaios do mesmo tipo
  const ensaios = (flexao ? ensaiosFlexao : ensaiosTracao)?.map(e => ({
    id: e.id, nome: e.nome, filename: e.filename,
    tensao: "tensao_flexao_max_MPa" in e ? e.tensao_flexao_max_MPa : e.tensao_max_MPa,
  }));
  const { data: clientes } = useClientes();
  const qc = useQueryClient();
  const [clienteId, setClienteId] = useState<number | null>(null);
  const [autoPreenchido, setAutoPreenchido] = useState(false);

  const [flags, setFlags] = useState({
    include_empresa: true,
    include_cliente: false,
    include_amostra: true,
    include_objetivos: false,
    include_condicoes: true,
    include_resultados: true,
    include_stress_strain: true,
    include_graficos_adicionais: false,
    include_comparativo: false,
    include_raw_data: false,
    include_conclusao: true,
    include_observacoes_finais: true,
  });

  const [comparacaoIds, setComparacaoIds] = useState<number[]>([]);

  // Modelo resumido (pedido da qualidade): só tração
  const [titulo, setTitulo] = useState(flexao ? "" : TITULO_TRACAO);
  const [modelo, setModelo] = useState<"resumido" | "completo">(flexao ? "completo" : "resumido");
  const resumido = !flexao && modelo === "resumido";
  const [escopo, setEscopo] = useState<"teste" | "lote">("teste");
  const [cpIds, setCpIds] = useState<number[]>([]);
  const [graficos, setGraficos] = useState<GraficoRelatorio[]>(["tensao_alongamento"]);
  const [requisitos, setRequisitos] = useState<Requisito[]>(flexao ? [] : REQUISITOS_PADRAO);
  // Norma define o modelo: NBR 15561 (alongamento ≥ 350 %) ou ISO 13953 (solda de topo:
  // força máxima e tipo de falha dúctil/frágil escolhido pelo operador para cada CP)
  const [normaRelatorio, setNormaRelatorio] = useState<"NBR 15561" | "ISO 13953">("NBR 15561");
  const iso13953 = resumido && normaRelatorio === "ISO 13953";
  const [falhas, setFalhas] = useState<Record<string, string>>({});
  function escolherNorma(n: "NBR 15561" | "ISO 13953") {
    setNormaRelatorio(n);
    setGraficos([n === "ISO 13953" ? "forca_deslocamento" : "tensao_alongamento"]);
    setCondicoesState(c => ({ ...c, metodo_ensaio: n, norma_referencia: n }));
  }
  const [conclusaoManual, setConclusaoManual] = useState("");
  const [extras, setExtras] = useState({
    include_sumario: flexao,
    include_tabela_detalhada: false,
    include_responsabilidade: flexao,
    assinar_emissor: flexao,
  });

  const [empresa, setEmpresaState] = useState<DadosEmpresa>(EMPTY_EMPRESA);
  const [cliente, setClienteState] = useState<DadosCliente>(EMPTY_CLIENTE);
  const [amostra, setAmostraState] = useState<DadosAmostra>(EMPTY_AMOSTRA);
  const [objetivos, setObjetivos] = useState("");
  const [condicoes, setCondicoesState] = useState<CondicoesEnsaio>(
    flexao ? { ...EMPTY_CONDICOES, norma_referencia: "ISO 178:2019" } : EMPTY_CONDICOES,
  );
  const [localData, setLocalData] = useState("");
  const [assinaturas, setAssinaturas] = useState<Assinatura[]>([
    { nome: "", cargo: "", funcao: "Executado por" },
    { nome: "", cargo: "", funcao: "Validado por" },
  ]);
  const [obsFinais, setObsFinais] = useState(DEFAULT_OBS);

  // Campos automáticos: setup do ensaio, cliente cadastrado, norma e dados do
  // último relatório (empresa, assinaturas, equipamento). Só preenche o que veio.
  useEffect(() => {
    let cancel = false;
    getCamposRelatorio(ensaioId, tipo).then((c) => {
      if (cancel) return;
      const cheios = <T extends object>(o: Partial<T>) =>
        Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v != null)) as Partial<T>;
      setEmpresaState((e) => ({ ...e, ...cheios(c.empresa), numero_relatorio: e.numero_relatorio || c.numero_relatorio_sugerido }));
      if (c.cliente) {
        setClienteState((x) => ({ ...x, ...cheios(c.cliente!) }));
        setFlags((f) => ({ ...f, include_cliente: true }));
      }
      setClienteId(c.cliente_id);
      setAmostraState((a) => ({ ...a, ...cheios(c.amostra) }));
      setCondicoesState((x) => ({
        ...x, ...cheios(c.condicoes),
        equipamentos: x.equipamentos || c.equipamentos,
      }));
      if (c.assinaturas?.length) {
        const padrao = ["Executado por", "Validado por"];
        setAssinaturas(c.assinaturas.map((s, i) => ({ ...s, funcao: s.funcao ?? padrao[i] ?? "" })));
      }
      if (c.requisitos?.length) setRequisitos(c.requisitos);
      if (c.titulo) setTitulo(c.titulo);
      if (c.metodo_ensaio) setCondicoesState((x) => ({ ...x, metodo_ensaio: x.metodo_ensaio || c.metodo_ensaio }));
      setAutoPreenchido(true);
    }).catch(() => { /* sem preenchimento automático */ });
    return () => { cancel = true; };
  }, [ensaioId, tipo]);

  function escolherCliente(id: number | null) {
    setClienteId(id);
    const c = clientes?.find((x) => x.id === id);
    if (!c) return;
    setClienteState((x) => ({
      ...x, nome: c.nome, contato: c.contato, email_cliente: c.email, telefone_cliente: c.telefone,
      endereco: c.endereco, bairro: c.bairro, cidade_uf: c.cidade_uf, cep: c.cep,
    }));
  }

  function setEmpresa(field: keyof DadosEmpresa, v: string) {
    setEmpresaState(e => ({ ...e, [field]: v }));
  }
  function setCliente(field: keyof DadosCliente, v: string) {
    setClienteState(c => ({ ...c, [field]: v }));
  }
  function setAmostra(field: keyof DadosAmostra, v: string) {
    setAmostraState(a => ({ ...a, [field]: v }));
  }
  function setCondicoes(field: keyof CondicoesEnsaio, v: string | string[]) {
    setCondicoesState(c => ({ ...c, [field]: v }));
  }
  function togglePreparacao(op: string) {
    setCondicoesState(c => ({
      ...c,
      preparacao_cp: c.preparacao_cp.includes(op)
        ? c.preparacao_cp.filter(x => x !== op)
        : [...c.preparacao_cp, op],
    }));
  }
  function toggleFlag(k: keyof typeof flags) {
    setFlags(f => ({ ...f, [k]: !f[k] }));
  }
  function setAssinatura(i: number, field: keyof Assinatura, v: string) {
    setAssinaturas(sigs => sigs.map((s, idx) => idx === i ? { ...s, [field]: v } : s));
  }
  function toggleCp(id: number) {
    setCpIds(ids => ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]);
  }
  function toggleGrafico(g: GraficoRelatorio) {
    setGraficos(gs => gs.includes(g) ? gs.filter(x => x !== g) : [...gs, g]);
  }
  function setRequisito(i: number, field: keyof Requisito, v: string) {
    setRequisitos(rs => rs.map((r, idx) => idx === i ? { ...r, [field]: v } as Requisito : r));
  }
  function toggleComparacao(id: number) {
    setComparacaoIds(ids =>
      ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]
    );
  }

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const req: ReportRequest = {
        ensaio_id: ensaioId,
        tipo,
        cliente_id: clienteId,
        ...flags,
        ...extras,
        titulo,
        modelo: flexao ? "completo" : modelo,
        escopo: resumido ? escopo : "teste",
        cp_ids: resumido && escopo === "lote" ? cpIds : [],
        graficos: resumido ? graficos : [],
        requisitos: requisitos.filter(r => r.valor.trim()),
        conclusao_manual: conclusaoManual,
        norma_relatorio: normaRelatorio,
        falhas: iso13953 ? falhas : {},
        ...(iso13953 ? { requisitos: [] } : {}),
        comparacao_ids: flags.include_comparativo ? comparacaoIds : [],
        empresa, cliente, amostra, objetivos,
        condicoes, local_data: localData,
        assinaturas: assinaturas.filter(s => s.nome),
        observacoes_finais: obsFinais,
        operator_name: "", specimen_id: "", standard: "", format: "html", observations: "",
      };
      await generateReport(req);
      qc.invalidateQueries({ queryKey: ["relatorios"] });
      qc.invalidateQueries({ queryKey: ["clientes"] });
    } catch (err: any) {
      const detail = err?.response?.data ? await err.response.data.text?.() : null;
      setError(detail ?? err?.message ?? "Erro desconhecido ao gerar relatório");
    } finally {
      setLoading(false);
    }
  }

  const outrosEnsaios = ensaios?.filter(e => e.id !== ensaioId) ?? [];

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <FileText className="text-accent" size={18} />
            <h2 className="font-semibold text-white">Gerar Relatório{flexao ? " de Flexão" : ""}</h2>
            {autoPreenchido && (
              <span className="flex items-center gap-1 text-[10px] text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                <Sparkles size={10} /> campos preenchidos a partir do ensaio
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-muted hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-5 space-y-3 flex-1">

          {/* Modelo do relatório */}
          <div className="rounded-lg border border-border p-4 space-y-3 bg-bg">
            <Field label="Título do relatório" value={titulo} onChange={setTitulo}
              placeholder={flexao ? "Relatório de Ensaio de Flexão" : TITULO_TRACAO} />
            {!flexao && (
              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Modelo</span>
                  <select value={modelo} onChange={e => setModelo(e.target.value as "resumido" | "completo")} className={INPUT_CLS}>
                    <option value="resumido">Resumido (Fmax, σmax, alongamento e conclusão)</option>
                    <option value="completo">Completo (todas as propriedades calculadas)</option>
                  </select>
                </label>
                {resumido && (
                  <label className="flex flex-col gap-1">
                    <span className="text-xs text-muted">Norma do relatório</span>
                    <select value={normaRelatorio} onChange={e => escolherNorma(e.target.value as "NBR 15561" | "ISO 13953")} className={INPUT_CLS}>
                      <option value="NBR 15561">NBR 15561 (alongamento ≥ 350 %)</option>
                      <option value="ISO 13953">ISO 13953 (solda de topo: força e dúctil/frágil)</option>
                    </select>
                  </label>
                )}
                {resumido && (
                  <label className="flex flex-col gap-1">
                    <span className="text-xs text-muted">Relatório de</span>
                    <select value={escopo} onChange={e => setEscopo(e.target.value as "teste" | "lote")} className={INPUT_CLS}>
                      <option value="teste">Um teste (este CP)</option>
                      <option value="lote">Um lote (vários CPs)</option>
                    </select>
                  </label>
                )}
              </div>
            )}
            {resumido && escopo === "lote" && (
              <div>
                <p className="text-xs text-muted mb-2">
                  Este ensaio já é o primeiro CP. Marque os outros CPs do mesmo lote:
                </p>
                {outrosEnsaios.length === 0 ? (
                  <p className="text-xs text-muted/50 italic">Nenhum outro ensaio disponível.</p>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1 border border-border rounded-lg p-2 bg-surface">
                    {outrosEnsaios.map(e => (
                      <label key={e.id} className="flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer hover:bg-bg transition-colors">
                        <input type="checkbox" checked={cpIds.includes(e.id)} onChange={() => toggleCp(e.id)}
                          className="w-3.5 h-3.5 accent-accent shrink-0" />
                        <span className="text-xs font-mono text-slate-300 truncate">{e.nome || e.filename.replace(".csv", "")}</span>
                        <span className="text-xs text-muted/60 ml-auto shrink-0">
                          {e.tensao != null ? `${e.tensao.toFixed(1)} MPa` : "—"}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
                <p className="text-xs text-accent mt-1.5">{cpIds.length + 1} corpo{cpIds.length ? "s" : ""} de prova no relatório</p>
              </div>
            )}
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {(
                [
                  ["include_sumario", "Sumário"],
                  ["include_responsabilidade", "Quadro de responsabilidade (controle interno)"],
                  ["assinar_emissor", "Usuário logado assina o relatório"],
                ] as [keyof typeof extras, string][]
              ).map(([k, label]) => (
                <label key={k} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={extras[k]}
                    onChange={() => setExtras(x => ({ ...x, [k]: !x[k] }))}
                    className="w-4 h-4 accent-accent" />
                  <span className="text-sm text-slate-300">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Empresa */}
          <SectionCard title="Cabeçalho / Empresa" enabled={flags.include_empresa} onToggle={() => toggleFlag("include_empresa")}>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Nome da Empresa" value={empresa.nome} onChange={v => setEmpresa("nome", v)} className="col-span-2" />
                <Field label="Endereço" value={empresa.endereco} onChange={v => setEmpresa("endereco", v)} className="col-span-2" />
                <Field label="Telefone" value={empresa.telefone} onChange={v => setEmpresa("telefone", v)} />
                <Field label="E-mail" value={empresa.email} onChange={v => setEmpresa("email", v)} />
                <Field label="Site" value={empresa.site} onChange={v => setEmpresa("site", v)} />
                <Field label="Número do Relatório" value={empresa.numero_relatorio} onChange={v => setEmpresa("numero_relatorio", v)} placeholder="ex: AFK01538/26" />
              </div>
              <ImageUpload label="Logo" value={empresa.logo_data_url} onChange={v => setEmpresa("logo_data_url", v)} />
            </div>
          </SectionCard>

          {/* Cliente */}
          <SectionCard title="Dados do Cliente / OS" enabled={flags.include_cliente} onToggle={() => toggleFlag("include_cliente")}>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 col-span-2">
                <span className="text-xs text-muted">Cliente cadastrado</span>
                <select value={clienteId ?? ""} onChange={e => escolherCliente(e.target.value ? Number(e.target.value) : null)}
                  className={INPUT_CLS}>
                  <option value="">— digitar manualmente —</option>
                  {clientes?.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </select>
              </label>
              <Field label="Cliente" value={cliente.nome} onChange={v => setCliente("nome", v)} />
              <Field label="OS (Ordem de Serviço)" value={cliente.os} onChange={v => setCliente("os", v)} />
              <Field label="Contato" value={cliente.contato} onChange={v => setCliente("contato", v)} />
              <Field label="E-mail" value={cliente.email_cliente} onChange={v => setCliente("email_cliente", v)} />
              <Field label="Telefone" value={cliente.telefone_cliente} onChange={v => setCliente("telefone_cliente", v)} />
              <Field label="Endereço" value={cliente.endereco} onChange={v => setCliente("endereco", v)} />
              <Field label="Bairro" value={cliente.bairro} onChange={v => setCliente("bairro", v)} />
              <Field label="Cidade/UF" value={cliente.cidade_uf} onChange={v => setCliente("cidade_uf", v)} />
              <Field label="CEP" value={cliente.cep} onChange={v => setCliente("cep", v)} />
              <Field label="Data de Recebimento" value={cliente.data_recebimento} onChange={v => setCliente("data_recebimento", v)} placeholder="dd/mm/aaaa" />
              <Field label="Período de Realização" value={cliente.periodo_realizacao} onChange={v => setCliente("periodo_realizacao", v)} placeholder="ex: 12/05/2026 a 26/05/2026" className="col-span-2" />
            </div>
          </SectionCard>

          {/* Amostra */}
          <SectionCard title="Identificação da Amostra" enabled={flags.include_amostra} onToggle={() => toggleFlag("include_amostra")}>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="ID Interno" value={amostra.id_interno} onChange={v => setAmostra("id_interno", v)} placeholder="ex: AFK2603566" />
                <Field label="ID do Cliente" value={amostra.id_cliente} onChange={v => setAmostra("id_cliente", v)} placeholder="ex: Amostra de PP" />
              </div>
              <ImageUpload label="Foto da Amostra" value={amostra.imagem_data_url} onChange={v => setAmostra("imagem_data_url", v)} />
            </div>
          </SectionCard>

          {/* Objetivos */}
          <SectionCard title="Objetivos" enabled={flags.include_objetivos} onToggle={() => toggleFlag("include_objetivos")}>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Descrição do objetivo do ensaio</span>
              <textarea value={objetivos} onChange={e => setObjetivos(e.target.value)} rows={3}
                placeholder={`Realizar os ensaios de ${flexao ? "flexão" : "tração"} para caracterizar a amostra...`}
                className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white
                           focus:outline-none focus:border-accent transition-colors resize-none" />
            </label>
          </SectionCard>

          {/* Condições */}
          <SectionCard title="Condições do Ensaio" enabled={flags.include_condicoes} onToggle={() => toggleFlag("include_condicoes")}>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <FieldWithSuffix label="Temperatura do Laboratório" value={condicoes.temp_laboratorio}
                  onChange={v => setCondicoes("temp_laboratorio", v)} placeholder="ex: 23,0" suffix="°C" />
                <FieldWithSuffix label="Umidade do Laboratório" value={condicoes.umidade_laboratorio}
                  onChange={v => setCondicoes("umidade_laboratorio", v)} placeholder="ex: 59" suffix="%" />
                {flexao ? (
                  <FieldWithSuffix label="Temperatura do Ensaio" value={condicoes.temp_ensaio}
                    onChange={v => setCondicoes("temp_ensaio", v)} placeholder="ex: 23,0 ou Tamb" suffix="°C" />
                ) : (
                  <Field label="Certificado de Calibração" value={condicoes.certificado_calibracao ?? ""}
                    onChange={v => setCondicoes("certificado_calibracao", v)} placeholder="nº do certificado" />
                )}
                <Field label="Número de Corpos de Prova" value={condicoes.num_corpos_prova}
                  onChange={v => setCondicoes("num_corpos_prova", v)} />
                <FieldWithUnitSelect
                  label="Célula de Carga"
                  value={condicoes.celula_carga}
                  onChange={v => setCondicoes("celula_carga", v)}
                  unit={condicoes.celula_carga_unidade}
                  onUnit={u => setCondicoes("celula_carga_unidade", u)}
                  units={["N", "kN"]}
                  placeholder="ex: 5"
                />
                {!flexao && (
                  <FieldWithSuffix label="Comprimento Inicial L₀" value={condicoes.comprimento_inicial_mm}
                    onChange={v => setCondicoes("comprimento_inicial_mm", v)} placeholder="ex: 50" suffix="mm" />
                )}
                <FieldWithUnitSelect
                  label="Velocidade do Ensaio"
                  value={condicoes.velocidade_ensaio}
                  onChange={v => setCondicoes("velocidade_ensaio", v)}
                  unit={condicoes.velocidade_ensaio_unidade}
                  onUnit={u => setCondicoes("velocidade_ensaio_unidade", u)}
                  units={["mm/min", "mm/s", "m/min"]}
                  placeholder="ex: 5,00"
                />
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Tipo de Corpo de Prova</span>
                  <input list="tipos-cp" value={condicoes.tipo_corpo_prova}
                    onChange={e => setCondicoes("tipo_corpo_prova", e.target.value)}
                    placeholder={flexao ? "ex: Barra 80 × 10 × 4" : "ex: Tipo 1, 2 ou 3"} className={INPUT_CLS} />
                  {!flexao && (
                    <datalist id="tipos-cp">
                      <option value="Tipo 1" /><option value="Tipo 2" /><option value="Tipo 3" />
                    </datalist>
                  )}
                </label>
                <FieldWithSuffix label={flexao ? "Distância entre Apoios (L)" : "Distância entre Garras"} value={condicoes.distancia_garras_mm}
                  onChange={v => setCondicoes("distancia_garras_mm", v)} placeholder={flexao ? "ex: 64" : "ex: 115"} suffix="mm" />
                <Field label="Extensômetro" value={condicoes.extensometro}
                  onChange={v => setCondicoes("extensometro", v)} placeholder="ex: Até a ruptura" />
                <FieldWithSuffix label="Largura dos CPs" value={condicoes.largura_cp_mm}
                  onChange={v => setCondicoes("largura_cp_mm", v)} placeholder="ex: 9,98 ± 0,01" suffix="mm" />
                <FieldWithSuffix label="Espessura dos CPs" value={condicoes.espessura_cp_mm}
                  onChange={v => setCondicoes("espessura_cp_mm", v)} placeholder="ex: 4,13 ± 0,01" suffix="mm" />
              </div>
              <div>
                <span className="text-xs text-muted block mb-2">Preparação dos Corpos de Prova</span>
                <div className="flex flex-wrap gap-3">
                  {PREPARACAO_OPCOES.map(op => (
                    <label key={op} className="flex items-center gap-1.5 cursor-pointer">
                      <input type="checkbox"
                        checked={condicoes.preparacao_cp.includes(op)}
                        onChange={() => togglePreparacao(op)}
                        className="w-3.5 h-3.5 accent-accent" />
                      <span className="text-xs text-slate-300">{op}</span>
                    </label>
                  ))}
                </div>
              </div>
              <Field label="Data de Realização" value={condicoes.data_realizacao}
                onChange={v => setCondicoes("data_realizacao", v)} placeholder="dd/mm/aaaa" />
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted">Equipamento(s)</span>
                <textarea value={condicoes.equipamentos} onChange={e => setCondicoes("equipamentos", e.target.value)}
                  rows={2} placeholder="Nome do equipamento, modelo..."
                  className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white
                             focus:outline-none focus:border-accent transition-colors resize-none font-mono" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Método de Ensaio" value={condicoes.metodo_ensaio ?? ""}
                  onChange={v => setCondicoes("metodo_ensaio", v)} placeholder="ex: NBR 15561 ou NBR ISO 6259" />
                <Field label="Norma de Referência" value={condicoes.norma_referencia}
                  onChange={v => setCondicoes("norma_referencia", v)} />
              </div>
              <p className="text-[11px] text-muted">Campos vazios não aparecem no relatório (ex.: temperatura do ensaio, célula de carga).</p>
            </div>
          </SectionCard>

          {/* Resultados */}
          <SectionCard title="Resultados" enabled={flags.include_resultados} onToggle={() => toggleFlag("include_resultados")}>
            {resumido ? (
              <div className="space-y-2">
                <span className="text-xs text-muted block">Gráficos (todos os CPs no mesmo gráfico)</span>
                {GRAFICOS.map(([g, label]) => (
                  <label key={g} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={graficos.includes(g)} onChange={() => toggleGrafico(g)}
                      className="w-4 h-4 accent-accent" />
                    <span className="text-sm text-slate-300">{label}</span>
                  </label>
                ))}
                {graficos.includes("tensao_alongamento") && !condicoes.distancia_garras_mm && (
                  <p className="text-xs text-amber-400">Preencha a Distância entre Garras em Condições do Ensaio; sem ela o alongamento usa L₀.</p>
                )}
                <label className="flex items-center gap-2 cursor-pointer border-t border-border/50 pt-2">
                  <input type="checkbox" checked={extras.include_tabela_detalhada}
                    onChange={() => setExtras(x => ({ ...x, include_tabela_detalhada: !x.include_tabela_detalhada }))}
                    className="w-4 h-4 accent-accent" />
                  <span className="text-sm text-slate-300">Tabela detalhada (módulo, energia, rigidez...)</span>
                </label>
              </div>
            ) : (
            <div className="space-y-3">
              <div className="space-y-2">
                {(
                  [
                    ["include_stress_strain", flexao ? "Gráfico Tensão × Deformação de flexão (σf × εf)" : "Gráfico Tensão × Deformação"],
                    ["include_graficos_adicionais", flexao ? "Gráfico Força × Deflexão" : "Gráfico Força × Deslocamento"],
                    ["include_raw_data", "Tabela de dados brutos"],
                  ] as [keyof typeof flags, string][]
                ).map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={flags[k]}
                      onChange={() => toggleFlag(k)}
                      className="w-4 h-4 accent-accent" />
                    <span className="text-sm text-slate-300">{label}</span>
                  </label>
                ))}
              </div>

              {/* Comparativo */}
              <div className="border-t border-border/50 pt-3">
                <label className="flex items-center gap-2 cursor-pointer mb-3">
                  <input type="checkbox" checked={flags.include_comparativo}
                    onChange={() => toggleFlag("include_comparativo")}
                    className="w-4 h-4 accent-accent" />
                  <BarChart2 size={13} className="text-muted" />
                  <span className="text-sm text-slate-300">Gráficos Comparativos</span>
                </label>

                {flags.include_comparativo && (
                  <div className="ml-6">
                    <p className="text-xs text-muted mb-2">
                      Selecione os ensaios {flexao ? "de flexão " : ""}para comparar com o atual. As curvas σ×ε e {flexao ? "F×δ" : "F×d"} serão sobrepostas no relatório.
                    </p>
                    {outrosEnsaios.length === 0 ? (
                      <p className="text-xs text-muted/50 italic">Nenhum outro ensaio disponível.</p>
                    ) : (
                      <div className="max-h-48 overflow-y-auto space-y-1 border border-border rounded-lg p-2 bg-bg">
                        {outrosEnsaios.map(e => (
                          <label key={e.id}
                            className="flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer
                                       hover:bg-surface transition-colors">
                            <input
                              type="checkbox"
                              checked={comparacaoIds.includes(e.id)}
                              onChange={() => toggleComparacao(e.id)}
                              className="w-3.5 h-3.5 accent-accent shrink-0"
                            />
                            <span className="text-xs font-mono text-slate-300 truncate">
                              {e.nome || e.filename.replace(".csv", "")}
                            </span>
                            <span className="text-xs text-muted/60 ml-auto shrink-0">
                              {e.tensao != null ? `${e.tensao.toFixed(0)} MPa` : "—"}
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                    {comparacaoIds.length > 0 && (
                      <p className="text-xs text-accent mt-1.5">
                        {comparacaoIds.length} ensaio{comparacaoIds.length > 1 ? "s" : ""} selecionado{comparacaoIds.length > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
            )}
          </SectionCard>

          {/* Conclusão */}
          <SectionCard title="Conclusão / Assinaturas" enabled={flags.include_conclusao} onToggle={() => toggleFlag("include_conclusao")}>
            <div className="space-y-4">
              {usuario && (
                <p className="text-xs text-muted bg-accent/5 border border-accent/20 rounded-lg px-3 py-2">
                  O relatório sai automaticamente com os seus dados como emissor
                  (<span className="text-slate-300">{[usuario.nome, usuario.cargo, usuario.registro].filter(Boolean).join(" · ")}</span>)
                  {!usuario.mestre && !usuario.desenvolvedor && ", e a sua assinatura entra aqui se não estiver na lista"}.
                </p>
              )}
              {iso13953 && (
                <div className="space-y-2">
                  <span className="text-xs text-muted block">
                    Tipo de falha de cada CP (ISO 13953). Todos dúcteis: APROVADO; algum frágil: REPROVADO.
                  </span>
                  {[ensaioId, ...(escopo === "lote" ? cpIds : [])].map(id => {
                    const e = ensaios?.find(x => x.id === id);
                    return (
                      <div key={id} className="grid grid-cols-[1fr_auto] gap-3 items-center">
                        <span className="text-xs font-mono text-slate-300 truncate">{e ? (e.nome || e.filename.replace(".csv", "")) : `Ensaio ${id}`}</span>
                        <select value={falhas[String(id)] ?? ""} onChange={ev => setFalhas(f => ({ ...f, [String(id)]: ev.target.value }))}
                          className={INPUT_CLS}>
                          <option value="">— escolher —</option>
                          <option value="Dúctil">Dúctil</option>
                          <option value="Frágil">Frágil</option>
                        </select>
                      </div>
                    );
                  })}
                </div>
              )}
              {resumido && !iso13953 && (
                <div className="space-y-2">
                  <span className="text-xs text-muted block">
                    Requisitos normativos (definidos pelo laboratório; já vem com Alongamento ≥ 350 % da NBR 15561). Cada linha sai Aprovado/Reprovado comparando o menor valor dos CPs.
                  </span>
                  {requisitos.map((r, i) => (
                    <div key={i} className="grid grid-cols-[1.3fr_0.7fr_0.8fr_1.4fr_auto] gap-2 items-center">
                      <select value={r.propriedade} onChange={e => setRequisito(i, "propriedade", e.target.value)} className={INPUT_CLS}>
                        {PROPRIEDADES.map(([k, l, u]) => <option key={k} value={k}>{l} ({u})</option>)}
                      </select>
                      <select value={r.criterio} onChange={e => setRequisito(i, "criterio", e.target.value)} className={INPUT_CLS}>
                        <option value=">=">mínimo ≥</option>
                        <option value="<=">máximo ≤</option>
                      </select>
                      <input value={r.valor} onChange={e => setRequisito(i, "valor", e.target.value)} placeholder="valor" className={INPUT_CLS} />
                      <input value={r.referencia} onChange={e => setRequisito(i, "referencia", e.target.value)} placeholder="norma citada, ex.: NBR 15561" className={INPUT_CLS} />
                      <button type="button" onClick={() => setRequisitos(rs => rs.filter((_, idx) => idx !== i))}
                        className="text-muted hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
                    </div>
                  ))}
                  <button type="button"
                    onClick={() => setRequisitos(rs => [...rs, { propriedade: rs.length === 0 ? "tensao_max" : "alongamento", criterio: ">=", valor: "", referencia: condicoes.metodo_ensaio || "" }])}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded text-xs text-white hover:border-accent transition-colors">
                    <Plus size={12} /> Adicionar requisito
                  </button>
                  {requisitos.filter(r => r.valor.trim()).length === 0 && (
                    <label className="flex flex-col gap-1">
                      <span className="text-xs text-muted">Sem requisitos: conclusão escrita à mão</span>
                      <select value={conclusaoManual} onChange={e => setConclusaoManual(e.target.value)} className={INPUT_CLS}>
                        <option value="">— não mostrar —</option>
                        <option value="APROVADO">APROVADO</option>
                        <option value="REPROVADO">REPROVADO</option>
                      </select>
                    </label>
                  )}
                </div>
              )}
              <Field label="Local e Data" value={localData} onChange={setLocalData}
                placeholder="ex: São Carlos, 27 de maio de 2026." />
              <div className="space-y-3">
                <span className="text-xs text-muted block">Assinaturas</span>
                {assinaturas.map((sig, i) => (
                  <div key={i} className="grid grid-cols-3 gap-3">
                    <Field label="Função" value={sig.funcao ?? ""}
                      onChange={v => setAssinatura(i, "funcao", v)} placeholder="ex: Executado por" />
                    <Field label={`Assinatura ${i + 1} — Nome`} value={sig.nome}
                      onChange={v => setAssinatura(i, "nome", v)} placeholder="Nome completo" />
                    <Field label="Cargo" value={sig.cargo}
                      onChange={v => setAssinatura(i, "cargo", v)} placeholder="ex: Inspetor de Qualidade" />
                  </div>
                ))}
              </div>
            </div>
          </SectionCard>

          {/* Observações Finais */}
          <SectionCard title="Observações Finais" enabled={flags.include_observacoes_finais} onToggle={() => toggleFlag("include_observacoes_finais")}>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Texto (uma observação por linha)</span>
              <textarea value={obsFinais} onChange={e => setObsFinais(e.target.value)} rows={5}
                className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white
                           focus:outline-none focus:border-accent transition-colors resize-none" />
            </label>
          </SectionCard>

        </div>

        {/* Footer */}
        {error && (
          <div className="mx-5 mb-0 mt-2 px-3 py-2 bg-red-900/30 border border-red-700/50 rounded-lg text-xs text-red-300 font-mono shrink-0">
            {error}
          </div>
        )}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-border shrink-0">
          <button onClick={onClose}
            className="px-4 py-2 text-sm text-muted hover:text-white transition-colors">
            Cancelar
          </button>
          <button onClick={handleGenerate} disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent text-bg rounded-lg
                       text-sm font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50">
            {loading ? <><Loader2 size={14} className="animate-spin" />Gerando...</> : <><FileText size={14} />Gerar Relatório</>}
          </button>
        </div>
      </div>
    </div>
  );
}
