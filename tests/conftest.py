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

# Tüm test hesaplarının parolası.
PASSWORD = "Test12345"


# FIXTURE: testlere hazır nesne sağlayan fonksiyon. Test, parametre adıyla ister (def test_x(app):
# ...) ve pytest otomatik üretip verir. Bu fixture her test için SIFIRDAN bir uygulama kurar: bellek
# içi veritabanı kullandığından testler birbirini etkilemez ve diske hiçbir şey yazılmaz.
@pytest.fixture()
def app(tmp_path):
    # Ayarları testlere göre ezeriz: bellek içi SQLite, geçici yükleme klasörü ve kapalı bakım
    # döngüsü (test zamanı kendisi ilerletir).
    settings = replace(
        load_settings(secret_key="test-secret-key-with-at-least-32-bytes!"),
        database_url="sqlite://",
        upload_dir=tmp_path / "uploads",
        maintenance_interval_seconds=0,
    )
    return create_app(settings)


# TestClient: gerçek bir sunucu başlatmadan HTTP isteklerini uygulamaya doğrudan gönderir; hızlıdır.
@pytest.fixture()
def client(app):
    return TestClient(app)


# Veritabanına doğrudan erişmek gereken testler için oturum (örn. yönetici hesabı eklemek).
@pytest.fixture()
def db(app):
    with app.state.db.session() as session:
        yield session


# Test kolaylaştırıcı: kullanıcıları GERÇEK API'den (kayıt + giriş) oluşturur ve yetki başlıklarını
# döndürür. Böylece testler hem kayıt hem giriş akışını da dolaylı sınar.
class Actors:
    """Creates accounts through the real API and returns auth headers."""

    def __init__(self, client: TestClient, db) -> None:
        self.client, self.db = client, db
        self._n = 0

    # Girişi yapıp 'Authorization: Bearer ...' başlığını üretir.
    def _headers(self, email: str) -> dict[str, str]:
        res = self.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    # Yöneticiyi ORM ile doğrudan ekler: kayıt ekranından yönetici oluşturulamadığı için başka yolu
    # yoktur.
    def admin(self) -> dict[str, str]:
        self.db.add(
            User(email="admin@t.test", password_hash=hash_password(PASSWORD), full_name="Admin Root",
                 role=UserRole.ADMIN, status=AccountStatus.ACTIVE)
        )
        self.db.commit()
        return self._headers("admin@t.test")

    # Verilen rolle kayıt olur; her çağrıda benzersiz e-posta üretir.
    def register(self, role: str, **extra) -> tuple[dict, dict[str, str]]:
        self._n += 1
        email = f"{role.lower()}{self._n}@t.test"
        body = {"email": email, "password": PASSWORD, "full_name": f"Test {role.title()} {self._n}", "role": role, **extra}
        res = self.client.post("/api/v1/auth/register", json=body)
        assert res.status_code == 201, res.text
        return res.json(), self._headers(email)

    # Bağışçıyı kayıt eder ve (approve=True ise) yönetici onayını da API'den verir.
    def donor(self, admin_headers: dict, lat: float = 39.75, lon: float = 37.01, approve: bool = True):
        user, headers = self.register(
            "DONOR", organization_name=f"Isletme {self._n}", license_number=f"LIC-{self._n}",
            address="Test Cd. 1", latitude=lat, longitude=lon,
        )
        if approve:
            res = self.client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=admin_headers)
            assert res.status_code == 200, res.text
        return user, headers

    # Yararlanıcı hemen aktif olur, onay gerekmez.
    def beneficiary(self):
        return self.register("BENEFICIARY")

    # Barınak da onay ister.
    def shelter(self, admin_headers: dict):
        user, headers = self.register("SHELTER", organization_name="Barinak", license_number="SHL-1", address="Yol 1")
        self.client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=admin_headers)
        return user, headers


# Actors yardımcısını testlere verir.
@pytest.fixture()
def actors(client, db) -> Actors:
    return Actors(client, db)


# Geçerli bir ilan gövdesi üretir; test yalnızca değiştirmek istediği alanı geçersiz kılar
# (`**overrides`). Böylece her testte yüz satır JSON yazılmaz.
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


# make_food: ilanı oluşturur ve oluştuğunu doğrular (201), sonra yanıtı verir.
@pytest.fixture()
def make_food(client):
    def _make(headers: dict, **overrides) -> dict:
        res = client.post("/api/v1/foods", json=food_payload(**overrides), headers=headers)
        assert res.status_code == 201, res.text
        return res.json()

    return _make
