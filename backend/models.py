from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class EnsaioSummary(BaseModel):
    id: int
    nome: str
    filename: str
    data_ensaio: str
    num_amostras: int
    forca_max_N: float
    tensao_max_MPa: float
    created_at: datetime

    model_config = {"from_attributes": True}


class EnsaioDetail(EnsaioSummary):
    metadata_version: str
    metadata_equipment_id: str
    metadata_code: str
    alonga_ruptura_pct: float
    tempo_ruptura_s: float


class KPIs(BaseModel):
    forca_max_N: float
    forca_max_kN: float
    tensao_max_MPa: float
    modulo_elasticidade_MPa: float
    modulo_elasticidade_GPa: float
    alonga_ruptura_pct: float
    deslocamento_max_mm: float
    tempo_ruptura_s: float
    taxa_carregamento_N_s: float
    rigidez_N_mm: float
    energia_J: float
    tensao_escoamento_MPa: Optional[float] = None
    cv_modulo: float


class EnsaioFlexaoSummary(BaseModel):
    id: int
    nome: str
    filename: str
    data_ensaio: str
    num_amostras: int
    forca_max_N: float
    tensao_flexao_max_MPa: float
    modulo_flexao_MPa: float
    created_at: datetime

    model_config = {"from_attributes": True}


class EnsaioFlexaoDetail(EnsaioFlexaoSummary):
    metadata_version: str
    metadata_equipment_id: str
    metadata_code: str
    deflexao_max_mm: float
    tempo_ensaio_s: float
    largura_mm: float
    espessura_mm: float
    span_mm: float
    norma: str


class KPIsFlexao(BaseModel):
    forca_max_N: float
    forca_max_kN: float
    tensao_flexao_max_MPa: float
    resistencia_flexao_MPa: float
    modulo_flexao_MPa: float
    modulo_flexao_GPa: float
    modulo_regressao_MPa: Optional[float] = None
    modulo_cordal_MPa: Optional[float] = None
    deflexao_max_mm: float
    deflexao_pico_mm: float
    deform_flexao_max_pct: float
    tempo_ensaio_s: float
    tempo_pico_s: float
    rigidez_N_mm: float
    taxa_carregamento_N_s: float
    energia_J: float
    tensao_escoamento_MPa: Optional[float] = None
    cv_modulo: float
    norma: str
    largura_mm: Optional[float] = None
    espessura_mm: Optional[float] = None
    span_mm: Optional[float] = None


class FlexaoControlStartRequest(BaseModel):
    sentido: str = "baixo"             # cutelo desce sobre o corpo de prova
    velocidade: Optional[float] = None
    deslocamento: Optional[float] = None    # deflexão-alvo (mm)
    limite_forca: Optional[float] = None
    largura_mm: Optional[float] = None
    espessura_mm: Optional[float] = None
    span_mm: Optional[float] = None
    norma: Optional[str] = None


class IHMRegister(BaseModel):
    name: str
    address: int
    description: str = ""
    # "coil" | "uint16" | "decimal" | "int32" | "decimal32" | "float32"
    data_type: str = "uint16"
    scale: float = 1.0          # aplicado a uint16/decimal/int32/decimal32: valor_real = raw * scale
    role: str = ""              # papel no controle (iniciar, parar, sentido_cima, limite_forca, ...)
    writable: bool = False      # se o software pode escrever neste registrador
    # Ordem das palavras em tipos de 32 bits: "big" (ABCD, palavra alta 1º, padrão)
    # ou "little" (CDAB, palavra baixa 1º — comum em CLP Mitsubishi/registradores D)
    word_order: str = "big"


class ParametrosIHM(BaseModel):
    id: int
    ensaio_filename: str
    captured_at: datetime
    ihm_ip: str
    params: dict

    model_config = {"from_attributes": True}


class ConfigModel(BaseModel):
    watch_directory: str
    auto_load: bool = True
    refresh_interval_s: int = 5
    ihm_ip: str = ""
    ihm_port: int = 502
    ihm_timeout: int = 3
    ihm_registers: List[IHMRegister] = []
    ftp_port: int = 21
    ftp_user: str = ""
    ftp_password: str = ""
    ftp_remote_dir: str = "/"
    ftp_remote_filename: str = ""
    realtime_interval_ms: int = 100
    realtime_bit_name: str = "teste_ativo_bit"
    realtime_stop_bit_name: str = "teste_parada_bit"
    realtime_forca_name: str = "forca_atual"
    realtime_deslocamento_name: str = "deslocamento_atual"
    # ── Conexão e controle direto do CLP (substitui a IHM) ──────────────────
    clp_ip: str = ""            # se vazio, faz fallback para ihm_ip
    clp_port: int = 502
    clp_timeout: int = 3
    control_registers: List[IHMRegister] = []
    control_pulse_ms: int = 300  # duração do pulso em coils de comando (iniciar/parar)
    area_seccao_mm2: float = 0.0       # default do setup; sobrescrito por ensaio
    comprimento_inicial_mm: float = 0.0
    # ── Flexão (3 pontos) — registradores e geometria default do setup ──────
    flexao_registers: List[IHMRegister] = []
    flexao_largura_mm: float = 0.0
    flexao_espessura_mm: float = 0.0
    flexao_span_mm: float = 0.0
    flexao_norma: str = "ISO 178"
    # ── Simulador: gera valores plausíveis sem IHM/máquina real ─────────────
    simulator_enabled: bool = False


