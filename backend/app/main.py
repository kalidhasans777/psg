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
app.add_exception_