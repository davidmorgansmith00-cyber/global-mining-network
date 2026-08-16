from __future__ import annotations

import base64
import hashlib
import hmac
import os


PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16


def hash_secret(secret: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}"
        f"${base64.b64encode(salt).decode('ascii')}"
        f"${base64.b64encode(digest).decode('ascii')}"
    )


def verify_secret(secret: str, hashed_value: str) -> bool:
    algorithm, iterations_text, salt_text, digest_text = hashed_value.split("$", maxsplit=3)
    if algorithm != "pbkdf2_sha256":
        raise ValueError("Unsupported hash algorithm")

    iterations = int(iterations_text)
    salt = base64.b64decode(salt_text.encode("ascii"))
    expected_digest = base64.b64decode(digest_text.encode("ascii"))
    candidate_digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)