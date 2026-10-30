from datetime import timedelta
import time
import uuid

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "invalid_hash_string") is False


def test_jwt_create_and_decode_valid() -> None:
    user_id = uuid.uuid4()
    role = "ADMIN"

    token = create_access_token(subject=user_id, role=role)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_jwt_expired_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(
        subject=user_id,
        role="STUDENT",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_jwt_tampered_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, role="STUDENT")

    # Alter a character in the signature
    header, payload, signature = token.split(".")
    tampered_sig = ("B" if signature[0] != "B" else "C") + signature[1:]
    tampered_token = f"{header}.{payload}.{tampered_sig}"

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(tampered_token)


def test_jwt_signed_with_wrong_key() -> None:
    user_id = uuid.uuid4()
    fake_token = jwt.encode(
        {"sub": str(user_id), "role": "ADMIN", "iat": int(time.time()), "exp": int(time.time()) + 3600},
        "wrong-secret-key-that-is-at-least-32-bytes-long!",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(fake_token)
