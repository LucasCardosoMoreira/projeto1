import os
import re
import json
import urllib.request
import urllib.error
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

def _get_clean_env(target_key: str) -> str:
    val = os.environ.get(target_key, "")
    if not val:
        for k, v in os.environ.items():
            if k.strip().upper() == target_key.upper():
                val = v
                break
    val = val.strip().strip('"').strip("'").strip("`").strip()
    if val.upper().startswith(f"{target_key.upper()}="):
        val = val.split("=", 1)[1].strip().strip('"').strip("'").strip("`")
    return val

def _find_postgres_url() -> str:
    # Procura em DATABASE_URL ou em qualquer variável de ambiente que contenha postgresql:// ou postgres://
    candidates = [
        _get_clean_env("DATABASE_URL"),
        _get_clean_env("SUPABASE_DB_URL"),
        _get_clean_env("POSTGRES_URL"),
    ]
    for _, v in os.environ.items():
        cleaned = v.strip().strip('"').strip("'").strip("`")
        if cleaned.startswith("postgresql://") or cleaned.startswith("postgres://"):
            candidates.append(cleaned)

    for url in candidates:
        if not url:
            continue
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        # Remove colchetes acidentais ao redor da senha, ex: :[minhasenha]@ -> :minhasenha@
        url = re.sub(r":\[([^\]]+)\]@", r":\1@", url)
        if url.startswith("postgresql://"):
            return url
    return ""

def _priority_weight(prioridade: str) -> int:
    if not prioridade:
        return 5
    p = prioridade.lower().strip()
    if "crítica" in p or "critica" in p:
        return 1
    if "alta" in p:
        return 2
    if "média" in p or "media" in p:
        return 3
    if "baixa" in p:
        return 4
    return 5

def _sort_chamados(lista: list) -> list:
    """Ordena por: 1º Prioridade (Crítica > Alta > Média > Baixa), 2º Menor ID (mais antigo primeiro)."""
    return sorted(
        lista,
        key=lambda c: (_priority_weight(c.get("prioridade", "")), int(c.get("id") or 0))
    )

# Configurações de ambiente
raw_db_url = _find_postgres_url()
SUPABASE_URL = _get_clean_env("SUPABASE_URL").rstrip("/")
if SUPABASE_URL.endswith("/rest/v1"):
    SUPABASE_URL = SUPABASE_URL[:-8].rstrip("/")
SUPABASE_KEY = _get_clean_env("SUPABASE_KEY")

DB_TYPE = "sqlite"
DB_DIAGNOSTIC = "init"
DATABASE_URL = "sqlite:///./local_helpdesk.db"
engine = None

if raw_db_url:
    engine = create_engine(
        raw_db_url,
        pool_pre_ping=True,
        pool_recycle=180,
        connect_args={"connect_timeout": 10}
    )
    DATABASE_URL = raw_db_url
    DB_TYPE = "supabase_postgres"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        DB_DIAGNOSTIC = "connected_via_database_url"
        print("Connected successfully to Supabase PostgreSQL via DATABASE_URL.")
    except Exception as e:
        DB_DIAGNOSTIC = f"postgres_boot_warning: {str(e)}"
        print(f"Warning: Initial ping via DATABASE_URL failed ({e}), will retry on requests.")

if engine is None and SUPABASE_URL.startswith("http") and SUPABASE_KEY:
    DB_TYPE = "supabase_rest"
    if DB_DIAGNOSTIC == "init":
        DB_DIAGNOSTIC = "connected_via_supabase_rest"
    print("Using Supabase REST API (SUPABASE_URL + SUPABASE_KEY) for persistence.")

if engine is None:
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

def _supabase_headers(extra: dict = None) -> dict:
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if SUPABASE_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if extra:
        headers.update(extra)
    return headers

def _save_via_supabase_rest(descricao: str, categoria: str, prioridade: str, justificativa: str):
    url = f"{SUPABASE_URL}/rest/v1/chamados"
    payload = {
        "descricao": descricao,
        "categoria": categoria,
        "prioridade": prioridade,
        "justificativa": justificativa
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_supabase_headers({"Prefer": "return=representation"}),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            row = rows[0] if isinstance(rows, list) and rows else payload
            return {
                "id": row.get("id"),
                "descricao": row.get("descricao", descricao),
                "categoria": row.get("categoria", categoria),
                "prioridade": row.get("prioridade", prioridade),
                "justificativa": row.get("justificativa", justificativa),
                "created_at": str(row.get("created_at", ""))
            }
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        print(f"Supabase REST POST HTTPError ({http_err.code}): {err_body}")
        raise

def _get_via_supabase_rest(limit: int = 50):
    url = f"{SUPABASE_URL}/rest/v1/chamados?select=*&order=id.asc&limit={limit}"
    req = urllib.request.Request(
        url,
        headers=_supabase_headers(),
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            items = [
                {
                    "id": r.get("id"),
                    "descricao": r.get("descricao") or "",
                    "categoria": r.get("categoria") or "Outros",
                    "prioridade": r.get("prioridade") or "Média",
                    "justificativa": r.get("justificativa") or "",
                    "created_at": str(r.get("created_at") or "")
                }
                for r in rows
            ]
            return _sort_chamados(items)[:limit]
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        print(f"Supabase REST GET HTTPError ({http_err.code}): {err_body}")
        raise

def save_chamado(descricao: str, categoria: str, prioridade: str, justificativa: str):
    if DB_TYPE == "supabase_rest":
        return _save_via_supabase_rest(descricao, categoria, prioridade, justificativa)

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
            "descricao": novo_chamado.descricao or "",
            "categoria": novo_chamado.categoria or "Outros",
            "prioridade": novo_chamado.prioridade or "Média",
            "justificativa": novo_chamado.justificativa or "",
            "created_at": str(novo_chamado.created_at or "")
        }
    except Exception as e:
        db.rollback()
        if SUPABASE_URL.startswith("http") and SUPABASE_KEY:
            print(f"SQLAlchemy save failed ({e}), falling back to Supabase REST API.")
            return _save_via_supabase_rest(descricao, categoria, prioridade, justificativa)
        raise
    finally:
        db.close()

def get_recent_chamados(limit: int = 50):
    if DB_TYPE == "supabase_rest":
        return _get_via_supabase_rest(limit)

    db = SessionLocal()
    try:
        chamados = db.query(Chamado).order_by(Chamado.id.asc()).limit(limit).all()
        items = [
            {
                "id": c.id,
                "descricao": c.descricao or "",
                "categoria": c.categoria or "Outros",
                "prioridade": c.prioridade or "Média",
                "justificativa": c.justificativa or "",
                "created_at": str(c.created_at or "")
            }
            for c in chamados
        ]
        return _sort_chamados(items)[:limit]
    except Exception as e:
        if SUPABASE_URL.startswith("http") and SUPABASE_KEY:
            print(f"SQLAlchemy fetch failed ({e}), falling back to Supabase REST API.")
            return _get_via_supabase_rest(limit)
        raise
    finally:
        db.close()
