from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 64


@dataclass(slots=True)
class SessionData:
    user_id: int
    email: str


_signer = URLSafeSerializer(settings.secret_key, salt="workspace-session")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LEN,
    )
    return "scrypt${}${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        KEY_LEN,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, n_str, r_str, p_str, key_len_str, salt_b64, digest_b64 = encoded.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_str),
            r=int(r_str),
            p=int(p_str),
            dklen=int(key_len_str),
        )
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def create_session_cookie(user_id: int, email: str) -> str:
    return _signer.dumps({"user_id": user_id, "email": email})


def read_session_cookie(token: str | None) -> SessionData | None:
    if not token:
        return None
    try:
        payload = _signer.loads(token)
        return SessionData(user_id=int(payload["user_id"]), email=str(payload["email"]))
    except (BadSignature, KeyError, ValueError, TypeError):
        return None
