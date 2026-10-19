import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { clsx } from "clsx";
import type { Qualidade, StatusQualidade } from "../../types";

const ICONE: Record<StatusQualidade, React.ReactNode> = {
  ok: <CheckCircle2 size={13} className="text-emerald-400" />,
  aviso: <AlertTriangle size={13} className="text-amber-400" />,
  erro: <XCircle size={13} className="text-red-400" />,
  info: <Info size={13} className="text-sky-400" />,
};

const RESUMO: Record<StatusQualidade, { texto: string; cls: string }> = {
  ok: { texto: "Dados confiáveis", cls: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30" },
  aviso: { texto: "Conferir avisos", cls: "text-amber-300 bg-amber-500/10 border-amber-500/30" },
  erro: { texto: "Resultado não confiável", cls: "text-red-300 bg-red-500/10 border-red-500/30" },
  info: { texto: "Informativo", cls: "text-sky-300 bg-sky-500/10 border-sky-500/30" },
};

/** Status de qualidade dos dados: completos, curva válida, ruptura, alongamento, faltantes. */
export default function QualidadePanel({ qualidade }: { qualidade: Qualidade }) {
  const r = RESUMO[qualidade.status];
  return (
    <div className="rounded-xl border border-border bg-surface p-3 flex-shrink-0">
      <div className="flex items-center justify-between mb-2.5">
        <p className="text-[10px] font-semibold text-muted/50 uppercase tracking-widest">Qualidade dos dados</p>
        <span className={clsx("text-[10px] font-semibold px-2 py-0.5 rounded-full border", r.cls)}>{r.texto}</span>
      </div>
      <div className="space-y-1.5">
        {qualidade.itens.map((i) => (
          <div key={i.chave} className="flex items-start gap-2" title={i.detalhe}>
            <span className="mt-0.5 flex-shrink-0">{ICONE[i.status]}</span>
            <div className="min-w-0">
              <p className="text-xs font-medium text-white leading-tight">{i.titulo}</p>
              <p className="text-[10px] text-muted leading-snug">{i.detalhe}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
