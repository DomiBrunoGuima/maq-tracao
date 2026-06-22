import { useState } from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import Dashboard from "./components/Dashboard/Dashboard";
import ComparisonView from "./components/Comparison/ComparisonView";
import ConfigPanel from "./components/Config/ConfigPanel";
import ControlPanel from "./components/Control/ControlPanel";
import FlexaoView from "./components/Flexao/FlexaoView";

type View = "dashboard" | "comparison" | "config" | "control" | "flexao";

export default function App() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [view, setView] = useState<View>("dashboard");

  function handleSelectEnsaio(id: number) {
    setSelectedId(id);
    setView("dashboard");
  }

  function handleToggleCompare(id: number) {
    setCompareIds((prev) =>
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
        onViewConfig={() => setView("config")}
        onViewComparison={() => setView("comparison")}
        onViewControl={() => setView("control")}
        onViewFlexao={() => setView("flexao")}
        currentView={view}
      />

      <main className="flex-1 min-h-0 overflow-hidden">
        {view === "dashboard" && (
          <Dashboard ensaioId={selectedId} />
        )}
        {view === "comparison" && (
          <ComparisonView ids={compareIds} onRemove={handleToggleCompare} />
        )}
        {view === "config" && (
          <ConfigPanel onClose={() => setView("dashboard")} />
        )}
        {view === "control" && (
          <ControlPanel onOpenEnsaio={handleSelectEnsaio} />
        )}
        {view === "flexao" && (
          <FlexaoView />
        )}
      </main>
    </div>
  );
}
