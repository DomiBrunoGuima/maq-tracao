import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Sidebar from "./components/Sidebar/Sidebar";
import Dashboard from "./components/Dashboard/Dashboard";
import ComparisonView from "./components/Comparison/ComparisonView";
import ConfigPanel from "./components/Config/ConfigPanel";
import ControlPanel from "./components/Control/ControlPanel";
import FlexaoView from "./components/Flexao/FlexaoView";
import ClientesView from "./components/Cadastro/ClientesView";
import RelatoriosView from "./components/Cadastro/RelatoriosView";
import UsuariosView from "./components/Usuarios/UsuariosView";
import LoginScreen, { TrocaObrigatoria } from "./components/Auth/LoginScreen";
import { useConfig } from "./hooks/useConfig";
import { AuthContext, useAuth } from "./hooks/useAuth";
import { EVENTO_SESSAO, getUsuarioLogado, logout, logoutConfig } from "./api/client";
import type { UsuarioLogado } from "./types";

type View = "dashboard" | "comparison" | "config" | "control" | "flexao" | "clientes" | "relatorios" | "usuarios";

/** Porta de entrada: sem sessão mostra o login; com senha provisória, a troca de senha. */
export default function App() {
  const qc = useQueryClient();
  // undefined = verificando a sessão; null = deslogado
  const [usuario, setUsuario] = useState<UsuarioLogado | null | undefined>(undefined);
  const [aviso, setAviso] = useState<string | undefined>();

  useEffect(() => {
    getUsuarioLogado().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  const encerrar = useCallback((msg?: string) => {
    setAviso(msg);
    setUsuario(null);
    qc.clear();
  }, [qc]);

  useEffect(() => {
    const h = () => encerrar("Sua sessão expirou. Entre de novo.");
    window.addEventListener(EVENTO_SESSAO, h);
    return () => window.removeEventListener(EVENTO_SESSAO, h);
  }, [encerrar]);

  const sair = useCallback(() => {
    logoutConfig();
    logout().finally(() => encerrar());
  }, [encerrar]);

  if (usuario === undefined) return <div className="h-screen bg-bg" />;
  if (usuario === null) return <LoginScreen aviso={aviso} onEntrar={(u) => { setAviso(undefined); qc.clear(); setUsuario(u); }} />;
  if (usuario.trocar_senha) {
    return <TrocaObrigatoria onSair={sair} onPronto={() => setUsuario({ ...usuario, trocar_senha: false })} />;
  }
  return (
    <AuthContext.Provider value={{ usuario, sair }}>
      <AppPrincipal key={usuario.id} />
    </AuthContext.Provider>
  );
}

function AppPrincipal() {
  const { usuario } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [compareFlexaoIds, setCompareFlexaoIds] = useState<number[]>([]);
  // Aba aberta na Comparação quando há tração e flexão selecionadas
  const [compareModo, setCompareModo] = useState<"tracao" | "flexao">("tracao");
  const [view, setView] = useState<View>("dashboard");
  // Máquina sem flexão: a tela de flexão cai no controle de tração
  const flexaoOn = useConfig().data?.flexao_habilitada !== false;
  const [clienteId, setClienteId] = useState<number | null>(null);
  const [flexaoId, setFlexaoId] = useState<number | null>(null);

  function handleSelectEnsaio(id: number) {
    setSelectedId(id);
    setView("dashboard");
  }

  function handleToggleCompare(id: number) {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  function handleToggleCompareFlexao(id: number) {
    setCompareFlexaoIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-slate-200">
      <Sidebar
        selectedId={selectedId}
        compareIds={compareIds}
        onSelect={handleSelectEnsaio}
        onToggleCompare={handleToggleCompare}
        compareFlexaoIds={compareFlexaoIds}
        onToggleCompareFlexao={handleToggleCompareFlexao}
        onSetCompareFlexao={(ids) => { setCompareFlexaoIds(ids); setCompareModo("flexao"); setView("comparison"); }}
        onViewConfig={() => setView("config")}
        onViewComparison={() => setView("comparison")}
        onViewControl={() => setView("control")}
        onViewFlexao={() => { setFlexaoId(null); setView("flexao"); }}
        onViewClientes={() => { setClienteId(null); setView("clientes"); }}
        onViewRelatorios={() => setView("relatorios")}
        onViewUsuarios={() => setView("usuarios")}
        onOpenCliente={(id) => { setClienteId(id); setView("clientes"); }}
        onOpenFlexao={(id) => { setFlexaoId(id); setView("flexao"); }}
        onSetCompare={(ids) => { setCompareIds(ids); setCompareModo("tracao"); setView("comparison"); }}
        currentView={view}
      />

      <main className="flex-1 min-h-0 overflow-hidden">
        {view === "dashboard" && (
          <Dashboard ensaioId={selectedId} />
        )}
        {view === "comparison" && (
          <ComparisonView key={compareModo} modoInicial={compareModo} ids={compareIds} onRemove={handleToggleCompare}
            flexaoIds={flexaoOn ? compareFlexaoIds : []} onRemoveFlexao={handleToggleCompareFlexao} />
        )}
        {view === "config" && (
          <ConfigPanel onClose={() => setView("dashboard")} />
        )}
        {(view === "control" || (view === "flexao" && !flexaoOn)) && (
          <ControlPanel onOpenEnsaio={handleSelectEnsaio} />
        )}
        {view === "flexao" && flexaoOn && (
          <FlexaoView key={flexaoId ?? "novo"} initialEnsaioId={flexaoId} />
        )}
        {view === "clientes" && (
          <ClientesView
            key={clienteId ?? "lista"}
            initialId={clienteId}
            onOpenEnsaio={handleSelectEnsaio}
            onCompare={(ids) => { setCompareIds(ids); setCompareModo("tracao"); setView("comparison"); }}
            onOpenFlexao={(id) => { setFlexaoId(id); setView("flexao"); }}
            onCompareFlexao={(ids) => { setCompareFlexaoIds(ids); setCompareModo("flexao"); setView("comparison"); }}
            flexaoOn={flexaoOn}
          />
        )}
        {view === "usuarios" && usuario.mestre && <UsuariosView />}
        {view === "relatorios" && (
          <RelatoriosView onOpenEnsaio={handleSelectEnsaio}
            onOpenFlexao={(id) => { setFlexaoId(id); setView("flexao"); }} />
        )}
      </main>
    </div>
  );
}
