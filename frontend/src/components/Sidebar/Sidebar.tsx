import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpFromLine,
  ChevronRight,
  FileText,
  GitCompare,
  Moon,
  RotateCcw,
  Search,
  Settings,
  Sun,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { buscar, relatorioUrl } from "../../api/client";
import { useEnsaios, useDeleteEnsaio, useReimportAll } from "../../hooks/useEnsaios";
import { useEnsaiosFlexao, useDeleteEnsaioFlexao } from "../../hooks/useFlexao";
import { useTheme } from "../../hooks/useTheme";
import { useConfig } from "../../hooks/useConfig";
import type { EnsaioFlexaoSummary, EnsaioSummary, ResultadoBusca, TipoBusca } from "../../types";
import { ConexaoCLPIndicator } from "../Common/Status";

const FILTROS: { key: TipoBusca; label: string }[] = [
  { key: "todos", label: "Todos" },
  { key: "cliente", label: "Clientes" },
  { key: "teste", label: "Testes" },
  { key: "relatorio", label: "Relatórios" },
];

interface Props {
  selectedId: number | null;
  compareIds: number[];
  onSelect: (id: number) => void;
  onToggleCompare: (id: number) => void;
  onViewConfig: () => void;
  onViewComparison: () => void;
  onViewControl: () => void;
  onViewFlexao: () => void;
  onViewClientes: () => void;
  onViewRelatorios: () => void;
  onOpenCliente: (id: number) => void;
  onOpenFlexao: (id: number) => void;
  onSetCompare: (ids: number[]) => void;
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
  onViewClientes,
  onViewRelatorios,
  onOpenCliente,
  onOpenFlexao,
  onSetCompare,
  currentView,
}: Props) {
  const { data: ensaios, isLoading } = useEnsaios();
  const deleteMut = useDeleteEnsaio();
  const { data: flexoes } = useEnsaiosFlexao();
  const deleteFlexaoMut = useDeleteEnsaioFlexao();
  const { data: config } = useConfig();
  const flexaoOn = config?.flexao_habilitada !== false;
  // Lista única com tração e flexão, mais recentes primeiro
  const lista: ({ modo: "tracao"; e: EnsaioSummary } | { modo: "flexao"; e: EnsaioFlexaoSummary })[] = [
    ...(ensaios ?? []).map((e) => ({ modo: "tracao" as const, e })),
    ...(flexaoOn ? flexoes ?? [] : []).map((e) => ({ modo: "flexao" as const, e })),
  ].sort((a, b) => (b.e.created_at ?? "").localeCompare(a.e.created_at ?? ""));
  const reimportMut = useReimportAll();
  const { tema, alternar } = useTheme();

  // Busca: espera o operador parar de digitar antes de consultar
  const [texto, setTexto] = useState("");
  const [filtro, setFiltro] = useState<TipoBusca>("todos");
  const [q, setQ] = useState("");
  useEffect(() => {
    const id = setTimeout(() => setQ(texto.trim()), 250);
    return () => clearTimeout(id);
  }, [texto]);
  const buscando = q !== "" || filtro !== "todos";
  const { data: busca, isFetching } = useQuery({
    queryKey: ["busca", q, filtro],
    queryFn: () => buscar(q, filtro),
    enabled: buscando,
  });
  const resultados = (busca?.resultados ?? []).filter((r) => flexaoOn || r.modo !== "flexao");
  const testesTracao = resultados.filter((r) => r.tipo === "teste" && r.modo === "tracao");

  function abrirResultado(r: ResultadoBusca) {
    if (r.tipo === "cliente") onOpenCliente(r.id);
    else if (r.tipo === "relatorio") window.open(relatorioUrl(r.id), "_blank");
    else if (r.modo === "flexao") onOpenFlexao(r.id);
    else onSelect(r.id);
  }

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col border-r border-border bg-surface h-full">
      {/* Logo + tema */}
      <div className="p-4 border-b border-border space-y-3">
        <div className="flex items-center gap-2">
          <Activity className="text-accent" size={22} />
          <div className="flex-1">
            <p className="font-semibold text-sm text-white leading-tight">
              Ensaios de Tração
            </p>
            <p className="text-xs text-muted">Analisador Automático</p>
          </div>
          <button
            onClick={alternar}
            title={tema === "claro" ? "Mudar para fundo preto" : "Mudar para fundo branco"}
            className="p-2 rounded-lg border border-border text-muted hover:text-accent hover:border-accent transition-colors"
          >
            {tema === "claro" ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </div>
        <ConexaoCLPIndicator />
      </div>

      {/* Modos de ensaio — Tração e Flexão em destaque */}
      <div className={clsx("p-3 border-b border-border grid gap-2", flexaoOn ? "grid-cols-2" : "grid-cols-1")}>
        <ModoButton
          ativo={currentView === "control"} onClick={onViewControl}
          icon={<ArrowUpFromLine size={30} strokeWidth={2.4} />} label="TRAÇÃO"
          cor="sky"
        />
        {flexaoOn && (
          <ModoButton
            ativo={currentView === "flexao"} onClick={onViewFlexao}
            icon={<ArrowDownToLine size={30} strokeWidth={2.4} />} label="FLEXÃO"
            cor="violet"
          />
        )}
      </div>

      {/* Busca */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Buscar cliente, teste, relatório…"
            className="w-full bg-bg border border-border rounded-lg pl-8 pr-7 py-1.5 text-xs text-white
                       focus:outline-none focus:border-accent placeholder:text-muted/60"
          />
          {texto && (
            <button onClick={() => setTexto("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-white">
              <X size={12} />
            </button>
          )}
        </div>
        <div className="flex gap-1">
          {FILTROS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFiltro(f.key)}
              className={clsx(
                "flex-1 px-1 py-1 rounded text-[10px] font-medium transition-colors",
                filtro === f.key ? "bg-accent/15 text-accent" : "text-muted hover:text-white hover:bg-border/40",
              )}
            >
              {f.label}
            </button>
          ))}
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

      {/* Resultados da busca */}
      {buscando && (
        <div className="flex-1 overflow-y-auto py-2">
          <div className="px-4 pb-2 flex items-center justify-between">
            <p className="text-[10px] text-muted uppercase tracking-wider">
              {isFetching ? "Buscando…" : `${busca?.total ?? 0} resultado(s)`}
            </p>
            {testesTracao.length > 1 && (
              <button
                onClick={() => onSetCompare(testesTracao.map((r) => r.id))}
                className="text-[10px] text-accent hover:underline"
                title="Compara os testes encontrados e mostra média e desvio padrão"
              >
                Comparar {testesTracao.length} testes
              </button>
            )}
          </div>
          {busca && resultados.map((r) => (
            <button
              key={`${r.tipo}-${r.modo ?? ""}-${r.id}`}
              onClick={() => abrirResultado(r)}
              className="w-full text-left mx-2 mb-1 px-3 py-2 rounded-lg border border-transparent hover:border-border hover:bg-border/30 transition-colors"
              style={{ width: "calc(100% - 1rem)" }}
            >
              <div className="flex items-center gap-2">
                <TipoIcon r={r} />
                <p className="text-sm font-medium text-white truncate flex-1">{r.titulo}</p>
              </div>
              {r.subtitulo && <p className="text-[11px] text-muted truncate pl-5">{r.subtitulo}</p>}
            </button>
          ))}
          {!isFetching && busca && resultados.length === 0 && (
            <p className="text-xs text-muted text-center mt-6 px-4">Nada encontrado. Tente menos palavras.</p>
          )}
        </div>
      )}

      {/* Ensaio list */}
      <div className={clsx("flex-1 overflow-y-auto py-2", buscando && "hidden")}>
        {isLoading && (
          <p className="text-xs text-muted text-center mt-8">Carregando...</p>
        )}
        {!isLoading && lista.length === 0 && (
          <div className="text-center mt-8 px-4">
            <p className="text-xs text-muted">Nenhum ensaio carregado.</p>
            <p className="text-xs text-muted mt-1">
              Adicione arquivos CSV na pasta monitorada ou rode um ensaio pelo Controle da Máquina.
            </p>
          </div>
        )}
        {lista.map((item) => item.modo === "tracao" ? (
          <EnsaioItem
            key={`t-${item.e.id}`}
            ensaio={item.e}
            selected={selectedId === item.e.id}
            inCompare={compareIds.includes(item.e.id)}
            onSelect={() => onSelect(item.e.id)}
            onToggleCompare={() => onToggleCompare(item.e.id)}
            onDelete={() => deleteMut.mutate(item.e.id)}
          />
        ) : (
          <FlexaoItem
            key={`f-${item.e.id}`}
            ensaio={item.e}
            onSelect={() => onOpenFlexao(item.e.id)}
            onDelete={() => deleteFlexaoMut.mutate(item.e.id)}
          />
        ))}
      </div>

      {/* Bottom nav */}
      <div className="p-3 border-t border-border space-y-1">
        <NavButton ativo={currentView === "clientes"} onClick={onViewClientes} icon={<Users size={15} />} label="Clientes" />
        <NavButton ativo={currentView === "relatorios"} onClick={onViewRelatorios} icon={<FileText size={15} />} label="Relatórios" />
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

function ModoButton({
  ativo, onClick, icon, label, cor,
}: {
  ativo: boolean; onClick: () => void; icon: React.ReactNode; label: string; cor: "sky" | "violet";
}) {
  const cores = cor === "sky"
    ? { on: "border-sky-400 bg-sky-500/20 text-sky-300 shadow-[0_0_18px_rgba(56,189,248,0.25)]", off: "hover:border-sky-400/60 hover:text-sky-300" }
    : { on: "border-violet-400 bg-violet-500/20 text-violet-300 shadow-[0_0_18px_rgba(167,139,250,0.25)]", off: "hover:border-violet-400/60 hover:text-violet-300" };
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex flex-col items-center justify-center gap-1.5 px-2 py-4 rounded-xl border-2 text-sm font-bold tracking-wider transition-all",
        ativo ? cores.on : clsx("border-border bg-bg text-slate-300", cores.off),
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function NavButton({
  ativo, onClick, icon, label,
}: {
  ativo: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors",
        ativo ? "bg-border text-white" : "text-muted hover:text-white hover:bg-border",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function TipoIcon({ r }: { r: ResultadoBusca }) {
  if (r.tipo === "cliente") return <Users size={12} className="text-emerald-400 flex-shrink-0" />;
  if (r.tipo === "relatorio") return <FileText size={12} className="text-amber-400 flex-shrink-0" />;
  return r.modo === "flexao"
    ? <ArrowDownToLine size={12} className="text-violet-300 flex-shrink-0" />
    : <ArrowUpFromLine size={12} className="text-sky-400 flex-shrink-0" />;
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
          <p className="text-xs text-muted truncate">
            {ensaio.data_ensaio}
            {ensaio.cliente_nome ? ` · ${ensaio.cliente_nome}` : ""}
            {ensaio.amostra ? ` · ${ensaio.amostra}` : ""}
          </p>
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

function FlexaoItem({
  ensaio, onSelect, onDelete,
}: {
  ensaio: EnsaioFlexaoSummary; onSelect: () => void; onDelete: () => void;
}) {
  return (
    <div className="group mx-2 mb-1 rounded-lg border border-transparent hover:border-border hover:bg-border/30 transition-all cursor-pointer">
      <div className="flex items-start gap-2 p-3" onClick={onSelect}>
        <ChevronRight size={14} className="mt-0.5 flex-shrink-0 text-muted" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium text-white truncate">{ensaio.filename.replace(".csv", "")}</p>
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 flex-shrink-0">FLEXÃO</span>
          </div>
          <p className="text-xs text-muted truncate">{ensaio.data_ensaio}</p>
          <div className="flex gap-3 mt-1.5">
            <Stat label="Fmax" value={`${((ensaio.forca_max_N ?? 0) / 1000).toFixed(2)} kN`} />
            <Stat label="σfM" value={`${(ensaio.tensao_flexao_max_MPa ?? 0).toFixed(1)} MPa`} />
          </div>
        </div>
      </div>
      <div className="flex justify-end border-t border-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
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
