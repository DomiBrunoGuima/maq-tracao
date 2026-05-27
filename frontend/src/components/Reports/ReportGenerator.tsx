import { useState } from "react";
import { X, FileText, Loader2 } from "lucide-react";
import { generateReport } from "../../api/client";
import type { ReportRequest } from "../../types";

interface Props {
  ensaioId: number;
  onClose: () => void;
}

export default function ReportGenerator({ ensaioId, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<Omit<ReportRequest, "ensaio_id">>({
    include_metadata: true,
    include_kpis: true,
    include_stress_strain: true,
    include_force_displacement: true,
    include_force_time: true,
    include_raw_data: false,
    include_derived_data: true,
    observations: "",
    operator_name: "",
    specimen_id: "",
    standard: "",
    format: "html",
  });

  async function handleGenerate() {
    setLoading(true);
    try {
      await generateReport({ ...form, ensaio_id: ensaioId });
    } finally {
      setLoading(false);
    }
  }

  function toggle(key: keyof typeof form) {
    setForm((f) => ({ ...f, [key]: !f[key] }));
  }

  const Check = ({ label, k }: { label: string; k: keyof typeof form }) => (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={!!form[k]}
        onChange={() => toggle(k)}
        className="w-4 h-4 rounded accent-accent"
      />
      <span className="text-sm text-slate-300">{label}</span>
    </label>
  );

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-2">
            <FileText className="text-accent" size={18} />
            <h2 className="font-semibold text-white">Gerar Relatório</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Identification */}
          <section>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
              Identificação
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Operador", "operator_name"],
                ["Corpo de Prova / Material", "specimen_id"],
              ].map(([label, key]) => (
                <label key={key} className="flex flex-col gap-1">
                  <span className="text-xs text-muted">{label}</span>
                  <input
                    value={form[key as keyof typeof form] as string}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm
                               text-white focus:outline-none focus:border-accent transition-colors"
                  />
                </label>
              ))}
              <label className="col-span-2 flex flex-col gap-1">
                <span className="text-xs text-muted">Norma Aplicada</span>
                <input
                  value={form.standard}
                  onChange={(e) => setForm((f) => ({ ...f, standard: e.target.value }))}
                  placeholder="ex: ASTM E8, NBR 6152"
                  className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm
                             text-white focus:outline-none focus:border-accent transition-colors"
                />
              </label>
            </div>
          </section>

          {/* Sections */}
          <section>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
              Seções do Relatório
            </h3>
            <div className="space-y-2.5">
              <Check label="Metadados do ensaio" k="include_metadata" />
              <Check label="Tabela de KPIs" k="include_kpis" />
              <Check label="Dados derivados calculados" k="include_derived_data" />
              <Check label="Tabela de dados brutos (todos os pontos)" k="include_raw_data" />
            </div>
          </section>

          {/* Observations */}
          <section>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
              Observações
            </h3>
            <textarea
              value={form.observations}
              onChange={(e) => setForm((f) => ({ ...f, observations: e.target.value }))}
              rows={3}
              placeholder="Anotações livres sobre o ensaio..."
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm
                         text-white focus:outline-none focus:border-accent transition-colors resize-none"
            />
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-muted hover:text-white transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 bg-accent text-bg rounded-lg
                       text-sm font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Gerando...
              </>
            ) : (
              <>
                <FileText size={14} />
                Gerar HTML
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
