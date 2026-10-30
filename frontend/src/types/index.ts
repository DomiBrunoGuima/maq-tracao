export interface EnsaioSummary {
  id: number;
  nome: string;
  filename: string;
  data_ensaio: string;
  num_amostras: number;
  forca_max_N: number;
  tensao_max_MPa: number;
  created_at: string;
  cliente_id: number | null;
  cliente_nome: string;
  amostra: string;
  norma: string;
  operador: string;
}

export interface EnsaioDetail extends EnsaioSummary {
  metadata_version: string;
  metadata_equipment_id: string;
  metadata_code: string;
  alonga_ruptura_pct: number;
  tempo_ruptura_s: number;
  observacoes: string;
  setup: Record<string, number | string | null>;
}

export interface EnsaioUpdate {
  nome?: string;
  cliente_id?: number | null;
  amostra?: string;
  norma?: string;
  operador?: string;
  observacoes?: string;
  limpar_cliente?: boolean;
}

export interface ClienteIn {
  nome: string;
  documento: string;
  contato: string;
  email: string;
  telefone: string;
  endereco: string;
  bairro: string;
  cidade_uf: string;
  cep: string;
  observacoes: string;
}

export interface Cliente extends ClienteIn {
  id: number;
  created_at: string;
  num_ensaios: number;
  num_relatorios: number;
}

export type TipoEnsaio = "tracao" | "flexao";

export interface RelatorioSummary {
  id: number;
  ensaio_id: number | null;
  tipo: TipoEnsaio;
  cliente_id: number | null;
  numero: string;
  titulo: string;
  cliente_nome: string;
  created_at: string;
}

export type TipoBusca = "todos" | "cliente" | "teste" | "relatorio";

export interface ResultadoBusca {
  tipo: "cliente" | "teste" | "relatorio";
  modo?: "tracao" | "flexao";
  id: number;
  titulo: string;
  subtitulo: string;
  data: string | null;
  cliente_id?: number | null;
  ensaio_id?: number | null;
  score: number;
}

export interface Norma {
  codigo: string;
  tipo: "tracao" | "flexao";
  material: string;
  titulo: string;
  corpo_prova: string;
  velocidade_mm_min: number | null;
  comprimento_inicial_mm?: number | null;
  distancia_garras_mm?: number | null;
  span_mm?: number | null;
  largura_mm?: number | null;
  espessura_mm?: number | null;
  observacao: string;
}

export type StatusQualidade = "ok" | "aviso" | "erro" | "info";

export interface ItemQualidade {
  chave: string;
  titulo: string;
  status: StatusQualidade;
  detalhe: string;
}

export interface Qualidade {
  status: StatusQualidade;
  itens: ItemQualidade[];
}

export interface ConexaoCLP {
  online: boolean;
  ip: string;
  port: number;
  simulador: boolean;
  latencia_ms: number | null;
  motivo: string;
}

export interface CamposRelatorio {
  cliente_id: number | null;
  cliente: Partial<DadosCliente> | null;
  amostra: Partial<DadosAmostra>;
  condicoes: Partial<CondicoesEnsaio>;
  empresa: Partial<DadosEmpresa>;
  numero_relatorio_sugerido: string;
  assinaturas: Assinatura[];
  equipamentos: string;
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
  r2_elastico: number | null;
  modulo_trecho_elastico_MPa: number | null;
  pontos_trecho_elastico: number | null;
  tensao_rp02_MPa: number | null;
  ruptura_detectada: boolean;
  forca_ruptura_N: number | null;
  deslocamento_ruptura_mm: number | null;
  alonga_ruptura_real_pct: number | null;
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
  cliente_id: number | null;
  cliente_nome: string;
  amostra: string;
  norma: string;
  operador: string;
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
  observacoes: string;
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
  r2_elastico?: number | null;
  pontos_trecho_elastico?: number | null;
  ruptura_detectada?: boolean;
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
  fases?: FaseFlexao[];
  trecho_elastico?: {
    ss: AjusteElastico | null;   // σf × εf
    fd: AjusteElastico | null;   // F × δ
  };
}

export interface FaseFlexao {
  fase: string;
  rotulo: string;
  n_pontos: number;
  t_ini: number | null;
  t_fim: number | null;
  eps_ini: number | null;
  eps_fim: number | null;
  d_ini: number | null;
  d_fim: number | null;
  forca_max: number | null;
}

export interface AjusteElastico {
  inclinacao: number;
  intercepto: number;
  r2: number;
  n_pontos: number;
  x_ini: number;
  x_fim: number;
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
  cliente_id?: number | null;
  amostra?: string;
  operador?: string;
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
  elastic_fit: ElasticFit | null;
  fases: FaseResumo[];
}

export interface ElasticFit {
  inclinacao: number;
  intercepto: number;
  r2: number;
  n_pontos: number;
  eps_ini: number;
  eps_fim: number;
  sigma_ini: number;
  sigma_fim: number;
  t_ini: number | null;
  t_fim: number | null;
}

export interface FaseResumo {
  fase: string;
  rotulo: string;
  n_pontos: number;
  t_ini: number | null;
  t_fim: number | null;
  eps_ini: number | null;
  eps_fim: number | null;
  d_ini: number | null;
  d_fim: number | null;
  forca_max: number | null;
}

export type ModbusDataType =
  | "uint16"
  | "decimal"
  | "int32"
  | "decimal32"
  | "float32"
  | "coil"
  | "input";

export interface IHMRegister {
  name: string;
  address: number;
  // Dispositivo Delta (ex.: "D412", "M5", "X0"). Se preenchido, substitui address.
  device?: string;
  // Registrador de origem no CLP (ex.: "D600"), só referência
  clp_ref?: string;
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
  device?: string;
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
  plc_family: "dvp" | "direto" | "as";
  control_registers: IHMRegister[];
  control_pulse_ms: number;
  area_seccao_mm2: number;
  comprimento_inicial_mm: number;
  flexao_registers: IHMRegister[];
  // Papéis em que a flexão usa o registrador próprio em vez do da tração
  flexao_separados?: string[];
  flexao_largura_mm: number;
  flexao_espessura_mm: number;
  flexao_span_mm: number;
  flexao_norma: string;
  flexao_habilitada?: boolean;
  forca_clp_kgf?: boolean;
  simulator_enabled: boolean;
  backup_ativo: boolean;
  backup_dir: string;
  backup_intervalo_h: number;
  backup_manter: number;
}

export interface BackupStatus {
  ativo: boolean;
  pasta: string;
  pasta_existe: boolean;
  ultimo: string | null;
  proximo: string | null;
  erro: string | null;
  backups: { arquivo: string; tamanho_kb: number; data: string }[];
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
  forca_maxima?: number | null;
  tensao_maxima?: number | null;
  deslocamento_maximo?: number | null;
  emergencia?: boolean | null;
  limite_superior?: boolean | null;
  limite_inferior?: boolean | null;
}

export interface ControlStartRequest {
  sentido: "cima" | "baixo";
  velocidade?: number | null;
  deslocamento?: number | null;
  limite_forca?: number | null;
  area_seccao?: number | null;
  comprimento_inicial?: number | null;
  cliente_id?: number | null;
  amostra?: string;
  norma?: string;
  operador?: string;
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
  forca_maxima?: number | null;
  tensao_maxima?: number | null;
  deslocamento_maximo?: number | null;
  emergencia?: boolean | null;
  limite_superior?: boolean | null;
  limite_inferior?: boolean | null;
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
  tipo?: TipoEnsaio;
  cliente_id?: number | null;
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
