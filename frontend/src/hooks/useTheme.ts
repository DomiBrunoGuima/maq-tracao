import { useEffect, useState } from "react";

export type Tema = "escuro" | "claro";

const CHAVE = "maq-tracao.tema";

function temaSalvo(): Tema {
  try {
    return localStorage.getItem(CHAVE) === "claro" ? "claro" : "escuro";
  } catch {
    return "escuro";
  }
}

/** Aplica o tema na raiz do documento (classe "light") e lembra a escolha neste PC. */
export function aplicarTemaInicial() {
  document.documentElement.classList.toggle("light", temaSalvo() === "claro");
}

export function useTheme() {
  const [tema, setTema] = useState<Tema>(temaSalvo);

  useEffect(() => {
    document.documentElement.classList.toggle("light", tema === "claro");
    try {
      localStorage.setItem(CHAVE, tema);
    } catch {
      /* sem armazenamento local: vale só nesta sessão */
    }
  }, [tema]);

  return { tema, alternar: () => setTema((t) => (t === "claro" ? "escuro" : "claro")) };
}
