from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./tracao.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class EnsaioDB(Base):
    __tablename__ = "ensaios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    filename = Column(String, unique=True, index=True)
    data_ensaio = Column(String)
    num_amostras = Column(Integer)
    forca_max_N = Column(Float)
    tensao_max_MPa = Column(Float)
    alonga_ruptura_pct = Column(Float)
    tempo_ruptura_s = Column(Float)
    metadata_version = Column(String)
    metadata_equipment_id = Column(String)
    metadata_code = Column(String)
    filepath = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    data_json = Column(Text)
    # Cadastro do teste (preenchido no Controle antes do ensaio ou editado depois)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    amostra = Column(String, default="")
    norma = Column(String, default="")
    operador = Column(String, default="")
    observacoes = Column(Text, default="")
    # JSON com o setup usado (velocidade, deslocamento, limite de força, área, L0, sentido)
    setup_json = Column(Text, default="")


class EnsaioFlexaoDB(Base):
    __tablename__ = "ensaios_flexao"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    filename = Column(String, unique=True, index=True)
    data_ensaio = Column(String)
    num_amostras = Column(Integer)
    forca_max_N = Column(Float)
    tensao_flexao_max_MPa = Column(Float)
    modulo_flexao_MPa = Column(Float)
    deflexao_max_mm = Column(Float)
    tempo_ensaio_s = Column(Float)
    # Geometria do corpo de prova (flexão 3 pontos)
    largura_mm = Column(Float)
    espessura_mm = Column(Float)
    span_mm = Column(Float)
    norma = Column(String)
    metadata_version = Column(String)
    metadata_equipment_id = Column(String)
    metadata_code = Column(String)
    filepath = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    data_json = Column(Text)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    amostra = Column(String, default="")
    operador = Column(String, default="")
    observacoes = Column(Text, default="")


class ParametrosIHMDB(Base):
    __tablename__ = "parametros_ihm"

    id               = Column(Integer, primary_key=True, index=True)
    ensaio_filename  = Column(String, index=True)
    captured_at      = Column(DateTime, default=datetime.utcnow)
    ihm_ip           = Column(String)
    params_json      = Column(Text)  # JSON: {name: value}


class ClienteDB(Base):
    __tablename__ = "clientes"

    id         = Column(Integer, primary_key=True, index=True)
    nome       = Column(String, index=True, nullable=False)
    documento  = Column(String, default="")   # CNPJ/CPF
    contato    = Column(String, default="")
    email      = Column(String, default="")
    telefone   = Column(String, default="")
    endereco   = Column(String, default="")
    bairro     = Column(String, default="")
    cidade_uf  = Column(String, default="")
    cep        = Column(String, default="")
    observacoes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class RelatorioDB(Base):
    """Relatório gerado: guarda o HTML final e o pedido que o gerou, para abrir de novo
    ou buscar depois sem precisar refazer."""
    __tablename__ = "relatorios"

    id           = Column(Integer, primary_key=True, index=True)
    ensaio_id    = Column(Integer, index=True)
    tipo         = Column(String, default="tracao")   # "tracao" ou "flexao": tabela do ensaio_id
    cliente_id   = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    numero       = Column(String, default="")
    titulo       = Column(String, default="")
    cliente_nome = Column(String, default="")
    request_json = Column(Text, default="")
    html         = Column(Text, default="")
    created_at   = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate(eng=engine) -> None:
    """SQLite não ganha colunas novas com create_all: adiciona as que faltam em bancos
    criados por versões anteriores (sem perder os ensaios já gravados)."""
    from sqlalchemy import inspect, text
    insp = inspect(eng)
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl_type = col.type.compile(dialect=eng.dialect)
                default = col.default.arg if col.default is not None and not callable(col.default.arg) else None
                sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}'
                if isinstance(default, str):
                    sql += " DEFAULT '" + default.replace("'", "''") + "'"
                conn.execute(text(sql))


Base.metadata.create_all(bind=engine)
migrate()
