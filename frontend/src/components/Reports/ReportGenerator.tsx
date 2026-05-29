import { useState, useRef } from "react";
import { X, FileText, Loader2, ChevronDown, Upload, Trash2, BarChart2 } from "lucide-react";
import { generateReport } from "../../api/client";
import { useEnsaios } from "../../hooks/useEnsaios";
import type {
  ReportRequest, DadosEmpresa, DadosCliente, DadosAmostra,
  CondicoesEnsaio, Assinatura,
} from "../../types";

interface Props {
  ensaioId: number;
  onClose: () => void;
}

const DEFAULT_OBS = `Os resultados aqui apresentados referem-se exclusivamente às amostras analisadas, nas condições em que foram realizados os ensaios, não sendo extensivos a quaisquer lotes, mesmo que similares.
O laboratório não é responsável em caso de interpretação ou uso indevido que se possa fazer deste documento.
A reprodução deste documento deve ser realizada na íntegra.`;

const EMPTY_EMPRESA: DadosEmpresa = { nome: "", endereco: "", telefone: "", email: "", site: "", numero_relatorio: "", logo_data_url: "" };
const EMPTY_CLIENTE: DadosCliente = { nome: "", os: "", contato: "", email_cliente: "", telefone_cliente: "", endereco: "", bairro: "", cidade_uf: "", cep: "", data_recebimento: "", periodo_realizacao: "" };
const EMPTY_AMOSTRA: DadosAmostra = { id_interno: "", id_cliente: "", imagem_data_url: "" };
const EMPTY_CONDICOES: CondicoesEnsaio = {
  temp_laboratorio: "", umidade_laboratorio: "", temp_ensaio: "Tamb",
  num_corpos_prova: "1", celula_carga: "", celula_carga_unidade: "kN",
  comprimento_inicial_mm: "", velocidade_ensaio: "", velocidade_ensaio_unidade: "mm/min",
  tipo_corpo_prova: "", distancia_garras_mm: "", extensometro: "",
  largura_cp_mm: "", espessura_cp_mm: "", preparacao_cp: [],
  data_realizacao: "", equipamentos: "", norma_referencia: "ISO 527-1:2019",
};

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

export default function ReportGenerator({ ensaioId, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: ensaios } = useEnsaios();

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

  const [empresa, setEmpresaState] = useState<DadosEmpresa>(EMPTY_EMPRESA);
  const [cliente, setClienteState] = useState<DadosCliente>(EMPTY_CLIENTE);
  const [amostra, setAmostraState] = useState<DadosAmostra>(EMPTY_AMOSTRA);
  const [objetivos, setObjetivos] = useState("");
  const [condicoes, setCondicoesState] = useState<CondicoesEnsaio>(EMPTY_CONDICOES);
  const [localData, setLocalData] = useState("");
  const [assinaturas, setAssinaturas] = useState<Assinatura[]>([
    { nome: "", cargo: "" },
    { nome: "", cargo: "" },
  ]);
  const [obsFinais, setObsFinais] = useState(DEFAULT_OBS);

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
        ...flags,
        comparacao_ids: flags.include_comparativo ? comparacaoIds : [],
        empresa, cliente, amostra, objetivos,
        condicoes, local_data: localData,
        assinaturas: assinaturas.filter(s => s.nome),
        observacoes_finais: obsFinais,
        operator_name: "", specimen_id: "", standard: "", format: "html", observations: "",
      };
      await generateReport(req);
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
            <h2 className="font-semibold text-white">Gerar Relatório</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-5 space-y-3 flex-1">

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
                placeholder="Realizar os ensaios de tração para caracterizar a amostra..."
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
                <FieldWithSuffix label="Temperatura do Ensaio" value={condicoes.temp_ensaio}
                  onChange={v => setCondicoes("temp_ensaio", v)} placeholder="ex: 23,0 ou Tamb" suffix="°C" />
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
                <FieldWithSuffix label="Comprimento Inicial L₀" value={condicoes.comprimento_inicial_mm}
                  onChange={v => setCondicoes("comprimento_inicial_mm", v)} placeholder="ex: 50" suffix="mm" />
                <FieldWithUnitSelect
                  label="Velocidade do Ensaio"
                  value={condicoes.velocidade_ensaio}
                  onChange={v => setCondicoes("velocidade_ensaio", v)}
                  unit={condicoes.velocidade_ensaio_unidade}
                  onUnit={u => setCondicoes("velocidade_ensaio_unidade", u)}
                  units={["mm/min", "mm/s", "m/min"]}
                  placeholder="ex: 5,00"
                />
                <Field label="Tipo de Corpo de Prova" value={condicoes.tipo_corpo_prova}
                  onChange={v => setCondicoes("tipo_corpo_prova", v)} placeholder="ex: Tipo 1A" />
                <FieldWithSuffix label="Distância entre Garras" value={condicoes.distancia_garras_mm}
                  onChange={v => setCondicoes("distancia_garras_mm", v)} placeholder="ex: 115" suffix="mm" />
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
              <Field label="Norma de Referência" value={condicoes.norma_referencia}
                onChange={v => setCondicoes("norma_referencia", v)} />
            </div>
          </SectionCard>

          {/* Resultados */}
          <SectionCard title="Resultados" enabled={flags.include_resultados} onToggle={() => toggleFlag("include_resultados")}>
            <div className="space-y-3">
              <div className="space-y-2">
                {(
                  [
                    ["include_stress_strain", "Gráfico Tensão × Deformação"],
                    ["include_graficos_adicionais", "Gráfico Força × Deslocamento"],
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
                      Selecione os ensaios para comparar com o atual. As curvas σ×ε e F×d serão sobrepostas no relatório.
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
                              {e.filename.replace(".csv", "")}
                            </span>
                            <span className="text-xs text-muted/60 ml-auto shrink-0">
                              {e.tensao_max_MPa.toFixed(0)} MPa
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
          </SectionCard>

          {/* Conclusão */}
          <SectionCard title="Conclusão / Assinaturas" enabled={flags.include_conclusao} onToggle={() => toggleFlag("include_conclusao")}>
            <div className="space-y-4">
              <Field label="Local e Data" value={localData} onChange={setLocalData}
                placeholder="ex: São Carlos, 27 de maio de 2026." />
              <div className="space-y-3">
                <span className="text-xs text-muted block">Assinaturas</span>
                {assinaturas.map((sig, i) => (
                  <div key={i} className="grid grid-cols-2 gap-3">
                    <Field label={`Assinatura ${i + 1} — Nome`} value={sig.nome}
                      onChange={v => setAssinatura(i, "nome", v)} placeholder="Nome completo" />
                    <Field label="Cargo" value={sig.cargo}
                      onChange={v => setAssinatura(i, "cargo", v)} placeholder="ex: Pesquisador" />
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
