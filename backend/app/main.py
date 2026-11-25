from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401
from app.routers import admin, ai, appointments, auth, doctor, patients, reports, visits, voice
from app.seed import seed_database

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema exists and synthetic demo records are seeded
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="MEDORA API",
    description="MEDORA – One Patient. One Permanent ID. A Complete Medical Journey. Centralized Healthcare & AI Medical Summarization API.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow all origins for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "database_dialect": "postgresql" if settings.is_postgres else "sqlite-dev-fallback",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "cloud_voice_configured": bool(settings.GOOGLE_CLOUD_SPEECH_API_KEY or settings.AZURE_SPEECH_KEY),
    }


app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(voice.router)
app.include_router(reports.router)
app.include_router(ai.router)
app.include_router(doctor.router)
app.include_router(admin.router)
app.include_router(appointments.router)