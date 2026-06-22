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
  velocidade_ihm: number | null;
}

export interface DataPoint {
  [key: string]: number | string | null;
}

// ── Flexão (3 pontos) ───────────────────────────────────────────────────────

export interface EnsaioFlexaoSummary {
  id: number;
  nome: string;
  filename: string;
  data_ensaio: string;
  num_amostras: number;
  forca_max_N: number;
  tensao_flexao_max_MPa: number;
  modulo_flexao_MPa: number;
  created_at: string;
}

export interface EnsaioFlexaoDetail extends EnsaioFlexaoSummary {
  metadata_version: string;
  metadata_equipment_id: string;
  metadata_code: string;
  deflexao_max_mm: number;
  tempo_ensaio_s: number;
  largura_mm: number;
  espessura_mm: number;
  span_mm: number;
  norma: string;
}

export interface KPIsFlexao {
  forca_max_N: number;
  forca_max_kN: number;
  tensao_flexao_max_MPa: number;
  resistencia_flexao_MPa: number;
  modulo_flexao_MPa: number;
  modulo_flexao_GPa: number;
  modulo_regressao_MPa: number | null;
  modulo_cordal_MPa: number | null;
  deflexao_max_mm: number;
  deflexao_pico_mm: number;
  deform_flexao_max_pct: number;
  tempo_ensaio_s: number;
  tempo_pico_s: number;
  rigidez_N_mm: number;
  taxa_carregamento_N_s: number;
  energia_J: number;
  tensao_escoamento_MPa: number | null;
  cv_modulo: number;
  norma: string;
  largura_mm: number | null;
  espessura_mm: number | null;
  span_mm: number | null;
}

export interface FlexaoChartData {
  stress_strain: DataPoint[];
  force_displacement: DataPoint[];
  force_time: DataPoint[];
  flexural_modulus_time: DataPoint[];
  stress_time: DataPoint[];
  peak: {
    elapsed_seconds: number;
    Forca_N: number;
    Deform_Flexao: number;
    Tensao_Flexao: number;
    Deslocamento: number;
  };
  Ef_regressao: number | null;
}

export interface FlexaoControlStartRequest {
  sentido: "cima" | "baixo";
  velocidade?: number | null;
  deslocamento?: number | null;
  limite_forca?: number | null;
  largura_mm?: number | null;
  espessura_mm?: number | null;
  span_mm?: number | null;
  norma?: string | null;
}

export interface FlexaoFrame {
  recording: boolean;
  forca: number | null;
  deslocamento: number | null;
  fim_ensaio?: boolean;
  t_ms: number;
  error?: string;
  saved_ensaio_id?: number | null;
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
  E_regressao: number | null;
}

export type ModbusDataType =
  | "uint16"
  | "decimal"
  | "int32"
  | "decimal32"
  | "float32"
  | "coil";

export interface IHMRegister {
  name: string;
  address: number;
  description: string;
  data_type: ModbusDataType;
  scale: number;
  role?: string;
  writable?: boolean;
  // Ordem das palavras em tipos de 32 bits: "big" (HI primeiro, ABCD) ou
  // "little" (LO primeiro, CDAB — comum em CLP Mitsubishi/registradores D)
  word_order?: "big" | "little";
}

export interface RegisterProbeRequest {
  address: number;
  data_type: ModbusDataType;
  scale?: number;
  word_order?: "big" | "little";
  direction: "read" | "write";
  value?: number | null;
  name?: string;
}

