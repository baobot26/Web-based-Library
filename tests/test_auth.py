from datetime import datetime, timezone

import bcrypt
import jwt
import pytest
from sqlalchemy import select

from app.config import settings
from app.infrastructure.models import UserModel

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def register(client, email="an@example.com", password="secret123", name="An"):
    return client.post(REGISTER, json={"email": email, "password": password, "name": name})


def login(client, email="an@example.com", password="secret123"):
    return client.post(LOGIN, json={"email": email, "password": password})


def test_register_returns_user(client):
    res = register(client)
    assert res.status_code == 201
    data = res.json()
    assert isinstance(data["id"], int)
    assert data == {"id": data["id"], "email": "an@example.com", "name": "An"}


def test_register_stores_hashed_password(client, db_session):
    register(client, password="secret123")
    user = db_session.scalars(select(UserModel)).one()
    assert user.password_hash != "secret123"
    assert bcrypt.checkpw(b"secret123", user.password_hash.encode())


def test_register_stores_email_lowercase(client):
    res = register(client, email="An@Example.com")
    assert res.status_code == 201
    assert res.json()["email"] == "an@example.com"


def test_register_duplicate_email_is_409(client):
    register(client)
    res = register(client)
    assert res.status_code == 409
    assert res.json()["error"] == {
        "code": "EMAIL_TAKEN",
        "message": "Email an@example.com is already registered",
    }


def test_register_duplicate_email_ignores_case(client):
    register(client, email="an@example.com")
    res = register(client, email="AN@EXAMPLE.COM")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "secret123", "name": "An"},
        {"email": "an@example.com", "password": "short", "name": "An"},
        {"email": "an@example.com", "password": "x" * 73, "name": "An"},
        {"email": "an@example.com", "password": "secret123", "name": ""},
        {"email": "an@example.com", "password": "secret123", "name": "x" * 201},
        {"email": "an@example.com", "password": "secret123"},
    ],
)
def test_register_invalid_input_is_422(client, payload):
    res = client.post(REGISTER, json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_returns_token(client):
    user_id = register(client).json()["id"]
    res = login(client)
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.jwt_expire_minutes * 60
    payload = jwt.decode(data["access_token"], settings.jwt_secret, algorithms=["HS256"])
    assert payload["sub"] == str(user_id)
    remaining = payload["exp"] - datetime.now(timezone.utc).timestamp()
    assert settings.jwt_expire_minutes * 60 - 30 < remaining <= settings.jwt_expire_minutes * 60


def test_login_email_ignores_case(client):
    register(client, email="an@example.com")
    res = login(client, email="An@Example.COM")
    assert res.status_code == 200


@pytest.mark.parametrize(
    "email, password",
    [
        ("an@example.com", "wrong-password"),
        ("nobody@example.com", "secret123"),
        ("an@example.com", "x" * 73),
    ],
)
def test_login_bad_credentials_is_401(client, email, password):
    register(client)
    res = login(client, email=email, password=password)
    assert res.status_code == 401
    assert res.json()["error"] == {
        "code": "INVALID_CREDENTIALS",
        "message": "Wrong email or password",
    }


def test_login_invalid_email_is_422(client):
    res = login(client, email="not-an-email")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
