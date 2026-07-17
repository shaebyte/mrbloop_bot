import asyncio
import hashlib
import logging
import random
import time

import httpx

from app import database
from app.config import REDEEM_API, REDEEM_SECRET

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
MAX_RATE_LIMIT_ATTEMPTS = 10  # 429 just means "try later" -- give it much more slack than real errors
RETRY_BACKOFF = 5
RATE_LIMIT_BACKOFF = 60
RATE_LIMIT_BACKOFF_JITTER = 0.3  # +/-30%, decorrelates accounts rate-limited in the same burst

# AIMD tuning for the shared token bucket. Live-tested sustained threshold is
# ~0.5 req/s (the API appears to enforce a rolling-window quota, not a flat
# per-second cap) -- start there, decrease hard on any 429, probe back up slowly.
RATE_MIN = 0.2
RATE_MAX = 1.0
RATE_START = 0.5
RATE_DECREASE_FACTOR = 0.5
RATE_INCREASE_STEP = 0.05
RATE_INCREASE_AFTER_QUIET = 20.0  # seconds without a 429 before probing the rate up

# The server tracks "logged in" state per fid (confirmed live: still valid 90s
# after /player, and NOT shared across different fids on the same client). A
# retry within this window can skip the redundant /player call and go
# straight to /gift_code. Kept below the confirmed-valid 90s with margin.
LOGIN_CACHE_TTL = 80.0

_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}


class _AdaptiveTokenBucket:
    """Caps outgoing requests to a shared, self-tuning rate (AIMD).

    A 429 from any concurrent worker immediately halves the rate for everyone;
    the rate only creeps back up after a sustained quiet period. This avoids
    the thundering-herd pattern where individual workers back off but the
    aggregate request rate never actually drops below the server's limit.
    """

    def __init__(self, start_rate: float, min_rate: float, max_rate: float):
        self._rate = start_rate
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._tokens = 1.0
        self._updated = time.monotonic()
        self._last_rate_limit = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self._maybe_increase(now)
                self._tokens = min(1.0, self._tokens + (now - self._updated) * self._rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)

    def _maybe_increase(self, now: float) -> None:
        if self._rate < self._max_rate and now - self._last_rate_limit >= RATE_INCREASE_AFTER_QUIET:
            old_rate = self._rate
            self._rate = min(self._max_rate, self._rate + RATE_INCREASE_STEP)
            self._last_rate_limit = now  # reset the quiet timer for the next step
            if self._rate != old_rate:
                logger.info("Rate limiter: no 429s for %.0fs, probing rate up to %.2f req/s", RATE_INCREASE_AFTER_QUIET, self._rate)

    async def on_rate_limited(self) -> None:
        async with self._lock:
            old_rate = self._rate
            self._rate = max(self._min_rate, self._rate * RATE_DECREASE_FACTOR)
            self._last_rate_limit = time.monotonic()
            if self._rate != old_rate:
                logger.warning("Rate limiter: 429 received, dropping rate %.2f -> %.2f req/s", old_rate, self._rate)


_bucket = _AdaptiveTokenBucket(RATE_START, RATE_MIN, RATE_MAX)


def _rate_limit_backoff_seconds(retry_after: str | None) -> float:
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    jitter = RATE_LIMIT_BACKOFF * RATE_LIMIT_BACKOFF_JITTER
    return RATE_LIMIT_BACKOFF + random.uniform(-jitter, jitter)


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


class _LoginSession:
    """Tracks whether an account's server-side login is still fresh enough to skip re-login.

    The server ties "logged in" state to the fid, not to the client/cookies,
    and it stays valid well past our retry windows -- see LOGIN_CACHE_TTL.
    """

    def __init__(self):
        self._logged_in_at = 0.0

    def is_fresh(self) -> bool:
        return time.monotonic() - self._logged_in_at < LOGIN_CACHE_TTL

    def mark_logged_in(self) -> None:
        self._logged_in_at = time.monotonic()


async def _submit_gift_code(client: httpx.AsyncClient, player_id: str, code: str, api_base: str) -> dict:
    ts = int(time.time() * 1000)
    form_str = f"captcha_code=&cdk={code}&fid={player_id}&time={ts}"
    body = f"sign={_sign(form_str)}&{form_str}"
    await _bucket.acquire()
    response = await client.post(f"{api_base}/gift_code", headers=_HEADERS, data=body, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def redeem_code(
    client: httpx.AsyncClient, player_id: str, code: str, api_base: str, session: _LoginSession,
) -> dict:
    if not session.is_fresh():
        await _login(client, player_id, api_base)
        session.mark_logged_in()
    return await _submit_gift_code(client, player_id, code, api_base)


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
    session = _LoginSession()
    attempt = 0
    rate_limit_attempt = 0

    while True:
        attempt += 1
        try:
            resp = await redeem_code(client, player_id, code, REDEEM_API, session)
        except Exception as exc:
            if not _is_rate_limited(exc):
                await _retry_or_give_up_on_error(code, player_id, name, attempt, exc)
                if attempt >= MAX_ATTEMPTS:
                    return
                continue

            await _bucket.on_rate_limited()
            rate_limit_attempt += 1
            if rate_limit_attempt >= MAX_RATE_LIMIT_ATTEMPTS:
                await database.save_attempt(code, player_id, 'error', attempt, str(exc))
                logger.error(
                    "[%s] %s (%s) — gave up after %d rate-limit retries",
                    code, name, player_id, rate_limit_attempt,
                )
                return

            backoff = _rate_limit_backoff_seconds(exc.response.headers.get('Retry-After'))
            logger.warning(
                "[%s] %s (%s) — rate limited (%d/%d), retrying in %.0fs...",
                code, name, player_id, rate_limit_attempt, MAX_RATE_LIMIT_ATTEMPTS, backoff,
            )
            await asyncio.sleep(backoff)
            attempt -= 1  # rate limits don't consume the real-error budget
            continue

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
            continue

        await database.save_attempt(code, player_id, 'failed', attempt, msg)
        logger.error(
            "[%s] %s (%s) — failed after %d attempts: %s",
            code, name, player_id, attempt, msg,
        )
        return


async def _retry_or_give_up_on_error(code: str, player_id: str, name: str, attempt: int, exc: Exception) -> None:
    """Logs a non-rate-limit error and persists it once the retry budget is exhausted."""
    if attempt < MAX_ATTEMPTS:
        logger.warning(
            "[%s] %s (%s) — attempt %d error (%s), retrying in %ds...",
            code, name, player_id, attempt, exc, RETRY_BACKOFF,
        )
        await asyncio.sleep(RETRY_BACKOFF)
        return

    await database.save_attempt(code, player_id, 'error', attempt, str(exc))
    logger.error(
        "[%s] %s (%s) — error after %d attempts: %s",
        code, name, player_id, attempt, exc,
    )


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
