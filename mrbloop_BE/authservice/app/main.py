import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ALLOWED_ORIGINS
from app.database import create_pool, close_pool
from app.api.auth import router as auth_router
from app.api.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Auth Service",
    description="Shared login + user/role management for the mrbloop backends.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounted at root, not prefix="/auth": nginx.conf's `/api/auth/` location
# strips that prefix before proxying here, so /api/auth/login must land on
# this service's plain /login. Keep in sync with mrbloop_FE/nginx.conf.
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
