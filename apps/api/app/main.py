from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .config import get_settings

settings = get_settings()
app = FastAPI(title="Revenue Incident Commander API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", phase="0-foundation")

@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {"service": "api", "status": "configured", "implementation": "foundation-only"}
