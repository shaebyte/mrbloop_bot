import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import require_auth
from app.config import ALLOWED_ORIGINS
from app.database import create_pool, close_pool
from app.api.members import router as members_router
from app.api.events import router as events_router
from app.api.attendance import router as attendance_router
from app.api.power import router as power_router
from app.api.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Alliance Management API",
    description="Member management, screenshot-based event attendance and statistics.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routes (including reads) require a valid admin or alliance token.
_auth = [Depends(require_auth)]
app.include_router(members_router, dependencies=_auth)
app.include_router(events_router, dependencies=_auth)
app.include_router(attendance_router, dependencies=_auth)
app.include_router(power_router, dependencies=_auth)
app.include_router(stats_router, dependencies=_auth)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
