import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

def _get_clean_env(target_key: str) -> str:
    val = os.environ.get(target_key, "")
    if not val:
        for k, v in os.environ.items():
            if k.strip().upper() == target_key.upper():
                val = v
                break
    return val.strip().strip('"').strip("'")

# Database Configuration (Supabase PostgreSQL)
raw_db_url = _get_clean_env("DATABASE_URL")

if not raw_db_url:
    # Use a local SQLite db for testing if no URL provided
    DATABASE_URL = "sqlite:///./local_helpdesk.db"
    DB_TYPE = "sqlite"
    print("Warning: DATABASE_URL not set. Using local SQLite database.")
else:
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = raw_db_url
    DB_TYPE = "supabase_postgres"

# SQLAlchemy setup
try:
    if DB_TYPE == "supabase_postgres":
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
except Exception as e:
    print(f"Error creating database engine ({DB_TYPE}): {e}. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./local_helpdesk.db"
    DB_TYPE = "sqlite_fallback"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chamado(Base):
    __tablename__ = "chamados"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(Text, nullable=False)
    categoria = Column(String(100), nullable=False)
    prioridade = Column(String(50), nullable=False)
    justificativa = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print(f"Database initialized successfully ({DB_TYPE}).")
    except Exception as e:
        print(f"Warning during init_db ({DB_TYPE}): {e}")

def save_chamado(descricao: str, categoria: str, prioridade: str, justificativa: str):
    db = SessionLocal()
    try:
        novo_chamado = Chamado(
            descricao=descricao,
            categoria=categoria,
            prioridade=prioridade,
            justificativa=justificativa
        )
        db.add(novo_chamado)
        db.commit()
        db.refresh(novo_chamado)
        return {
            "id": novo_chamado.id,
            "descricao": novo_chamado.descricao,
            "categoria": novo_chamado.categoria,
            "prioridade": novo_chamado.prioridade,
            "justificativa": novo_chamado.justificativa,
            "created_at": str(novo_chamado.created_at)
        }
    finally:
        db.close()

def get_recent_chamados(limit: int = 10):
    db = SessionLocal()
    try:
        chamados = db.query(Chamado).order_by(Chamado.created_at.desc()).limit(limit).all()
        return [
            {
                "id": c.id,
                "descricao": c.descricao,
                "categoria": c.categoria,
                "prioridade": c.prioridade,
                "justificativa": c.justificativa,
                "created_at": str(c.created_at)
            }
            for c in chamados
        ]
    finally:
        db.close()
