import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

# Database Configuration (Supabase PostgreSQL)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Use a local SQLite db for testing if no URL provided
    DATABASE_URL = "sqlite:///./local_helpdesk.db"
    print("Warning: DATABASE_URL not set. Using local SQLite database.")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chamado(Base):
    __tablename__ = "chamados"

    id = Column(Integer, primary_key=True, index=True)
    setor = Column(Text, nullable=False, default="Geral")
    descricao = Column(Text, nullable=False)
    categoria = Column(String(100), nullable=True)
    prioridade = Column(String(50), nullable=False)
    justificativa = Column(Text, nullable=True)
    status = Column(Text, nullable=True, default="Triado pela IA")
    data_criacao = Column(DateTime(timezone=False), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)
    # Garantir que tabelas já existentes no Supabase recebam as colunas novas sem perder dados
    if DATABASE_URL.startswith("postgresql://"):
        migration_statements = [
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS setor TEXT DEFAULT 'Geral';",
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS categoria VARCHAR(100);",
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS justificativa TEXT;",
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Triado pela IA';",
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT NOW();",
            "ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();"
        ]
        try:
            with engine.begin() as conn:
                for stmt in migration_statements:
                    conn.execute(text(stmt))
        except Exception as e:
            print(f"Aviso ao sincronizar colunas da tabela chamados: {e}")

def save_chamado(descricao: str, categoria: str, prioridade: str, justificativa: str):
    db = SessionLocal()
    try:
        novo_chamado = Chamado(
            setor=categoria,
            descricao=descricao,
            categoria=categoria,
            prioridade=prioridade,
            justificativa=justificativa,
            status="Triado pela IA"
        )
        db.add(novo_chamado)
        db.commit()
        db.refresh(novo_chamado)
        return {
            "id": novo_chamado.id,
            "setor": novo_chamado.setor,
            "descricao": novo_chamado.descricao,
            "categoria": novo_chamado.categoria or novo_chamado.setor,
            "prioridade": novo_chamado.prioridade,
            "justificativa": novo_chamado.justificativa,
            "status": novo_chamado.status,
            "created_at": str(novo_chamado.created_at or novo_chamado.data_criacao)
        }
    finally:
        db.close()

def get_recent_chamados(limit: int = 10):
    db = SessionLocal()
    try:
        chamados = db.query(Chamado).order_by(Chamado.id.desc()).limit(limit).all()
        return [
            {
                "id": c.id,
                "setor": c.setor,
                "descricao": c.descricao,
                "categoria": c.categoria or c.setor or "Geral",
                "prioridade": c.prioridade,
                "justificativa": c.justificativa or "",
                "status": c.status or "Aberto",
                "created_at": str(c.created_at or c.data_criacao or "")
            }
            for c in chamados
        ]
    finally:
        db.close()
