import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

# Database Configuration (Supabase PostgreSQL)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Use a local SQLite db for testing if no URL provided
    DATABASE_URL = "sqlite:///./local_helpdesk.db"
    print("Warning: DATABASE_URL not set. Using local SQLite database.")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
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
    Base.metadata.create_all(bind=engine)

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
