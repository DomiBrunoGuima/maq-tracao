import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import {
  Check, Copy, History, KeyRound, Pencil, Plus, ShieldCheck, Trash2, UserCheck, UserCog, UserX, X,
} from "lucide-react";
import {
  criarUsuario, editarUsuario, excluirUsuario, getAuditoria, getUsuarios, redefinirSenha,
} from "../../api/client";
import type { Usuario, UsuarioIn } from "../../types";

const inputCls =
  "w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white " +
  "focus:outline-none focus:border-accent transition-colors placeholder:text-muted/40";

const VAZIO: UsuarioIn = { login: "", nome: "", cargo: "", registro: "", email: "", ativo: true };

const ACOES: Record<string, string> = {
  login: "Entrou no sistema",
  logout: "Saiu do sistema",
  login_falhou: "Tentativa de login recusada",
  senha_trocada: "Trocou a própria senha",
  senha_redefinida: "Senha redefinida",
  usuario_criado: "Usuário criado",
  usuario_editado: "Usuário alterado",
  usuario_excluido: "Usuário excluído",
  ensaio_iniciado: "Iniciou ensaio",
  ensaio_editado: "Editou dados do ensaio",
  ensaio_excluido: "Excluiu ensaio",
  relatorio_gerado: "Gerou relatório",
  relatorio_excluido: "Excluiu relatório",
  cliente_excluido: "Excluiu cliente",
  config_aberta: "Abriu as Configurações",
  config_senha_errada: "Senha das Configurações errada",
  config_alterada: "Alterou as Configurações",
  config_senha_trocada: "Trocou a senha das Configurações",
};

function erroDe(err: any, padrao: string): string {
  return err?.response?.data?.detail ?? padrao;
}

function dataHora(iso: string | null): string {
  if (!iso) return "—";
  // O servidor grava em UTC sem fuso: força a leitura como UTC.
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z");
  return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

/** Sugere um login "nome.sobrenome" sem acentos. */
function sugerirLogin(nome: string): string {
  const p = nome.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z\s]/g, "").trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "";
  return (p.length > 1 ? `${p[0]}.${p[p.length - 1]}` : p[0]).slice(0, 32);
}

