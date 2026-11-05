import { useState } from "react";
import { Activity, Eye, EyeOff, KeyRound, Lock, LogIn, User } from "lucide-react";
import { login, trocarMinhaSenha } from "../../api/client";
import type { UsuarioLogado } from "../../types";

const inputCls =
  "w-full bg-bg border border-border rounded-lg pl-9 pr-3 py-2.5 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors placeholder:text-muted/50";

function erroDe(err: any, padrao: string): string {
  return err?.response?.data?.detail ?? padrao;
}

function Moldura({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-6">
          <Activity className="text-accent" size={28} />
          <div>
            <p className="font-semibold text-white leading-tight">Ensaios de Tração</p>
            <p className="text-xs text-muted">Sistema de ensaios mecânicos</p>
          </div>
        </div>
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl">{children}</div>
        <p className="text-center text-[11px] text-muted mt-4">
          Acesso restrito. Todas as ações ficam registradas com o seu usuário.
        </p>
      </div>
    </div>
  );
}

function CampoSenha({ value, onChange, placeholder, autoFocus }: {
  value: string; onChange: (v: string) => void; placeholder: string; autoFocus?: boolean;
}) {
  const [ver, setVer] = useState(false);
  return (
    <div className="relative">
      <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
      <input type={ver ? "text" : "password"} value={value} autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        autoComplete="current-password" className={inputCls + " pr-9"} />
      <button type="button" tabIndex={-1} onClick={() => setVer((v) => !v)}
        title={ver ? "Esconder senha" : "Mostrar senha"}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-white">
        {ver ? <EyeOff size={15} /> : <Eye size={15} />}
      </button>
    </div>
  );
}

export default function LoginScreen({ onEntrar, aviso }: { onEntrar: (u: UsuarioLogado) => void; aviso?: string }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true); setErro(null);
    try {
      onEntrar(await login(usuario.trim(), senha));
    } catch (err) {
      setErro(erroDe(err, "Não foi possível entrar. Verifique se o servidor está ligado."));
      setSenha("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Moldura>
      <form onSubmit={entrar} className="space-y-4">
        <div>
          <h1 className="text-lg font-semibold text-white">Entrar</h1>
          <p className="text-xs text-muted mt-0.5">Use o usuário e a senha fornecidos pelo administrador.</p>
        </div>
        {aviso && <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">{aviso}</p>}
        <div className="relative">
          <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoFocus
            autoComplete="username" autoCapitalize="none" spellCheck={false}
            placeholder="Usuário" className={inputCls} />
        </div>
        <CampoSenha value={senha} onChange={setSenha} placeholder="Senha" />
        {erro && <p className="text-xs text-red-400">{erro}</p>}
        <button type="submit" disabled={!usuario.trim() || !senha || enviando}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50">
          <LogIn size={16} />
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </Moldura>
  );
}

/** Formulário de troca da própria senha (tela cheia na senha provisória ou dentro de um modal). */
export function FormTrocarSenha({ obrigatoria, onPronto, onCancelar }: {
  obrigatoria?: boolean; onPronto: () => void; onCancelar?: () => void;
}) {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [conf, setConf] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (nova !== conf) { setErro("A confirmação não confere com a senha nova."); return; }
    setEnviando(true); setErro(null);
    try {
      await trocarMinhaSenha(atual, nova);
      onPronto();
    } catch (err) {
      setErro(erroDe(err, "Não foi possível trocar a senha."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-3">
      <div className="flex items-center gap-2">
        <KeyRound size={16} className="text-accent" />
        <h2 className="font-semibold text-white">{obrigatoria ? "Crie a sua senha" : "Trocar minha senha"}</h2>
      </div>
      {obrigatoria && (
        <p className="text-xs text-muted">
          A senha que você recebeu é provisória. Escolha uma senha pessoal para continuar.
        </p>
      )}
      <CampoSenha value={atual} onChange={setAtual} placeholder={obrigatoria ? "Senha provisória" : "Senha atual"} autoFocus />
      <CampoSenha value={nova} onChange={setNova} placeholder="Senha nova" />
      <CampoSenha value={conf} onChange={setConf} placeholder="Repita a senha nova" />
      <p className="text-[11px] text-muted">Mínimo de 8 caracteres, com letras e números.</p>
      {erro && <p className="text-xs text-red-400">{erro}</p>}
      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={!atual || !nova || !conf || enviando}
          className="flex-1 px-4 py-2 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50">
          {enviando ? "Salvando..." : "Salvar senha"}
        </button>
        {onCancelar && (
          <button type="button" onClick={onCancelar}
            className="px-4 py-2 rounded-lg border border-border text-sm text-muted hover:text-white transition-colors">
            {obrigatoria ? "Sair" : "Cancelar"}
          </button>
        )}
      </div>
    </form>
  );
}

export function TrocaObrigatoria({ onPronto, onSair }: { onPronto: () => void; onSair: () => void }) {
  return (
    <Moldura>
      <FormTrocarSenha obrigatoria onPronto={onPronto} onCancelar={onSair} />
    </Moldura>
  );
}
