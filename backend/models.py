from pydantic import BaseModel
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


class ReportRequest(BaseModel):
    ensaio_id: int
    include_metadata: bool = True
    include_kpis: bool = True
    include_stress_strain: bool = True
    include_force_displacement: bool = True
    include_force_time: bool = True
    include_raw_data: bool = False
    include_derived_data: bool = True
    observations: str = ""
    operator_name: str = ""
    specimen_id: str = ""
    standard: str = ""
    format: str = "html"
