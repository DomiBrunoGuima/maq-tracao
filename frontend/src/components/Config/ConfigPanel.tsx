import { useState, useEffect } from "react";
import { Save, X, FolderOpen } from "lucide-react";
import { useConfig, useUpdateConfig } from "../../hooks/useConfig";
import { useScan } from "../../hooks/useEnsaios";

interface Props {
  onClose: () => void;
}

export default function ConfigPanel({ onClose }: Props) {
  const { data: config, isLoading } = useConfig();
  const updateMut = useUpdateConfig();
  const scanMut = useScan();

  const [form, setForm] = useState({
    watch_directory: "",
    auto_load: true,
    refresh_interval_s: 5,
    ihm_ip: "",
    ihm_port: 502,
    ihm_timeout: 3,
    ihm_registers: [] as any[],
  });

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  function handleSave() {
    updateMut.mutate(form, { onSuccess: () => scanMut.mutate() });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted text-sm">Carregando configurações...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-white">Configurações</h1>
        <button onClick={onClose} className="text-muted hover:text-white transition-colors">
          <X size={18} />
        </button>
      </div>

      <div className="space-y-6">
        {/* Watch directory */}
        <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Diretório Monitorado</h2>
          <div>
            <label className="text-xs text-muted block mb-1.5">
              Caminho do diretório com arquivos CSV da IHM
            </label>
            <div className="flex gap-2">
              <input
                value={form.watch_directory}
                onChange={(e) =>
                  setForm((f) => ({ ...f, watch_directory: e.target.value }))
                }
                placeholder="ex: C:\IHM_Exports\"
                className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm
                           text-white focus:outline-none focus:border-accent transition-colors font-mono"
              />
            </div>
            <p className="text-xs text-muted mt-1.5">
              O software monitora automaticamente este diretório por arquivos{" "}
              <code className="text-accent">.csv</code> no formato HISTORY V1.0.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_load"
              checked={form.auto_load}
              onChange={(e) =>
                setForm((f) => ({ ...f, auto_load: e.target.checked }))
              }
              className="w-4 h-4 rounded accent-accent"
            />
            <label htmlFor="auto_load" className="text-sm text-slate-300 cursor-pointer">
              Monitoramento automático ativo
            </label>
          </div>

          <div>
            <label className="text-xs text-muted block mb-1.5">
              Intervalo de verificação (s)
            </label>
            <input
              type="number"
              min={1}
              max={60}
              value={form.refresh_interval_s}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  refresh_interval_s: Number(e.target.value),
                }))
              }
              className="w-24 bg-bg border border-border rounded-lg px-3 py-2 text-sm
                         text-white focus:outline-none focus:border-accent transition-colors font-mono"
            />
          </div>
        </div>

        {/* IHM Modbus */}
        <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">IHM — Modbus TCP</h2>
          <p className="text-xs text-muted">
            Parâmetros capturados automaticamente via Modbus quando um ensaio é detectado.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted block mb-1.5">IP da IHM</label>
              <input
                value={form.ihm_ip}
                onChange={(e) => setForm((f) => ({ ...f, ihm_ip: e.target.value }))}
                placeholder="192.168.1.100"
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm
                           text-white focus:outline-none focus:border-accent transition-colors font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1.5">Porta</label>
              <input
                type="number"
                value={form.ihm_port}
                onChange={(e) => setForm((f) => ({ ...f, ihm_port: Number(e.target.value) }))}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm
                           text-white focus:outline-none focus:border-accent transition-colors font-mono"
              />
            </div>
          </div>

          {/* Registradores configurados (somente leitura) */}
          {form.ihm_registers.length > 0 && (
            <div>
              <p className="text-xs text-muted mb-2">Registradores configurados</p>
              <div className="space-y-1">
                {form.ihm_registers.map((r: any) => (
                  <div key={r.name} className="flex items-center gap-3 text-xs font-mono text-slate-400">
                    <span className="text-accent w-16">{r.address}</span>
                    <span>{r.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-white mb-3">Sobre</h2>
          <dl className="grid grid-cols-2 gap-2 text-xs">
            {[
              ["Software", "Analisador de Ensaios de Tração"],
              ["Versão", "1.0.0"],
              ["Banco de dados", "SQLite (tracao.db)"],
              ["Formato suportado", "HISTORY V1.0 (UTF-16, TAB)"],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-muted">{k}</dt>
                <dd className="text-slate-300 font-mono">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Save */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={updateMut.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent text-bg rounded-lg
                       font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            <Save size={15} />
            {updateMut.isPending ? "Salvando..." : "Salvar e Aplicar"}
          </button>
          {updateMut.isSuccess && (
            <span className="text-sm text-green-400">Configurações salvas!</span>
          )}
        </div>
      </div>
    </div>
  );
}
