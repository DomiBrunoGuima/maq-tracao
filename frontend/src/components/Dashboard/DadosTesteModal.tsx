import { useState } from "react";
import { ClipboardList, Save, X } from "lucide-react";
import { useUpdateEnsaio } from "../../hooks/useEnsaios";
import { useUpdateEnsaioFlexao } from "../../hooks/useFlexao";
import type { TipoEnsaio } from "../../types";
import CadastroTeste, { type CadastroForm } from "../Common/CadastroTeste";

const SETUP_LABELS: Record<string, [string, string]> = {
  velocidade: ["Velocidade", "mm/min"],
  deslocamento: ["Deslocamento programado", "mm"],
  limite_forca: ["Limite de força", "N"],
  area_seccao: ["Área da seção", "mm²"],
  comprimento_inicial: ["Comprimento inicial L₀", "mm"],
  sentido: ["Sentido", ""],
};

interface EnsaioCadastro {
  id: number;
  nome: string;
  observacoes?: string;
  cliente_id: number | null;
  amostra?: string;
  norma?: string;
  operador?: string;
  setup?: Record<string, unknown>;
}

/** Edita cliente, amostra, norma, operador e observações de um ensaio já gravado
 * (tração ou flexão). A curva e os resultados gravados não são alterados. */
export default function DadosTesteModal({ ensaio, tipo = "tracao", onClose }: {
  ensaio: EnsaioCadastro; tipo?: TipoEnsaio; onClose: () => void;
}) {
  const mutTracao = useUpdateEnsaio();
  const mutFlexao = useUpdateEnsaioFlexao();
  const mut = tipo === "flexao" ? mutFlexao : mutTracao;
  const [nome, setNome] = useState(ensaio.nome);
  const [obs, setObs] = useState(ensaio.observacoes ?? "");
  const [cad, setCad] = useState<CadastroForm>({
    cliente_id: ensaio.cliente_id, amostra: ensaio.amostra ?? "",
    norma: ensaio.norma ?? "", operador: ensaio.operador ?? "",
  });
  const setup = Object.entries(ensaio.setup ?? {}).filter(([, v]) => v != null && v !== "");

  async function salvar() {
    await mut.mutateAsync({
      id: ensaio.id,
      body: {
        nome, observacoes: obs, amostra: cad.amostra, norma: cad.norma, operador: cad.operador,
        ...(cad.cliente_id != null ? { cliente_id: cad.cliente_id } : { limpar_cliente: true }),
      },
    });
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-3xl shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-2">
            <ClipboardList className="text-accent" size={18} />
            <h2 className="font-semibold text-white">Dados do teste</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Nome do ensaio</span>
            <input value={nome} onChange={(e) => setNome(e.target.value)}
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent" />
          </label>
          <CadastroTeste value={cad} onChange={setCad} tipo={tipo} />
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Observações</span>
            <textarea value={obs} onChange={(e) => setObs(e.target.value)} rows={3}
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent resize-none" />
          </label>
          {setup.length > 0 && (
            <div>
              <p className="text-xs text-muted mb-1.5">Parâmetros usados no ensaio (gravados automaticamente)</p>
              <div className="flex flex-wrap gap-2">
                {setup.map(([k, v]) => (
                  <span key={k} className="text-xs font-mono bg-panel border border-border/50 rounded-lg px-2.5 py-1">
                    <span className="text-muted">{SETUP_LABELS[k]?.[0] ?? k} </span>
                    <span className="text-white">{String(v)} {SETUP_LABELS[k]?.[1] ?? ""}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {mut.isError && <p className="text-xs text-red-400">Não foi possível salvar.</p>}
        </div>
        <div className="flex justify-end gap-3 p-5 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 text-sm text-muted hover:text-white">Cancelar</button>
          <button onClick={salvar} disabled={mut.isPending}
            className="flex items-center gap-2 px-5 py-2 bg-accent text-bg rounded-lg text-sm font-semibold disabled:opacity-50">
            <Save size={14} /> Salvar
          </button>
        </div>
      </div>
    </div>
  );
}
