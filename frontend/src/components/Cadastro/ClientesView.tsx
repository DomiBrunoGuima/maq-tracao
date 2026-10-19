import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, GitCompare, Plus, Save, Search, Trash2, Users } from "lucide-react";
import { clsx } from "clsx";
import {
  createCliente,
  deleteCliente,
  getEnsaiosDoCliente,
  relatorioUrl,
  updateCliente,
} from "../../api/client";
import { useClientes, useRelatorios } from "../../hooks/useEnsaios";
import type { Cliente, ClienteIn } from "../../types";
import { dataUTC } from "../../utils/data";

const VAZIO: ClienteIn = {
  nome: "", documento: "", contato: "", email: "", telefone: "",
  endereco: "", bairro: "", cidade_uf: "", cep: "", observacoes: "",
};

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors placeholder:text-muted/40";

function semAcento(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function Campo({ label, value, onChange, className = "", placeholder }: {
  label: string; value: string; onChange: (v: string) => void; className?: string; placeholder?: string;
}) {
  return (
    <label className={clsx("flex flex-col gap-1", className)}>
      <span className="text-xs text-muted">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={inputCls} />
    </label>
  );
}

export default function ClientesView({
  initialId, onOpenEnsaio, onCompare,
}: {
  initialId?: number | null;
  onOpenEnsaio: (id: number) => void;
  onCompare: (ids: number[]) => void;
}) {
  const qc = useQueryClient();
  const { data: clientes, isLoading } = useClientes();
  const [selId, setSelId] = useState<number | null>(initialId ?? null);
  const [novo, setNovo] = useState(false);
  const [form, setForm] = useState<ClienteIn>(VAZIO);
  const [filtro, setFiltro] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);

  const sel: Cliente | undefined = clientes?.find((c) => c.id === selId);

  useEffect(() => {
    if (sel) setForm({ ...VAZIO, ...Object.fromEntries(Object.keys(VAZIO).map((k) => [k, (sel as any)[k] ?? ""])) });
  }, [sel?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const { data: ensaios } = useQuery({
    queryKey: ["ensaios", "cliente", selId],
    queryFn: () => getEnsaiosDoCliente(selId!),
    enabled: selId != null,
  });
  const { data: relatorios } = useRelatorios(selId != null ? { cliente_id: selId } : { cliente_id: -1 });

  const lista = useMemo(() => {
    const f = semAcento(filtro.trim());
    if (!f) return clientes ?? [];
    return (clientes ?? []).filter((c) =>
      f.split(/\s+/).every((t) => semAcento(`${c.nome} ${c.contato} ${c.cidade_uf} ${c.documento}`).includes(t)),
    );
  }, [clientes, filtro]);

  const set = (k: keyof ClienteIn, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function salvar() {
    setMsg(null);
    try {
      if (novo || sel == null) {
        const c = await createCliente(form);
        setSelId(c.id);
        setNovo(false);
      } else {
        await updateCliente(sel.id, form);
      }
      await qc.invalidateQueries({ queryKey: ["clientes"] });
      qc.invalidateQueries({ queryKey: ["ensaios"] });
      setMsg({ ok: true, texto: "Cliente salvo." });
    } catch (e: any) {
      setMsg({ ok: false, texto: e?.response?.data?.detail ?? "Não foi possível salvar." });
    }
  }

  async function apagar() {
    if (!sel) return;
    if (!window.confirm(`Apagar o cliente "${sel.nome}"? Os ensaios e relatórios dele continuam, só ficam sem cliente.`)) return;
    await deleteCliente(sel.id);
    setSelId(null);
    setForm(VAZIO);
    qc.invalidateQueries({ queryKey: ["clientes"] });
    qc.invalidateQueries({ queryKey: ["ensaios"] });
  }

  const editando = novo || sel != null;

  return (
    <div className="h-full flex overflow-hidden">
      {/* Lista */}
      <div className="w-72 flex-shrink-0 border-r border-border flex flex-col">
        <div className="p-4 border-b border-border space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold text-white flex items-center gap-2"><Users size={18} className="text-accent" /> Clientes</h1>
            <button
              onClick={() => { setNovo(true); setSelId(null); setForm(VAZIO); setMsg(null); }}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-accent text-bg text-xs font-semibold"
            >
              <Plus size={13} /> Novo
            </button>
          </div>
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Filtrar clientes"
              className={clsx(inputCls, "pl-8 text-xs")} />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoading && <p className="text-xs text-muted text-center mt-6">Carregando…</p>}
          {!isLoading && lista.length === 0 && (
            <p className="text-xs text-muted text-center mt-6 px-4">Nenhum cliente. Clique em Novo para cadastrar.</p>
          )}
          {lista.map((c) => (
            <button key={c.id}
              onClick={() => { setSelId(c.id); setNovo(false); setMsg(null); }}
              className={clsx(
                "w-full text-left rounded-lg border px-3 py-2 transition-colors",
                c.id === selId ? "border-accent/50 bg-accent/10" : "border-transparent hover:border-border hover:bg-border/30",
              )}>
              <p className="text-sm font-medium text-white truncate">{c.nome}</p>
              <p className="text-[11px] text-muted">
                {c.num_ensaios} teste(s) · {c.num_relatorios} relatório(s){c.cidade_uf ? ` · ${c.cidade_uf}` : ""}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Detalhe */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {!editando ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Users size={36} className="text-muted/30 mb-3" />
            <p className="text-sm text-muted">Selecione um cliente ou cadastre um novo.</p>
          </div>
        ) : (
          <>
            <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
              <p className="text-sm font-semibold text-white">{novo ? "Novo cliente" : "Dados do cliente"}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Campo label="Nome / Razão social *" value={form.nome} onChange={(v) => set("nome", v)} className="col-span-2" />
                <Campo label="CNPJ / CPF" value={form.documento} onChange={(v) => set("documento", v)} />
                <Campo label="Contato" value={form.contato} onChange={(v) => set("contato", v)} />
                <Campo label="E-mail" value={form.email} onChange={(v) => set("email", v)} />
                <Campo label="Telefone" value={form.telefone} onChange={(v) => set("telefone", v)} />
                <Campo label="Endereço" value={form.endereco} onChange={(v) => set("endereco", v)} className="col-span-2" />
                <Campo label="Bairro" value={form.bairro} onChange={(v) => set("bairro", v)} />
                <Campo label="Cidade/UF" value={form.cidade_uf} onChange={(v) => set("cidade_uf", v)} placeholder="ex: São Carlos/SP" />
                <Campo label="CEP" value={form.cep} onChange={(v) => set("cep", v)} />
                <Campo label="Observações" value={form.observacoes} onChange={(v) => set("observacoes", v)} className="col-span-2 md:col-span-3" />
              </div>
              <div className="flex items-center gap-3">
                <button onClick={salvar}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-bg text-sm font-semibold">
                  <Save size={14} /> Salvar
                </button>
                {sel && !novo && (
                  <button onClick={apagar}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-sm text-muted hover:text-red-400 hover:border-red-400/50">
                    <Trash2 size={14} /> Apagar
                  </button>
                )}
                {msg && <p className={clsx("text-xs", msg.ok ? "text-emerald-400" : "text-red-400")}>{msg.texto}</p>}
              </div>
            </div>

            {sel && !novo && (
              <>
                <div className="bg-surface border border-border rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-semibold text-white">Testes do cliente</p>
                    {(ensaios?.length ?? 0) > 1 && (
                      <button onClick={() => onCompare(ensaios!.map((e) => e.id))}
                        className="flex items-center gap-1.5 text-xs text-accent hover:underline">
                        <GitCompare size={13} /> Comparar todos (média e desvio padrão)
                      </button>
                    )}
                  </div>
                  {!ensaios?.length ? (
                    <p className="text-xs text-muted">Nenhum teste deste cliente. Escolha o cliente no Controle antes de iniciar o ensaio, ou em "Dados do teste" no resultado.</p>
                  ) : (
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-muted border-b border-border">
                          <th className="py-1.5 font-medium">Ensaio</th>
                          <th className="py-1.5 font-medium">Amostra</th>
                          <th className="py-1.5 font-medium">Norma</th>
                          <th className="py-1.5 font-medium">Data</th>
                          <th className="py-1.5 font-medium text-right">Fmáx (kN)</th>
                          <th className="py-1.5 font-medium text-right">σmáx (MPa)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ensaios.map((e) => (
                          <tr key={e.id} onClick={() => onOpenEnsaio(e.id)}
                            className="border-t border-border/50 hover:bg-border/20 cursor-pointer">
                            <td className="py-1.5 text-white">{e.filename.replace(".csv", "")}</td>
                            <td className="py-1.5 text-slate-300">{e.amostra || "—"}</td>
                            <td className="py-1.5 text-slate-300">{e.norma || "—"}</td>
                            <td className="py-1.5 text-slate-300">{e.data_ensaio}</td>
                            <td className="py-1.5 text-right font-mono text-slate-300">{((e.forca_max_N ?? 0) / 1000).toFixed(2)}</td>
                            <td className="py-1.5 text-right font-mono text-slate-300">{(e.tensao_max_MPa ?? 0).toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div className="bg-surface border border-border rounded-xl p-5">
                  <p className="text-sm font-semibold text-white mb-3">Relatórios do cliente</p>
                  {!relatorios?.length ? (
                    <p className="text-xs text-muted">Nenhum relatório salvo para este cliente.</p>
                  ) : (
                    <div className="space-y-1">
                      {relatorios.map((r) => (
                        <a key={r.id} href={relatorioUrl(r.id)} target="_blank" rel="noreferrer"
                          className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-border/30 text-xs">
                          <span className="text-white font-medium">{r.numero ? `Nº ${r.numero}` : `#${r.id}`}</span>
                          <span className="text-muted truncate flex-1">{r.titulo}</span>
                          <span className="text-muted">{dataUTC(r.created_at).toLocaleDateString("pt-BR")}</span>
                          <ExternalLink size={12} className="text-muted" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
