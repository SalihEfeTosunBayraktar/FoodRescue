"""Shared fixtures. Every test gets its own in-memory app, so tests never affect each other."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config.settings import load_settings
from app.core.clock import utcnow
from app.core.security import hash_password
from app.main import create_app
from app.modules.identity.models import AccountStatus, User, UserRole

PASSWORD = "Test12345"


@pytest.fixture()
def app(tmp_path):
    settings = replace(
        load_settings(secret_key="test-secret-key-with-at-least-32-bytes!"),
        database_url="sqlite://",
        upload_dir=tmp_path / "uploads",
        maintenance_interval_seconds=0,
    )
    return create_app(settings)


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def db(app):
    with app.state.db.session() as session:
        yield session


class Actors:
    """Creates accounts through the real API and returns auth headers."""

    def __init__(self, client: TestClient, db) -> None:
        self.client, self.db = client, db
        self._n = 0

    def _headers(self, email: str) -> dict[str, str]:
        res = self.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    def admin(self) -> dict[str, str]:
        self.db.add(
            User(email="admin@t.test", password_hash=hash_password(PASSWORD), full_name="Admin Root",
                 role=UserRole.ADMIN, status=AccountStatus.ACTIVE)
        )
        self.db.commit()
        return self._headers("admin@t.test")

    def register(self, role: str, **extra) -> tuple[dict, dict[str, str]]:
        self._n += 1
        email = f"{role.lower()}{self._n}@t.test"
        body = {"email": email, "password": PASSWORD, "full_name": f"Test {role.title()} {self._n}", "role": role, **extra}
        res = self.client.post("/api/v1/auth/register", json=body)
        assert res.status_code == 201, res.text
        return res.json(), self._headers(email)

    def donor(self, admin_headers: dict, lat: float = 39.75, lon: float = 37.01, approve: bool = True):
        user, headers = self.register(
            "DONOR", organization_name=f"Isletme {self._n}", license_number=f"LIC-{self._n}",
            address="Test Cd. 1", latitude=lat, longitude=lon,
        )
        if approve:
            res = self.client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=admin_headers)
            assert res.status_code == 200, res.text
        return user, headers

    def beneficiary(self):
        return self.register("BENEFICIARY")

    def shelter(self, admin_headers: dict):
        user, headers = self.register("SHELTER", organization_name="Barinak", license_number="SHL-1", address="Yol 1")
        self.client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=admin_headers)
        return user, headers


@pytest.fixture()
def actors(client, db) -> Actors:
    return Actors(client, db)


def food_payload(**overrides) -> dict:
    body = {
        "title": "Mercimek corbasi",
        "portions_total": 10,
        "max_per_person": 2,
        "category": "HUMAN",
        "storage": "HOT",
        "pickup_until": (utcnow() + timedelta(hours=3)).isoformat(),
        "hygiene_confirmed": True,
    }
    return {**body, **overrides}


@pytest.fixture()
def make_food(client):
    def _make(headers: dict, **overrides) -> dict:
        res = client.post("/api/v1/foods", json=food_payload(**overrides), headers=headers)
        assert res.status_code == 201, res.text
        return res.json()

    return _make
