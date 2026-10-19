import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus } from "lucide-react";
import { createCliente } from "../../api/client";
import { useClientes, useNormas } from "../../hooks/useEnsaios";
import type { Norma } from "../../types";

export interface CadastroForm {
  cliente_id: number | null;
  amostra: string;
  norma: string;
  operador: string;
}

export const CADASTRO_VAZIO: CadastroForm = { cliente_id: null, amostra: "", norma: "", operador: "" };

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors placeholder:text-muted/40";

/**
 * Cliente, amostra, norma e operador do teste. O que for preenchido aqui é gravado
 * automaticamente no ensaio quando ele termina. Ao escolher uma norma, onNorma
 * recebe os parâmetros sugeridos para pré-preencher velocidade, L₀ etc.
 */
export default function CadastroTeste({
  value, onChange, tipo, onNorma, disabled,
}: {
  value: CadastroForm;
  onChange: (v: CadastroForm) => void;
  tipo: "tracao" | "flexao";
  onNorma?: (n: Norma) => void;
  disabled?: boolean;
}) {
  const { data: clientes } = useClientes();
  const { data: normas } = useNormas(tipo);
  const qc = useQueryClient();
  const [novoNome, setNovoNome] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const set = <K extends keyof CadastroForm>(k: K, v: CadastroForm[K]) => onChange({ ...value, [k]: v });
  const normaSel = normas?.find((n) => n.codigo === value.norma);

  async function salvarNovoCliente() {
    if (!novoNome?.trim()) return;
    try {
      const c = await createCliente({
        nome: novoNome.trim(), documento: "", contato: "", email: "", telefone: "",
        endereco: "", bairro: "", cidade_uf: "", cep: "", observacoes: "",
      });
      await qc.invalidateQueries({ queryKey: ["clientes"] });
      set("cliente_id", c.id);
      setNovoNome(null);
      setErro(null);
    } catch (e: any) {
      setErro(e?.response?.data?.detail ?? "Não foi possível cadastrar o cliente.");
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-muted uppercase tracking-wide">
        Dados do teste <span className="normal-case tracking-normal text-muted/60">— vão automaticamente para o ensaio e o relatório</span>
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <span className="text-xs font-medium text-muted block mb-1.5">Cliente</span>
          {novoNome == null ? (
            <div className="flex gap-1.5">
              <select
                value={value.cliente_id ?? ""}
                disabled={disabled}
                onChange={(e) => set("cliente_id", e.target.value ? Number(e.target.value) : null)}
                className={inputCls}
              >
                <option value="">— sem cliente —</option>
                {clientes?.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
              <button
                type="button" title="Cadastrar cliente novo" disabled={disabled}
                onClick={() => setNovoNome("")}
                className="px-2.5 rounded-lg border border-border bg-bg text-muted hover:text-accent hover:border-accent transition-colors"
              >
                <Plus size={14} />
              </button>
            </div>
          ) : (
            <div className="flex gap-1.5">
              <input
                autoFocus value={novoNome} placeholder="Nome do cliente"
                onChange={(e) => setNovoNome(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") salvarNovoCliente(); if (e.key === "Escape") setNovoNome(null); }}
                className={inputCls}
              />
              <button type="button" onClick={salvarNovoCliente}
                className="px-3 rounded-lg bg-accent text-bg text-xs font-semibold">OK</button>
            </div>
          )}
          {erro && <p className="text-[11px] text-red-400 mt-1">{erro}</p>}
        </div>
        <div>
          <span className="text-xs font-medium text-muted block mb-1.5">Amostra / identificação</span>
          <input value={value.amostra} disabled={disabled} placeholder="ex: Lote 23 · CP 1"
            onChange={(e) => set("amostra", e.target.value)} className={inputCls} />
        </div>
        <div>
          <span className="text-xs font-medium text-muted block mb-1.5">Norma de referência</span>
          <select
            value={value.norma} disabled={disabled}
            onChange={(e) => {
              set("norma", e.target.value);
              const n = normas?.find((x) => x.codigo === e.target.value);
              if (n && onNorma) onNorma(n);
            }}
            className={inputCls}
          >
            <option value="">— nenhuma —</option>
            {normas?.map((n) => <option key={n.codigo} value={n.codigo}>{n.codigo} · {n.material}</option>)}
            {value.norma && !normaSel && <option value={value.norma}>{value.norma}</option>}
          </select>
        </div>
        <div>
          <span className="text-xs font-medium text-muted block mb-1.5">Operador</span>
          <input value={value.operador} disabled={disabled} placeholder="Nome de quem executa"
            onChange={(e) => set("operador", e.target.value)} className={inputCls} />
        </div>
      </div>
      {normaSel && (
        <p className="flex items-start gap-1.5 text-[11px] text-muted">
          <BookOpen size={12} className="mt-0.5 flex-shrink-0 text-accent" />
          <span>
            <span className="text-slate-300">{normaSel.titulo}</span> · CP {normaSel.corpo_prova}. {normaSel.observacao}{" "}
            <span className="text-muted/60">Valores sugeridos; confira a edição vigente da norma.</span>
          </span>
        </p>
      )}
    </div>
  );
}
