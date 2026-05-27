import type { DataPoint } from "../../types";

export const STAGE_COLORS: Record<string, string> = {
  elastico_linear:     "#00d4ff",
  escoamento_superior: "#f59e0b",
  patamar_escoamento:  "#10b981",
  encruamento:         "#8b5cf6",
  estriccao:           "#f97316",
  ruptura:             "#ef4444",
  // retrocompatibilidade
  carregamento:        "#00d4ff",
  pos_ruptura:         "#f97316",
};

export const STAGE_LABELS: Record<string, string> = {
  elastico_linear:     "Elástico Linear",
  escoamento_superior: "Escoamento Superior",
  patamar_escoamento:  "Patamar de Escoamento",
  encruamento:         "Encruamento",
  estriccao:           "Estricção",
  ruptura:             "Ruptura",
  carregamento:        "Carregamento",
  pos_ruptura:         "Pós-ruptura",
};

export const ORDERED_STAGES = [
  "elastico_linear",
  "escoamento_superior",
  "patamar_escoamento",
  "encruamento",
  "estriccao",
  "ruptura",
  "carregamento",
  "pos_ruptura",
] as const;

export type StageName = (typeof ORDERED_STAGES)[number];

export function splitByStage(data: DataPoint[]): Record<string, DataPoint[]> {
  const groups: Record<string, DataPoint[]> = {};
  ORDERED_STAGES.forEach((s) => { groups[s] = []; });

  for (let i = 0; i < data.length; i++) {
    const stage = String(data[i].fase ?? "");
    if (!(stage in groups)) continue;
    if (groups[stage].length === 0 && i > 0) {
      groups[stage].push(data[i - 1]);
    }
    groups[stage].push(data[i]);
  }
  return groups;
}
