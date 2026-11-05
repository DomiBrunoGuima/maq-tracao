import { createContext, useContext } from "react";
import type { UsuarioLogado } from "../types";

export interface AuthCtx {
  usuario: UsuarioLogado;
  sair: () => void;
}

export const AuthContext = createContext<AuthCtx | null>(null);

/** Usuário logado (só existe dentro do app já autenticado). */
export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora do AuthContext");
  return ctx;
}

/** Versão que não exige o contexto (componentes usados também fora do login). */
export function useUsuarioOpcional(): UsuarioLogado | null {
  return useContext(AuthContext)?.usuario ?? null;
}
