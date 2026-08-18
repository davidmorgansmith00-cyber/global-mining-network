from __future__ import annotations

from base64 import b32decode
import hashlib
import hmac
import struct
import time


def verify_totp_code(*, secret: str, code: str, now: int | None = None, period: int = 30, digits: int = 6) -> bool:
    normalized_code = code.strip()
    if len(normalized_code) != digits or not normalized_code.isdigit():
        return False
    timestamp = int(time.time()) if now is None else int(now)
    for drift in (-1, 0, 1):
        if _generate_totp(secret=secret, counter=(timestamp // period) + drift, digits=digits) == normalized_code:
            return True
    return False


def _generate_totp(*, secret: str, counter: int, digits: int) -> str:
    padded_secret = secret.strip().replace(" ", "").upper()
    key = b32decode(padded_secret + "=" * (-len(padded_secret) % 8), casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)