export default function UsuariosView() {
  const [aba, setAba] = useState<"usuarios" | "auditoria">("usuarios");
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto p-6 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-white flex items-center gap-2">
              <UserCog size={20} className="text-accent" /> Usuários e acessos
            </h1>
            <p className="text-sm text-muted mt-1">
              Crie os acessos de quem opera a máquina. O nome, o cargo e o registro de cada
              usuário saem automaticamente nos relatórios que ele gerar.
            </p>
          </div>
          <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 flex-shrink-0">
            <ShieldCheck size={13} /> Acesso mestre
          </span>
        </div>
        <div className="flex gap-1 border-b border-border">
          {([["usuarios", "Usuários", UserCog], ["auditoria", "Registro de atividades", History]] as const).map(([id, label, Icon]) => (
            <button key={id} onClick={() => setAba(id)}
              className={clsx("flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 -mb-px transition-colors",
                aba === id ? "border-accent text-white" : "border-transparent text-muted hover:text-white")}>
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>
        {aba === "usuarios" ? <ListaUsuarios /> : <Auditoria />}
      </div>
    </div>
  );
}

function ListaUsuarios() {
  const qc = useQueryClient();
  const { data: lista, isLoading } = useQuery({ queryKey: ["usuarios"], queryFn: getUsuarios });
  const [editando, setEditando] = useState<Usuario | "novo" | null>(null);
  const [credencial, setCredencial] = useState<{ usuario: Usuario; senha: string; nova: boolean } | null>(null);
  const [resetando, setResetando] = useState<Usuario | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const atualizar = () => qc.invalidateQueries({ queryKey: ["usuarios"] });

  const alternarAtivo = useMutation({
    mutationFn: (u: Usuario) => editarUsuario(u.id, { ...u, ativo: !u.ativo }),
    onSuccess: atualizar,
    onError: (e) => setErro(erroDe(e, "Não foi possível alterar o usuário.")),
  });
  const excluir = useMutation({
    mutationFn: (u: Usuario) => excluirUsuario(u.id),
    onSuccess: atualizar,
    onError: (e) => setErro(erroDe(e, "Não foi possível excluir o usuário.")),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted">
          {lista ? `${lista.filter((u) => u.ativo).length} ativo(s) de ${lista.length}` : ""}
        </p>
        <button onClick={() => setEditando("novo")}
          className="flex items-center gap-1.5 px-3 py-2 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors">
          <Plus size={15} /> Novo usuário
        </button>
      </div>
      {erro && <p className="text-xs text-red-400">{erro}</p>}

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted border-b border-border">
              <th className="px-4 py-2.5 font-medium">Nome</th>
              <th className="px-4 py-2.5 font-medium">Login</th>
              <th className="px-4 py-2.5 font-medium">Cargo / registro</th>
              <th className="px-4 py-2.5 font-medium">Último acesso</th>
              <th className="px-4 py-2.5 font-medium">Situação</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="px-4 py-6 text-center text-muted text-xs">Carregando...</td></tr>}
            {lista?.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted text-sm">
                Nenhum usuário ainda. Clique em <b>Novo usuário</b> para criar o primeiro acesso.
              </td></tr>
            )}
            {lista?.map((u) => (
              <tr key={u.id} className={clsx("border-b border-border/50 last:border-0", !u.ativo && "opacity-50")}>
                <td className="px-4 py-2.5 text-white">{u.nome}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-300">{u.login}</td>
                <td className="px-4 py-2.5 text-xs text-slate-300">
                  {[u.cargo, u.registro].filter(Boolean).join(" · ") || <span className="text-muted">—</span>}
                </td>
                <td className="px-4 py-2.5 text-xs text-muted">{dataHora(u.ultimo_login)}</td>
                <td className="px-4 py-2.5 text-xs">
                  {!u.ativo ? <span className="text-muted">Desativado</span>
                    : u.trocar_senha ? <span className="text-amber-300">Senha provisória</span>
                    : <span className="text-emerald-300">Ativo</span>}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex justify-end gap-1">
                    <Acao title="Editar dados" onClick={() => setEditando(u)}><Pencil size={14} /></Acao>
                    <Acao title="Gerar nova senha" onClick={() => setResetando(u)}><KeyRound size={14} /></Acao>
                    <Acao title={u.ativo ? "Desativar acesso" : "Reativar acesso"} onClick={() => alternarAtivo.mutate(u)}>
                      {u.ativo ? <UserX size={14} /> : <UserCheck size={14} />}
                    </Acao>
                    <Acao title="Excluir usuário" perigo onClick={() => {
                      if (window.confirm(`Excluir o acesso de "${u.nome}"? Os ensaios e relatórios dele continuam com o nome gravado. Para só impedir o acesso, prefira desativar.`)) excluir.mutate(u);
                    }}><Trash2 size={14} /></Acao>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted">
        As senhas são guardadas criptografadas (hash) e não podem ser consultadas depois. Se alguém esquecer,
        gere uma nova senha. O acesso mestre é fixo e não aparece nesta lista.
      </p>

      {editando && (
        <FormUsuario
          inicial={editando === "novo" ? null : editando}
          onFechar={() => setEditando(null)}
          onSalvo={(r) => { setEditando(null); atualizar(); if (r) setCredencial({ ...r, nova: true }); }}
        />
      )}
      {resetando && (
        <ConfirmarReset usuario={resetando} onFechar={() => setResetando(null)}
          onPronto={(r) => { setResetando(null); atualizar(); setCredencial({ ...r, nova: false }); }} />
      )}
      {credencial && <Credencial {...credencial} onFechar={() => setCredencial(null)} />}
    </div>
  );
}

function Acao({ title, onClick, children, perigo }: { title: string; onClick: () => void; children: React.ReactNode; perigo?: boolean }) {
  return (
    <button title={title} onClick={onClick}
      className={clsx("p-1.5 rounded text-muted transition-colors", perigo ? "hover:text-red-400" : "hover:text-accent")}>
      {children}
    </button>
  );
}

function Modal({ titulo, onFechar, children }: { titulo: string; onFechar: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onFechar}>
      <div className="w-full max-w-md bg-surface border border-border rounded-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-white">{titulo}</h2>
          <button onClick={onFechar} className="text-muted hover:text-white"><X size={16} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function FormUsuario({ inicial, onFechar, onSalvo }: {
  inicial: Usuario | null;
  onFechar: () => void;
  onSalvo: (criado: { usuario: Usuario; senha: string } | null) => void;
}) {
  const [f, setF] = useState<UsuarioIn>(inicial ? { ...inicial } : VAZIO);
  const [loginManual, setLoginManual] = useState(!!inicial);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const set = (k: keyof UsuarioIn, v: string | boolean) => setF((x) => ({ ...x, [k]: v }));

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true); setErro(null);
    try {
      if (inicial) { await editarUsuario(inicial.id, f); onSalvo(null); }
      else onSalvo(await criarUsuario(f));
    } catch (err) {
      setErro(erroDe(err, "Não foi possível salvar."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={inicial ? "Editar usuário" : "Novo usuário"} onFechar={onFechar}>
      <form onSubmit={salvar} className="space-y-3">
        <Campo label="Nome completo *">
          <input autoFocus value={f.nome} className={inputCls} placeholder="ex.: Maria Souza"
            onChange={(e) => { set("nome", e.target.value); if (!loginManual) set("login", sugerirLogin(e.target.value)); }} />
        </Campo>
        <Campo label="Login (usuário para entrar) *">
          <input value={f.login} className={inputCls + " font-mono"} placeholder="ex.: maria.souza"
            autoCapitalize="none" spellCheck={false}
            onChange={(e) => { setLoginManual(true); set("login", e.target.value.toLowerCase()); }} />
        </Campo>
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Cargo / função">
            <input value={f.cargo} className={inputCls} placeholder="ex.: Técnico de laboratório"
              onChange={(e) => set("cargo", e.target.value)} />
          </Campo>
          <Campo label="Registro / matrícula">
            <input value={f.registro} className={inputCls} placeholder="ex.: CREA 12345"
              onChange={(e) => set("registro", e.target.value)} />
          </Campo>
        </div>
        <Campo label="E-mail">
          <input type="email" value={f.email} className={inputCls} placeholder="opcional"
            onChange={(e) => set("email", e.target.value)} />
        </Campo>
        {inicial && (
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={f.ativo} onChange={(e) => set("ativo", e.target.checked)} />
            Acesso ativo
          </label>
        )}
        <p className="text-[11px] text-muted">
          Nome, cargo e registro aparecem no relatório como responsável pela emissão.
          {!inicial && " A senha é gerada automaticamente ao salvar."}
        </p>
        {erro && <p className="text-xs text-red-400">{erro}</p>}
        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={!f.nome.trim() || !f.login.trim() || enviando}
            className="flex-1 px-4 py-2 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50">
            {enviando ? "Salvando..." : inicial ? "Salvar" : "Criar e gerar senha"}
          </button>
          <button type="button" onClick={onFechar}
            className="px-4 py-2 rounded-lg border border-border text-sm text-muted hover:text-white transition-colors">
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-muted block mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function ConfirmarReset({ usuario, onFechar, onPronto }: {
  usuario: Usuario; onFechar: () => void; onPronto: (r: { usuario: Usuario; senha: string }) => void;
}) {
  const [trocar, setTrocar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  async function gerar() {
    setEnviando(true); setErro(null);
    try { onPronto(await redefinirSenha(usuario.id, trocar)); }
    catch (err) { setErro(erroDe(err, "Não foi possível gerar a senha.")); }
    finally { setEnviando(false); }
  }
  return (
    <Modal titulo="Gerar nova senha" onFechar={onFechar}>
      <div className="space-y-3">
        <p className="text-sm text-slate-300">
          Gerar uma senha nova para <b className="text-white">{usuario.nome}</b> ({usuario.login})?
          A senha atual deixa de valer e a pessoa é desconectada.
        </p>
        <label className="flex items-start gap-2 text-sm text-slate-300">
          <input type="checkbox" className="mt-1" checked={trocar} onChange={(e) => setTrocar(e.target.checked)} />
          <span>Senha provisória: pedir para a pessoa criar a própria senha no próximo login</span>
        </label>
        {erro && <p className="text-xs text-red-400">{erro}</p>}
        <div className="flex gap-2 pt-1">
          <button onClick={gerar} disabled={enviando}
            className="flex-1 px-4 py-2 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50">
            {enviando ? "Gerando..." : "Gerar senha"}
          </button>
          <button onClick={onFechar}
            className="px-4 py-2 rounded-lg border border-border text-sm text-muted hover:text-white transition-colors">
            Cancelar
          </button>
        </div>
      </div>
    </Modal>
  );
}

/** Mostra a senha gerada uma única vez (no banco só fica o hash). */
function Credencial({ usuario, senha, nova, onFechar }: { usuario: Usuario; senha: string; nova: boolean; onFechar: () => void }) {
  const [copiado, setCopiado] = useState(false);
  const texto = `Usuário: ${usuario.login}\nSenha: ${senha}`;
  function copiar() {
    navigator.clipboard?.writeText(texto).then(() => { setCopiado(true); setTimeout(() => setCopiado(false), 2000); });
  }
  return (
    <Modal titulo={nova ? "Usuário criado" : "Senha nova gerada"} onFechar={onFechar}>
      <div className="space-y-4">
        <p className="text-sm text-slate-300">
          Entregue estes dados para <b className="text-white">{usuario.nome}</b>.
        </p>
        <div className="bg-bg border border-border rounded-lg p-4 font-mono text-sm space-y-1.5">
          <div><span className="text-muted">Usuário: </span><span className="text-white select-all">{usuario.login}</span></div>
          <div><span className="text-muted">Senha:&nbsp;&nbsp; </span><span className="text-accent text-base tracking-wider select-all">{senha}</span></div>
        </div>
        <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
          Anote agora: esta senha não será mostrada de novo. Se perder, gere outra.
          {usuario.trocar_senha && " No primeiro login a pessoa vai criar a própria senha."}
        </p>
        <div className="flex gap-2">
          <button onClick={copiar}
            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-border text-sm text-slate-300 hover:text-white hover:border-accent transition-colors">
            {copiado ? <><Check size={14} /> Copiado</> : <><Copy size={14} /> Copiar</>}
          </button>
          <button onClick={onFechar}
            className="flex-1 px-4 py-2 bg-accent text-bg rounded-lg font-semibold text-sm hover:bg-accent/90 transition-colors">
            Pronto
          </button>
        </div>
      </div>
    </Modal>
  );
}

function Auditoria() {
  const [usuario, setUsuario] = useState("");
  const [acao, setAcao] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["auditoria", usuario, acao],
    queryFn: () => getAuditoria({ usuario, acao, limite: 500 }),
    refetchInterval: 15000,
  });
  const { data: lista } = useQuery({ queryKey: ["usuarios"], queryFn: getUsuarios });
  const logins = useMemo(() => ["mestre", ...(lista ?? []).map((u) => u.login)], [lista]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <select value={usuario} onChange={(e) => setUsuario(e.target.value)} className={inputCls + " max-w-[220px]"}>
          <option value="">Todos os usuários</option>
          {logins.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <select value={acao} onChange={(e) => setAcao(e.target.value)} className={inputCls + " max-w-[280px]"}>
          <option value="">Todas as ações</option>
          {Object.entries(ACOES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted border-b border-border">
              <th className="px-4 py-2.5 font-medium w-36">Data</th>
              <th className="px-4 py-2.5 font-medium w-32">Usuário</th>
              <th className="px-4 py-2.5 font-medium w-56">Ação</th>
              <th className="px-4 py-2.5 font-medium">Detalhe</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={4} className="px-4 py-6 text-center text-muted text-xs">Carregando...</td></tr>}
            {data?.length === 0 && <tr><td colSpan={4} className="px-4 py-6 text-center text-muted text-xs">Nada registrado.</td></tr>}
            {data?.map((a) => (
              <tr key={a.id} className="border-b border-border/50 last:border-0 align-top">
                <td className="px-4 py-2 text-xs text-muted whitespace-nowrap">{dataHora(a.data)}</td>
                <td className="px-4 py-2 font-mono text-xs text-slate-300">{a.usuario || "—"}</td>
                <td className={clsx("px-4 py-2 text-xs",
                  /falhou|errada|excluid/.test(a.acao) ? "text-amber-300" : "text-slate-300")}>
                  {ACOES[a.acao] ?? a.acao}
                </td>
                <td className="px-4 py-2 text-xs text-muted break-all">{[a.detalhe, a.ip].filter(Boolean).join(" · ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted">Mostra os 500 eventos mais recentes do filtro escolhido.</p>
    </div>
  );
}