class ControlStartRequest(BaseModel):
    sentido: str = "cima"              # "cima" | "baixo"
    velocidade: Optional[float] = None
    deslocamento: Optional[float] = None
    limite_forca: Optional[float] = None
    area_seccao: Optional[float] = None
    comprimento_inicial: Optional[float] = None


class ControlSetpointsRequest(BaseModel):
    sentido: Optional[str] = None      # "cima" | "baixo" | None (não altera)
    velocidade: Optional[float] = None
    deslocamento: Optional[float] = None
    limite_forca: Optional[float] = None


class RegisterProbeRequest(BaseModel):
    """Teste isolado de um registrador, sem depender do mapa de controle salvo."""
    address: int
    data_type: str = "float32"          # coil|uint16|decimal|int32|decimal32|float32
    scale: float = 1.0
    word_order: str = "big"             # big|little (tipos de 32 bits)
    direction: str = "read"             # "read" (entrada) | "write" (saída)
    value: Optional[float] = None       # obrigatório quando direction == "write"
    name: str = ""


class ControlStatus(BaseModel):
    online: bool = False
    forca_atual: Optional[float] = None
    deslocamento_atual: Optional[float] = None
    material_integro: Optional[bool] = None
    ruptura: Optional[bool] = None
    ativo: Optional[bool] = None


class DadosEmpresa(BaseModel):
    nome: str = ""
    endereco: str = ""
    telefone: str = ""
    email: str = ""
    site: str = ""
    numero_relatorio: str = ""
    logo_data_url: str = ""   # data URL completo (data:image/...;base64,...)

class DadosCliente(BaseModel):
    nome: str = ""
    os: str = ""
    contato: str = ""
    email_cliente: str = ""
    telefone_cliente: str = ""
    endereco: str = ""
    bairro: str = ""
    cidade_uf: str = ""
    cep: str = ""
    data_recebimento: str = ""
    periodo_realizacao: str = ""

class DadosAmostra(BaseModel):
    id_interno: str = ""
    id_cliente: str = ""
    imagem_data_url: str = ""  # data URL completo

class CondicoesEnsaio(BaseModel):
    temp_laboratorio: str = ""
    umidade_laboratorio: str = ""
    temp_ensaio: str = "Tamb"
    num_corpos_prova: str = "1"
    celula_carga: str = ""
    celula_carga_unidade: str = "kN"
    comprimento_inicial_mm: str = ""
    velocidade_ensaio: str = ""
    velocidade_ensaio_unidade: str = "mm/min"
    tipo_corpo_prova: str = ""
    distancia_garras_mm: str = ""
    extensometro: str = ""
    largura_cp_mm: str = ""
    espessura_cp_mm: str = ""
    preparacao_cp: List[str] = []
    data_realizacao: str = ""
    equipamentos: str = ""
    norma_referencia: str = "ISO 527-1:2019"

class Assinatura(BaseModel):
    nome: str = ""
    cargo: str = ""

class ReportRequest(BaseModel):
    ensaio_id: int
    # Flags de seção
    include_empresa: bool = True
    include_cliente: bool = False
    include_amostra: bool = True
    include_objetivos: bool = False
    include_condicoes: bool = True
    include_resultados: bool = True
    include_stress_strain: bool = True
    include_graficos_adicionais: bool = False
    include_comparativo: bool = False
    comparacao_ids: List[int] = []
    include_raw_data: bool = False
    include_conclusao: bool = True
    include_observacoes_finais: bool = True
    # Dados das seções
    empresa: DadosEmpresa = Field(default_factory=DadosEmpresa)
    cliente: DadosCliente = Field(default_factory=DadosCliente)
    amostra: DadosAmostra = Field(default_factory=DadosAmostra)
    objetivos: str = ""
    condicoes: CondicoesEnsaio = Field(default_factory=CondicoesEnsaio)
    local_data: str = ""
    assinaturas: List[Assinatura] = []
    observacoes_finais: str = (
        "Os resultados aqui apresentados referem-se exclusivamente às amostras analisadas, "
        "nas condições em que foram realizados os ensaios, não sendo extensivos a quaisquer "
        "lotes, mesmo que similares.\n"
        "O laboratório não é responsável em caso de interpretação ou uso indevido que se possa "
        "fazer deste documento.\n"
        "A reprodução deste documento deve ser realizada na íntegra."
    )
    # Legado
    operator_name: str = ""
    specimen_id: str = ""
    standard: str = ""
    format: str = "html"
    observations: str = ""
