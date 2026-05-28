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


class ParametrosIHMDB(Base):
    __tablename__ = "parametros_ihm"

    id               = Column(Integer, primary_key=True, index=True)
    ensaio_filename  = Column(String, index=True)
    captured_at      = Column(DateTime, default=datetime.utcnow)
    ihm_ip           = Column(String)
    params_json      = Column(Text)  # JSON: {name: value}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
