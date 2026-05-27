export interface EnsaioSummary {
  id: number;
  nome: string;
  filename: string;
  data_ensaio: string;
  num_amostras: number;
  forca_max_N: number;
  tensao_max_MPa: number;
  created_at: string;
}

export interface EnsaioDetail extends EnsaioSummary {
  metadata_version: string;
  metadata_equipment_id: string;
  metadata_code: string;
  alonga_ruptura_pct: number;
  tempo_ruptura_s: number;
}

export interface KPIs {
  forca_max_N: number;
  forca_max_kN: number;
  tensao_max_MPa: number;
  modulo_elasticidade_MPa: number;
  modulo_elasticidade_GPa: number;
  alonga_ruptura_pct: number;
  deslocamento_max_mm: number;
  tempo_ruptura_s: number;
  taxa_carregamento_N_s: number;
  rigidez_N_mm: number;
  energia_J: number;
  tensao_escoamento_MPa: number | null;
  cv_modulo: number;
  area_secao_mm2: number | null;
  comprimento_inicial_mm: number | null;
  tensao_max_calc_MPa: number | null;
  alonga_calc_pct: number | null;
  modulo_regressao_MPa: number | null;
}

export interface DataPoint {
  [key: string]: number | string | null;
}

export interface RupturePoint {
  elapsed_seconds: number;
  Forca_N: number;
  Deform_Along: number;
  Tensao_Pa: number;
  Deslocamento: number;
}

export interface ChartData {
  stress_strain: DataPoint[];
  force_displacement: DataPoint[];
  force_time: DataPoint[];
  elastic_modulus_time: DataPoint[];
  stress_time: DataPoint[];
  rupture: RupturePoint;
}

export interface IHMRegister {
  name: string;
  address: number;
  description: string;
  data_type: "uint16" | "decimal" | "float32";
  scale: number;
}

export interface ParametrosIHM {
  id: number;
  ensaio_filename: string;
  captured_at: string;
  ihm_ip: string;
  params: Record<string, number | null>;
}

export interface AppConfig {
  watch_directory: string;
  auto_load: boolean;
  refresh_interval_s: number;
  ihm_ip: string;
  ihm_port: number;
  ihm_timeout: number;
  ihm_registers: IHMRegister[];
}

export interface ReportRequest {
  ensaio_id: number;
  include_metadata: boolean;
  include_kpis: boolean;
  include_stress_strain: boolean;
  include_force_displacement: boolean;
  include_force_time: boolean;
  include_raw_data: boolean;
  include_derived_data: boolean;
  observations: string;
  operator_name: string;
  specimen_id: string;
  standard: string;
  format: string;
}
