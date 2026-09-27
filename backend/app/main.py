from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="SatQuery AI",
    description="Agentic vision-language assistant for remote-sensing imagery (PS 26167).",
    version="0.1.0",
)

# CORS: permissive for local dev only. Tighten via ALLOWED_ORIGINS env var
# before any real deployment — see README "Security".
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
