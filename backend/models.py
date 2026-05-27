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


class IHMRegister(BaseModel):
    name: str
    address: int
    description: str = ""
    data_type: str = "uint16"   # "uint16" | "decimal" | "float32"
    scale: float = 1.0          # aplicado ao uint16/decimal: valor_real = raw * scale


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
    comprimento_inicial_mm: str = ""
    velocidade_ensaio: str = ""
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