export interface RegisterProbeResult {
  ok: boolean;
  direction: "read" | "write";
  address: number;
  name: string;
  data_type: string;
  word_order: string;
  scale: number;
  ip: string;
  port: number;
  sent_words: number[] | null;
  read_words: number[] | null;
  decoded: number | null;
  as_float: number | null;
  as_int: number | null;
  error: string | null;
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
  ftp_port: number;
  ftp_user: string;
  ftp_password: string;
  ftp_remote_dir: string;
  ftp_remote_filename: string;
  realtime_interval_ms: number;
  realtime_bit_name: string;
  realtime_stop_bit_name: string;
  realtime_forca_name: string;
  realtime_deslocamento_name: string;
  clp_ip: string;
  clp_port: number;
  clp_timeout: number;
  control_registers: IHMRegister[];
  control_pulse_ms: number;
  area_seccao_mm2: number;
  comprimento_inicial_mm: number;
  flexao_registers: IHMRegister[];
  flexao_largura_mm: number;
  flexao_espessura_mm: number;
  flexao_span_mm: number;
  flexao_norma: string;
  simulator_enabled: boolean;
}

export interface RealtimePoint {
  t_ms: number;
  forca: number;
  deslocamento: number;
}

export interface RealtimeFrame {
  recording: boolean;
  bit: boolean;
  forca: number | null;
  deslocamento: number | null;
  t_ms: number;
  error?: string;
  stopped?: boolean;
  material_integro?: boolean | null;
  ruptura?: boolean;
  saved_ensaio_id?: number | null;
}

export interface ControlStartRequest {
  sentido: "cima" | "baixo";
  velocidade?: number | null;
  deslocamento?: number | null;
  limite_forca?: number | null;
  area_seccao?: number | null;
  comprimento_inicial?: number | null;
}

export interface ControlSetpointsRequest {
  sentido?: "cima" | "baixo" | null;
  velocidade?: number | null;
  deslocamento?: number | null;
  limite_forca?: number | null;
}

export interface ControlStatus {
  online: boolean;
  forca_atual: number | null;
  deslocamento_atual: number | null;
  material_integro: boolean | null;
  ruptura: boolean | null;
  ativo: boolean | null;
}

export interface ModbusFetchResult {
  status: string;
  bytes_received: number;
  filename: string;
  ensaio_id: number;
}

export interface DadosEmpresa {
  nome: string;
  endereco: string;
  telefone: string;
  email: string;
  site: string;
  numero_relatorio: string;
  logo_data_url: string;
}

export interface DadosCliente {
  nome: string;
  os: string;
  contato: string;
  email_cliente: string;
  telefone_cliente: string;
  endereco: string;
  bairro: string;
  cidade_uf: string;
  cep: string;
  data_recebimento: string;
  periodo_realizacao: string;
}

export interface DadosAmostra {
  id_interno: string;
  id_cliente: string;
  imagem_data_url: string;
}

export interface CondicoesEnsaio {
  temp_laboratorio: string;
  umidade_laboratorio: string;
  temp_ensaio: string;
  num_corpos_prova: string;
  celula_carga: string;
  celula_carga_unidade: string;
  comprimento_inicial_mm: string;
  velocidade_ensaio: string;
  velocidade_ensaio_unidade: string;
  tipo_corpo_prova: string;
  distancia_garras_mm: string;
  extensometro: string;
  largura_cp_mm: string;
  espessura_cp_mm: string;
  preparacao_cp: string[];
  data_realizacao: string;
  equipamentos: string;
  norma_referencia: string;
}

export interface Assinatura {
  nome: string;
  cargo: string;
}

export interface ReportRequest {
  ensaio_id: number;
  include_empresa: boolean;
  include_cliente: boolean;
  include_amostra: boolean;
  include_objetivos: boolean;
  include_condicoes: boolean;
  include_resultados: boolean;
  include_stress_strain: boolean;
  include_graficos_adicionais: boolean;
  include_comparativo: boolean;
  comparacao_ids: number[];
  include_raw_data: boolean;
  include_conclusao: boolean;
  include_observacoes_finais: boolean;
  empresa: DadosEmpresa;
  cliente: DadosCliente;
  amostra: DadosAmostra;
  objetivos: string;
  condicoes: CondicoesEnsaio;
  local_data: string;
  assinaturas: Assinatura[];
  observacoes_finais: string;
  operator_name: string;
  specimen_id: string;
  standard: string;
  format: string;
  observations: string;
}
