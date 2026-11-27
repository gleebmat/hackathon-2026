"""Password hashing and cookie sessions. Standard library only."""

import hashlib
import hmac
import os
import secrets

EMAIL_DOMAIN = "@edu.aau.at"
MIN_PASSWORD = 4
COOKIE = "session"
ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return hmac.compare_digest(actual.hex(), digest)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def valid_email(email: str) -> bool:
    local = email.removesuffix(EMAIL_DOMAIN)
    return email.endswith(EMAIL_DOMAIN) and local != "" and "@" not in local and " " not in local
