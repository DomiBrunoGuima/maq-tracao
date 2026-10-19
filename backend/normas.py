"""Normas de referência padronizadas para os ensaios.

Cada norma traz os parâmetros sugeridos que o software pré-preenche no Controle e
no relatório (velocidade, L0, distância entre garras, corpo de prova). São valores
de partida usuais: conferir sempre a edição vigente da norma e o material ensaiado.
"""
from __future__ import annotations

NORMAS: list[dict] = [
    # ── Tração ──────────────────────────────────────────────────────────────
    {
        "codigo": "ISO 527-2", "tipo": "tracao", "material": "Plásticos",
        "titulo": "Plásticos — Determinação das propriedades de tração (moldagem e extrusão)",
        "corpo_prova": "Tipo 1A (170 × 10 × 4 mm)",
        "velocidade_mm_min": 50.0, "comprimento_inicial_mm": 75.0, "distancia_garras_mm": 115.0,
        "observacao": "Módulo a 1 mm/min; resistência a 50 mm/min (ou 5 mm/min para materiais frágeis).",
    },
    {
        "codigo": "ASTM D638", "tipo": "tracao", "material": "Plásticos",
        "titulo": "Standard Test Method for Tensile Properties of Plastics",
        "corpo_prova": "Tipo I (165 × 13 × 3,2 mm)",
        "velocidade_mm_min": 5.0, "comprimento_inicial_mm": 50.0, "distancia_garras_mm": 115.0,
        "observacao": "5 mm/min para plásticos rígidos; 50 mm/min para não rígidos.",
    },
    {
        "codigo": "ABNT NBR ISO 6892-1", "tipo": "tracao", "material": "Metais",
        "titulo": "Materiais metálicos — Ensaio de tração à temperatura ambiente",
        "corpo_prova": "Proporcional (L₀ = 5,65·√S₀)",
        "velocidade_mm_min": None, "comprimento_inicial_mm": None, "distancia_garras_mm": None,
        "observacao": "Velocidade pela taxa de deformação (método A) ou de tensão (método B); L₀ depende da seção.",
    },
    {
        "codigo": "ASTM E8/E8M", "tipo": "tracao", "material": "Metais",
        "titulo": "Standard Test Methods for Tension Testing of Metallic Materials",
        "corpo_prova": "Chapa padrão (12,5 mm de largura)",
        "velocidade_mm_min": None, "comprimento_inicial_mm": 50.0, "distancia_garras_mm": None,
        "observacao": "Controle por taxa de deformação; L₀ = 50 mm para corpo de prova padrão.",
    },
    {
        "codigo": "ASTM D3039", "tipo": "tracao", "material": "Compósitos",
        "titulo": "Tensile Properties of Polymer Matrix Composite Materials",
        "corpo_prova": "250 × 25 × 2,5 mm",
        "velocidade_mm_min": 2.0, "comprimento_inicial_mm": None, "distancia_garras_mm": None,
        "observacao": "Velocidade padrão de 2 mm/min.",
    },
    {
        "codigo": "ISO 37", "tipo": "tracao", "material": "Borrachas",
        "titulo": "Borracha vulcanizada ou termoplástica — Propriedades de tensão-deformação",
        "corpo_prova": "Gravata tipo 1",
        "velocidade_mm_min": 500.0, "comprimento_inicial_mm": 25.0, "distancia_garras_mm": None,
        "observacao": "500 mm/min para tipos 1 e 2; 200 mm/min para tipos 3 e 4.",
    },
    {
        "codigo": "ASTM D412", "tipo": "tracao", "material": "Borrachas",
        "titulo": "Vulcanized Rubber and Thermoplastic Elastomers — Tension",
        "corpo_prova": "Matriz C",
        "velocidade_mm_min": 500.0, "comprimento_inicial_mm": 25.0, "distancia_garras_mm": None,
        "observacao": "Velocidade de 500 ± 50 mm/min.",
    },
    # ── Flexão ──────────────────────────────────────────────────────────────
    {
        "codigo": "ISO 178", "tipo": "flexao", "material": "Plásticos",
        "titulo": "Plásticos — Determinação das propriedades de flexão",
        "corpo_prova": "80 × 10 × 4 mm",
        "velocidade_mm_min": 2.0, "span_mm": 64.0, "largura_mm": 10.0, "espessura_mm": 4.0,
        "observacao": "Vão L = 16·h; 2 mm/min para o corpo de prova preferencial.",
    },
    {
        "codigo": "ASTM D790", "tipo": "flexao", "material": "Plásticos",
        "titulo": "Flexural Properties of Unreinforced and Reinforced Plastics",
        "corpo_prova": "127 × 12,7 × 3,2 mm",
        "velocidade_mm_min": 1.4, "span_mm": 51.2, "largura_mm": 12.7, "espessura_mm": 3.2,
        "observacao": "Vão 16:1; velocidade R = 0,01·L²/(6·d) (procedimento A).",
    },
]


def listar_normas(tipo: str | None = None) -> list[dict]:
    if tipo:
        return [n for n in NORMAS if n["tipo"] == tipo]
    return list(NORMAS)
