import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CloudUpload, Loader2, XCircle } from "lucide-react";
import { clsx } from "clsx";
import { fazerBackupAgora, getBackupStatus } from "../../api/client";
import type { AppConfig } from "../../types";
import type { FormState } from "./ConfigPanel";

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors font-mono placeholder:text-muted/40";

const fmtData = (iso: string | null) => (iso ? new Date(iso).toLocaleString("pt-BR") : "—");

/** Backup automático: o programa grava um .zip numa pasta que o app da nuvem
 *  (Google Drive, OneDrive, Dropbox) já sincroniza. */
export default function BackupSection({
  form, setForm, salvo,
}: {
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
  salvo?: AppConfig;
}) {
  const { data: st, refetch } = useQuery({ queryKey: ["backup"], queryFn: getBackupStatus, refetchInterval: 15000 });
  const [rodando, setRodando] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);
  const pendente = salvo != null && (salvo.backup_dir ?? "") !== form.backup_dir;

  async function agora() {
    setRodando(true);
    setMsg(null);
    try {
      const r = await fazerBackupAgora();
      setMsg({ ok: true, texto: `Backup gravado: ${r.arquivo}` });
      refetch();
    } catch (e: any) {
      setMsg({ ok: false, texto: e?.response?.data?.detail ?? "Falha no backup." });
    } finally {
      setRodando(false);
    }
  }

  return (
    <div>
      <h2 className="text-base font-semibold text-white mb-1">Backup automático</h2>
      <p className="text-xs text-muted/70 mb-6 leading-relaxed">
        O programa copia os ensaios, clientes, relatórios e configurações para uma pasta do seu
        Google Drive, OneDrive ou Dropbox instalado neste PC. O app da nuvem envia a cópia sozinho,
        e sem internet ele envia quando a conexão voltar.
      </p>

      <div className="space-y-5">
        <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
          <div>
            <p className="text-sm text-white font-medium">Fazer backup automaticamente</p>
            <p className="text-xs text-muted/70 mt-0.5">Liga a cópia no intervalo escolhido abaixo.</p>
          </div>
          <button
            onClick={() => setForm((f) => ({ ...f, backup_ativo: !f.backup_ativo }))}
            className={clsx(
              "relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
              form.backup_ativo ? "bg-accent" : "bg-border",
            )}
          >
            <span className={clsx(
              "inline-block h-4 w-4 transform rounded-full bg-[#fff] shadow transition duration-200",
              form.backup_ativo ? "translate-x-4" : "translate-x-0",
            )} />
          </button>
        </div>

        <div>
          <span className="text-xs font-medium text-muted block mb-1.5">Pasta do backup</span>
          <input
            value={form.backup_dir}
            onChange={(e) => setForm((f) => ({ ...f, backup_dir: e.target.value }))}
            placeholder="ex: C:\Users\Bruno\Google Drive\Backup Tração"
            className={inputCls}
          />
          <p className="text-xs text-muted/60 mt-1.5">
            Escolha uma pasta dentro da pasta do Google Drive, OneDrive ou Dropbox. Se ela não existir, o programa cria.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-xs font-medium text-muted block mb-1.5">Intervalo (horas)</span>
            <input type="number" min={1} value={form.backup_intervalo_h}
              onChange={(e) => setForm((f) => ({ ...f, backup_intervalo_h: Number(e.target.value) }))}
              className={inputCls} />
          </div>
          <div>
            <span className="text-xs font-medium text-muted block mb-1.5">Manter os últimos</span>
            <input type="number" min={1} value={form.backup_manter}
              onChange={(e) => setForm((f) => ({ ...f, backup_manter: Number(e.target.value) }))}
              className={inputCls} />
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface px-4 py-3 space-y-1 text-xs">
          <p><span className="text-muted">Último backup: </span><span className="text-white font-mono">{fmtData(st?.ultimo ?? null)}</span></p>
          <p><span className="text-muted">Próximo: </span><span className="text-white font-mono">{st?.ativo ? fmtData(st?.proximo ?? null) : "desligado"}</span></p>
          {st?.erro && <p className="text-red-400">Último erro: {st.erro}</p>}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={agora} disabled={rodando || pendente || !form.backup_dir}
            title={pendente ? "Clique em Salvar e Aplicar antes" : undefined}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-accent/50 bg-accent/10 text-accent text-sm font-medium disabled:opacity-40">
            {rodando ? <Loader2 size={14} className="animate-spin" /> : <CloudUpload size={14} />}
            Fazer backup agora
          </button>
          {pendente && <span className="text-xs text-amber-300">Salve a pasta nova antes de testar.</span>}
          {msg && (
            <span className={clsx("flex items-center gap-1 text-xs", msg.ok ? "text-emerald-400" : "text-red-400")}>
              {msg.ok ? <CheckCircle2 size={13} /> : <XCircle size={13} />} {msg.texto}
            </span>
          )}
        </div>

        {st?.backups && st.backups.length > 0 && (
          <div>
            <p className="text-xs text-muted mb-1.5">Backups na pasta</p>
            <div className="rounded-lg border border-border divide-y divide-border/50">
              {st.backups.map((b) => (
                <div key={b.arquivo} className="flex items-center justify-between px-3 py-1.5 text-xs font-mono">
                  <span className="text-slate-300">{b.arquivo}</span>
                  <span className="text-muted">{b.tamanho_kb} KB</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted/60 mt-1.5">
              Para restaurar: feche o programa, descompacte o .zip e troque o tracao.db da instalação pelo do backup.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
