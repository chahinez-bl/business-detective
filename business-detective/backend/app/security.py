import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings
from .errors import ApiError

ALGO = "HS256"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def check_password_rules(pw: str) -> None:
    if len(pw) < 8:
        raise ApiError(422, "Your password must have at least 8 characters.")
    if len(pw.encode()) > 72:
        raise ApiError(422, "Your password is too long (maximum 72 bytes).")
    if pw.isdigit() or pw.isalpha():
        raise ApiError(422, "Please mix letters with numbers or symbols in your password.")


def create_token(user_id: int) -> tuple[str, datetime]:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.token_ttl_minutes)
    tok = jwt.encode({"sub": str(user_id), "jti": uuid.uuid4().hex, "exp": exp, "iat": datetime.now(timezone.utc)}, s.secret_key, algorithm=ALGO)
    return tok, exp


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise ApiError(401, "Your session has expired. Please sign in again.")


# --- login throttling (in-memory, per process; put a shared store / proxy rate limit in front when running several instances)
_fails: dict[str, list[float]] = {}
WINDOW = 15 * 60


def throttle_check(key: str) -> None:
    now = time.time()
    hits = [t for t in _fails.get(key, []) if now - t < WINDOW]
    _fails[key] = hits
    if len(hits) >= get_settings().login_max_failures:
        raise ApiError(429, "Too many failed sign-in attempts. Please wait a few minutes and try again.")


def throttle_fail(key: str) -> None:
    _fails.setdefault(key, []).append(time.time())


def throttle_reset(key: str | None = None) -> None:
    _fails.clear() if key is None else _fails.pop(key, None)
