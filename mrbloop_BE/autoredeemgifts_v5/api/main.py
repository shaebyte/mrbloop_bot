import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
from app.config import ALLOWED_ORIGINS
from app.poller import run_poller
from .routes.accounts import router as accounts_router
from .routes.gift_codes import router as codes_router
from .routes.redeem_attempts import router as redeem_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_poller())
    logger.info("Poller started as background task.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Poller stopped.")


app = FastAPI(title="AutoRedeemGifts API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router)
app.include_router(codes_router)
app.include_router(redeem_router)