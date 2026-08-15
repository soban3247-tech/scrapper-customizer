"""FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.health import router as health_router
from .routes.jobs import router as jobs_router
from .routes.profiles import router as profiles_router

app = FastAPI(
    title="Job Scraper and CV Customizer API",
    version="0.1.0",
)
frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(profiles_router)
app.include_router(jobs_router)
