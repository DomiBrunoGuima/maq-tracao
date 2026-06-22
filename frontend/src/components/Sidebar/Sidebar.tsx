import {
  Activity,
  ChevronRight,
  GitCompare,
  RotateCcw,
  Ruler,
  Settings,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { clsx } from "clsx";
import { useEnsaios, useDeleteEnsaio, useReimportAll } from "../../hooks/useEnsaios";
import type { EnsaioSummary } from "../../types";

interface Props {
  selectedId: number | null;
  compareIds: number[];
  onSelect: (id: number) => void;
  onToggleCompare: (id: number) => void;
  onViewConfig: () => void;
  onViewComparison: () => void;
  onViewControl: () => void;
  onViewFlexao: () => void;
  currentView: string;
}

export default function Sidebar({
  selectedId,
  compareIds,
  onSelect,
  onToggleCompare,
  onViewConfig,
  onViewComparison,
  onViewControl,
  onViewFlexao,
  currentView,
}: Props) {
  const { data: ensaios, isLoading } = useEnsaios();
  const deleteMut = useDeleteEnsaio();
  const reimportMut = useReimportAll();

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col border-r border-border bg-surface h-full">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Activity className="text-accent" size={22} />
          <div>
            <p className="font-semibold text-sm text-white leading-tight">
              Ensaios de Tração
            </p>
            <p className="text-xs text-muted">Analisador Automático</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-3 border-b border-border space-y-2">
        <button
          onClick={onViewComparison}
          title="Comparar ensaios selecionados"
          className={clsx(
            "w-full flex items-center justify-center gap-1.5 px-3 py-1.5",
            "rounded text-xs font-medium transition-colors",
            currentView === "comparison"
              ? "bg-accent text-bg"
              : "bg-accent/10 hover:bg-accent/20 text-accent"
          )}
        >
          <GitCompare size={13} />
          Comparar {compareIds.length > 0 && `(${compareIds.length})`}
        </button>
        <button
          onClick={() => reimportMut.mutate()}
          disabled={reimportMut.isPending}
          title="Reprocessa todos os ensaios com o parser atual (aplica trim de pré-contato, etc.)"
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium
                     bg-border/40 hover:bg-border text-muted hover:text-white transition-colors disabled:opacity-50"
        >
          <RotateCcw size={12} className={reimportMut.isPending ? "animate-spin" : ""} />
          {reimportMut.isPending
            ? "Reimportando..."
            : reimportMut.isSuccess
            ? `✓ ${(reimportMut.data as any)?.reimported ?? 0} reimportados`
            : "Reimportar todos"}
        </button>
      </div>

      {/* Ensaio list */}
      <div className="flex-1 overflow-y-auto py-2">
        {isLoading && (
          <p className="text-xs text-muted text-center mt-8">Carregando...</p>
        )}
        {!isLoading && (!ensaios || ensaios.length === 0) && (
          <div className="text-center mt-8 px-4">
            <p className="text-xs text-muted">Nenhum ensaio carregado.</p>
            <p className="text-xs text-muted mt-1">
              Adicione arquivos CSV na pasta monitorada ou rode um ensaio pelo Controle da Máquina.
            </p>
          </div>
        )}
        {ensaios?.map((e) => (
          <EnsaioItem
            key={e.id}
            ensaio={e}
            selected={selectedId === e.id}
            inCompare={compareIds.includes(e.id)}
            onSelect={() => onSelect(e.id)}
            onToggleCompare={() => onToggleCompare(e.id)}
            onDelete={() => deleteMut.mutate(e.id)}
          />
        ))}
      </div>

      {/* Bottom nav — Tração e Flexão como ensaios de igual importância */}
      <div className="p-3 border-t border-border space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onViewControl}
            className={clsx(
              "flex flex-col items-center justify-center gap-1 px-2 py-3 rounded-lg border text-xs font-semibold transition-colors",
              currentView === "control"
                ? "border-accent bg-accent/10 text-accent"
                : "border-border bg-bg text-muted hover:text-white hover:border-accent/50"
            )}
          >
            <SlidersHorizontal size={18} />
            Tração
          </button>
          <button
            onClick={onViewFlexao}
            className={clsx(
              "flex flex-col items-center justify-center gap-1 px-2 py-3 rounded-lg border text-xs font-semibold transition-colors",
              currentView === "flexao"
                ? "border-accent bg-accent/10 text-accent"
                : "border-border bg-bg text-muted hover:text-white hover:border-accent/50"
            )}
          >
            <Ruler size={18} />
            Flexão
          </button>
        </div>
        <button
          onClick={onViewConfig}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors",
            currentView === "config"
              ? "bg-border text-white"
              : "text-muted hover:text-white hover:bg-border"
          )}
        >
          <Settings size={15} />
          Configurações
        </button>
      </div>
    </aside>
  );
}

function EnsaioItem({
  ensaio,
  selected,
  inCompare,
  onSelect,
  onToggleCompare,
  onDelete,
}: {
  ensaio: EnsaioSummary;
  selected: boolean;
  inCompare: boolean;
  onSelect: () => void;
  onToggleCompare: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={clsx(
        "group mx-2 mb-1 rounded-lg border transition-all cursor-pointer",
        selected
          ? "border-accent/50 bg-accent/10"
          : "border-transparent hover:border-border hover:bg-border/30"
      )}
    >
      <div className="flex items-start gap-2 p-3" onClick={onSelect}>
        <ChevronRight
          size={14}
          className={clsx(
            "mt-0.5 flex-shrink-0 transition-transform text-muted",
            selected && "rotate-90 text-accent"
          )}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{ensaio.filename.replace(".csv", "")}</p>
          <p className="text-xs text-muted">{ensaio.data_ensaio}</p>
          <div className="flex gap-3 mt-1.5">
            <Stat label="Fmax" value={`${((ensaio.forca_max_N ?? 0) / 1000).toFixed(2)} kN`} />
            <Stat label="σmax" value={`${(ensaio.tensao_max_MPa ?? 0).toFixed(1)} MPa`} />
          </div>
        </div>
      </div>
      <div className="flex border-t border-border/50 divide-x divide-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => { e.stopPropagation(); onToggleCompare(); }}
          className={clsx(
            "flex-1 py-1.5 text-xs transition-colors",
            inCompare
              ? "text-accent bg-accent/10"
              : "text-muted hover:text-accent"
          )}
        >
          {inCompare ? "✓ Comparar" : "+ Comparar"}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="px-3 py-1.5 text-xs text-muted hover:text-red-400 transition-colors"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="text-xs">
      <span className="text-muted">{label} </span>
      <span className="font-mono text-slate-300">{value}</span>
    </span>
  );
}
