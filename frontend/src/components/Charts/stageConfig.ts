import type { DataPoint } from "../../types";

export const STAGE_COLORS: Record<string, string> = {
  elastico_linear:     "#38bdf8",
  escoamento_superior: "#f59e0b",
  patamar_escoamento:  "#10b981",
  encruamento:         "#a78bfa",
  estriccao:           "#f97316",
  ruptura:             "#ef4444",
  carregamento:        "#38bdf8",
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
    // Include bridge point from previous stage to ensure visual continuity
    if (groups[stage].length === 0 && i > 0) {
      groups[stage].push(data[i - 1]);
    }
    groups[stage].push(data[i]);
  }
  return groups;
}

/** Returns X ranges per stage for use as ReferenceArea bands. */
export function stageRanges(data: DataPoint[], xKey: string): { stage: string; x1: number; x2: number }[] {
  const ranges: { stage: string; x1: number; x2: number }[] = [];
  for (const pt of data) {
    const stage = String(pt.fase ?? "");
    const x = typeof pt[xKey] === "number" ? (pt[xKey] as number) : null;
    if (x == null) continue;
    const last = ranges[ranges.length - 1];
    if (!last || last.stage !== stage) {
      ranges.push({ stage, x1: x, x2: x });
    } else {
      last.x2 = x;
    }
  }
  return ranges;
}
