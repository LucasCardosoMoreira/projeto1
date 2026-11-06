import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.chamado_controller import router as chamado_router
from models.chamado_model import init_db

app = FastAPI(title="Helpdesk Triage API")

# Configure CORS
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "*"  # Allows all origins for now. In production, specify your frontend URL here.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Include routers
app.include_router(chamado_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Helpdesk Triage API is running"}
