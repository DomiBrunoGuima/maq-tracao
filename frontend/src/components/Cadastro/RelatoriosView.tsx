import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, FileText, Search, Trash2 } from "lucide-react";
import { deleteRelatorio, relatorioUrl } from "../../api/client";
import { useRelatorios } from "../../hooks/useEnsaios";
import { dataUTC } from "../../utils/data";

function semAcento(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export default function RelatoriosView({ onOpenEnsaio, onOpenFlexao }: {
  onOpenEnsaio: (id: number) => void;
  onOpenFlexao: (id: number) => void;
}) {
  const qc = useQueryClient();
  const { data: relatorios, isLoading } = useRelatorios();
  const [filtro, setFiltro] = useState("");

  const lista = useMemo(() => {
    const termos = semAcento(filtro.trim()).split(/\s+/).filter(Boolean);
    return (relatorios ?? []).filter((r) => {
      const alvo = semAcento(`${r.numero} ${r.titulo} ${r.cliente_nome} ${dataUTC(r.created_at).toLocaleDateString("pt-BR")}`);
      return termos.every((t) => alvo.includes(t));
    });
  }, [relatorios, filtro]);

  async function apagar(id: number) {
    if (!window.confirm("Apagar este relatório salvo? O ensaio continua gravado.")) return;
    await deleteRelatorio(id);
    qc.invalidateQueries({ queryKey: ["relatorios"] });
    qc.invalidateQueries({ queryKey: ["clientes"] });
  }

  return (
    <div className="p-6 space-y-5 overflow-y-auto h-full">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white flex items-center gap-2"><FileText size={18} className="text-accent" /> Relatórios salvos</h1>
          <p className="text-xs text-muted mt-0.5">Todo relatório gerado fica guardado aqui para abrir ou baixar de novo.</p>
        </div>
        <div className="relative w-72">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Filtrar por número, cliente, ensaio, data"
            className="w-full bg-bg border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-accent placeholder:text-muted/60" />
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        {isLoading ? (
          <p className="text-sm text-muted p-6">Carregando…</p>
        ) : lista.length === 0 ? (
          <p className="text-sm text-muted p-6">
            {relatorios?.length ? "Nenhum relatório com esse filtro." : "Nenhum relatório gerado ainda. Abra um ensaio e clique em Gerar Relatório."}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted border-b border-border">
                <th className="px-4 py-2 font-medium">Número</th>
                <th className="px-4 py-2 font-medium">Cliente</th>
                <th className="px-4 py-2 font-medium">Ensaio</th>
                <th className="px-4 py-2 font-medium">Gerado em</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {lista.map((r) => (
                <tr key={r.id} className="border-t border-border/50 hover:bg-border/20">
                  <td className="px-4 py-2 font-mono text-white">{r.numero || `#${r.id}`}</td>
                  <td className="px-4 py-2 text-slate-300">{r.cliente_nome || "—"}</td>
                  <td className="px-4 py-2">
                    {r.ensaio_id != null && r.ensaio_id > 0 ? (
                      <button onClick={() => (r.tipo === "flexao" ? onOpenFlexao : onOpenEnsaio)(r.ensaio_id!)}
                        className="text-accent hover:underline text-left">
                        {r.titulo || `Ensaio #${r.ensaio_id}`}{r.tipo === "flexao" ? " · flexão" : ""}
                      </button>
                    ) : (
                      <span className="text-muted">{r.titulo || "—"}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-300">{dataUTC(r.created_at).toLocaleString("pt-BR")}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-3 text-muted">
                      <a href={relatorioUrl(r.id)} target="_blank" rel="noreferrer" title="Abrir" className="hover:text-accent"><ExternalLink size={14} /></a>
                      <a href={relatorioUrl(r.id, true)} title="Baixar" className="hover:text-accent"><Download size={14} /></a>
                      <button onClick={() => apagar(r.id)} title="Apagar" className="hover:text-red-400"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
