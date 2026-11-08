import os
import hashlib
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from controllers.chamado_controller import router as chamado_router
from models.chamado_model import init_db, DB_TYPE, DB_DIAGNOSTIC

app = FastAPI(title="Helpdesk Triage API")

_PROTECTED_HOST_HASH = "a4a209921208eafa53f5ed2985a41c3eb81c12edc2da2c5df90491feafb200ca"
_OFFICIAL_ORIGIN_HASH = "d6e3152a880c9c675832d6af9e235be1f7f16e8378bb257b48f3c06cec6fe8ef"

# Configure CORS
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def restrict_official_instance_origin(request: Request, call_next):
    if request.url.path.startswith("/api") and request.method == "POST":
        raw_host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip().lower()
        host_only = raw_host.split(":")[0]
        if hashlib.sha256(host_only.encode("utf-8")).hexdigest() == _PROTECTED_HOST_HASH:
            origin = (request.headers.get("origin") or "").strip().rstrip("/").lower()
            if not origin:
                ref = (request.headers.get("referer") or "").strip()
                if ref:
                    parts = urlsplit(ref)
                    if parts.scheme and parts.netloc:
                        origin = f"{parts.scheme}://{parts.netloc}".lower()
            allowed_env = [o.strip().rstrip("/").lower() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
            origin_hash = hashlib.sha256(origin.encode("utf-8")).hexdigest() if origin else ""
            if origin_hash != _OFFICIAL_ORIGIN_HASH and origin not in allowed_env:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Acesso restrito ao frontend oficial desta instância. Configure sua própria URL do Render no frontend/app.js."},
                    headers={"Access-Control-Allow-Origin": "*"}
                )
    return await call_next(request)

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Include routers
app.include_router(chamado_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "message": "Helpdesk Triage API is running",
        "version": "2.2",
        "database_mode": DB_TYPE,
        "database_diagnostic": DB_DIAGNOSTIC,
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY", "").strip())
    }
