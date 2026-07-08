import asyncio
import hashlib
import logging
import time

import httpx

from app import database
from app.config import REDEEM_API, REDEEM_SECRET

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
MAX_RATE_LIMIT_ATTEMPTS = 10  # 429 just means "try later" -- give it much more slack than real errors
RETRY_BACKOFF = 5
RATE_LIMIT_BACKOFF = 60
REQUESTS_PER_SECOND = 1.0  # conservative; live-tested threshold was ~2-3 req/s before 429s

_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}


class _TokenBucket:
    """Caps outgoing requests to a steady rate, shared across all concurrent workers."""

    def __init__(self, rate: float):
        self._rate = rate
        self._tokens = 1.0
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self._tokens = min(1.0, self._tokens + (now - self._updated) * self._rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)


_bucket = _TokenBucket(REQUESTS_PER_SECOND)


def _sign(form_str: str) -> str:
    return hashlib.md5((form_str + REDEEM_SECRET).encode()).hexdigest()


def _is_rate_limited(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


async def _login(client: httpx.AsyncClient, player_id: str, api_base: str) -> dict:
    ts = int(time.time() * 1000)
    form_str = f"fid={player_id}&time={ts}"
    body = f"sign={_sign(form_str)}&{form_str}"
    await _bucket.acquire()
    response = await client.post(f"{api_base}/player", headers=_HEADERS, data=body, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def fetch_player_info(player_id: str, api_base: str) -> dict:
    async with httpx.AsyncClient() as client:
        result = await _login(client, player_id, api_base)
    logger.debug("fetch_player_info(%s) raw result: %s", player_id, result)

    if result.get("code") != 0:
        raise ValueError(result.get("msg", "Player not found"))

    return result["data"]


async def redeem_code(client: httpx.AsyncClient, player_id: str, code: str, api_base: str) -> dict:
    await _login(client, player_id, api_base)

    ts = int(time.time() * 1000)
    form_str = f"captcha_code=&cdk={code}&fid={player_id}&time={ts}"
    body = f"sign={_sign(form_str)}&{form_str}"

    await _bucket.acquire()
    response = await client.post(f"{api_base}/gift_code", headers=_HEADERS, data=body, timeout=30.0)
    response.raise_for_status()
    return response.json()


def is_success(response: dict) -> bool:
    if response.get('code') == 0:
        return True
    msg = response.get('msg', '').lower()
    return any(k in msg for k in ('success', 'claimed', 'redeemed'))


def is_already_redeemed(response: dict) -> bool:
    msg = response.get('msg', '').lower()
    return any(k in msg for k in ('already', 'used', 'duplicate', 'received'))


def is_permanent_failure(response: dict) -> bool:
    msg = response.get('msg', '').lower()
    return any(k in msg for k in ('time error', 'same type', 'expired', 'invalid', 'not exist'))


async def _redeem_account(client: httpx.AsyncClient, code: str, player_id: str, name: str) -> None:
    attempt = 0
    rate_limit_attempt = 0
    while True:
        attempt += 1
        try:
            resp = await redeem_code(client, player_id, code, REDEEM_API)

            if is_success(resp) or is_already_redeemed(resp):
                await database.save_attempt(code, player_id, 'success', attempt)
                logger.info("[%s] %s (%s) — success on attempt %d", code, name, player_id, attempt)
                return

            msg = resp.get('msg', '')
            if attempt < MAX_ATTEMPTS and not is_permanent_failure(resp):
                logger.warning(
                    "[%s] %s (%s) — attempt %d failed (%s), retrying...",
                    code, name, player_id, attempt, msg,
                )
                await asyncio.sleep(RETRY_BACKOFF)
            else:
                await database.save_attempt(code, player_id, 'failed', attempt, msg)
                logger.error(
                    "[%s] %s (%s) — failed after %d attempts: %s",
                    code, name, player_id, attempt, msg,
                )
                return

        except Exception as exc:
            if _is_rate_limited(exc):
                rate_limit_attempt += 1
                if rate_limit_attempt < MAX_RATE_LIMIT_ATTEMPTS:
                    logger.warning(
                        "[%s] %s (%s) — rate limited (%d/%d), retrying in %ds...",
                        code, name, player_id, rate_limit_attempt, MAX_RATE_LIMIT_ATTEMPTS, RATE_LIMIT_BACKOFF,
                    )
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    attempt -= 1  # rate limits don't consume the real-error budget
                    continue
                await database.save_attempt(code, player_id, 'error', attempt, str(exc))
                logger.error(
                    "[%s] %s (%s) — gave up after %d rate-limit retries",
                    code, name, player_id, rate_limit_attempt,
                )
                return

            if attempt < MAX_ATTEMPTS:
                logger.warning(
                    "[%s] %s (%s) — attempt %d error (%s), retrying in %ds...",
                    code, name, player_id, attempt, exc, RETRY_BACKOFF,
                )
                await asyncio.sleep(RETRY_BACKOFF)
            else:
                await database.save_attempt(code, player_id, 'error', attempt, str(exc))
                logger.error(
                    "[%s] %s (%s) — error after %d attempts: %s",
                    code, name, player_id, attempt, exc,
                )
                return


async def redeem_all(code: str) -> None:
    await database.cleanup_old_attempts(days=3)
    async with httpx.AsyncClient() as client:
        accounts = await database.get_accounts_to_redeem(code)
        if not accounts:
            logger.info("[%s] No accounts to redeem for.", code)
            return
        logger.info("[%s] Redeeming for %d account(s)...", code, len(accounts))
        await asyncio.gather(
            *[_redeem_account(client, code, acc['player_id'], acc['name']) for acc in accounts]
        )
