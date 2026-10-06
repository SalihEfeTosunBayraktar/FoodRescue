import threading
from datetime import timedelta

from app.core.clock import utcnow
from app.modules.inventory import service as inventory
from tests.conftest import food_payload


# İş kuralı: hijyen beyanı olmadan ilan açılamaz.
def test_hygiene_confirmation_is_mandatory(client, actors):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    res = client.post("/api/v1/foods", json=food_payload(hygiene_confirmed=False), headers=donor)
    assert res.status_code == 422


# Zaman kuralları: geçmiş ve 24 saatten uzak tarihler reddedilir.
def test_pickup_time_must_be_future_and_within_limit(client, actors):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    past = client.post("/api/v1/foods", json=food_payload(pickup_until=(utcnow() - timedelta(minutes=1)).isoformat()), headers=donor)
    far = client.post("/api/v1/foods", json=food_payload(pickup_until=(utcnow() + timedelta(hours=48)).isoformat()), headers=donor)
    assert past.status_code == 422 and far.status_code == 422


# Liste herkese açık; kategori ve arama süzgeçleri çalışır.
def test_public_listing_needs_no_login_and_filters_by_category(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    make_food(donor, title="Insan yemegi")
    make_food(donor, title="Hayvan yemegi", category="ANIMAL")
    assert len(client.get("/api/v1/foods").json()) == 2
    animal = client.get("/api/v1/foods", params={"category": "ANIMAL"}).json()
    assert [f["title"] for f in animal] == ["Hayvan yemegi"]
    assert client.get("/api/v1/foods", params={"q": "Insan"}).json()[0]["title"] == "Insan yemegi"


# Haversine ile sıralama ve yarıçap süzgeci. Sivas içinde yakın ve uzak iki işletme kullanılır.
def test_listing_sorts_by_distance_and_applies_radius(client, actors, make_food):
    admin = actors.admin()
    _, near = actors.donor(admin, lat=39.750, lon=37.015)
    _, far = actors.donor(admin, lat=39.900, lon=37.300)
    make_food(near, title="Yakin")
    make_food(far, title="Uzak")
    ranked = client.get("/api/v1/foods", params={"lat": 39.7505, "lon": 37.0150}).json()
    assert [f["title"] for f in ranked] == ["Yakin", "Uzak"]
    assert ranked[0]["distance_km"] < ranked[1]["distance_km"]
    within = client.get("/api/v1/foods", params={"lat": 39.7505, "lon": 37.0150, "radius_km": 5}).json()
    assert [f["title"] for f in within] == ["Yakin"]


# Sahiplik: başkasının ilanı düzenlenemez ve kaldırılamaz.
def test_only_owner_can_edit_or_cancel(client, actors, make_food):
    admin = actors.admin()
    _, owner = actors.donor(admin)
    _, stranger = actors.donor(admin)
    food = make_food(owner)
    assert client.patch(f"/api/v1/foods/{food['id']}", json={"title": "Hijack"}, headers=stranger).status_code == 403
    assert client.delete(f"/api/v1/foods/{food['id']}", headers=stranger).status_code == 403
    assert client.patch(f"/api/v1/foods/{food['id']}", json={"title": "Yeni ad"}, headers=owner).json()["title"] == "Yeni ad"
    assert client.delete(f"/api/v1/foods/{food['id']}", headers=owner).json()["status"] == "CANCELLED"
    assert client.get("/api/v1/foods").json() == []


# Güvenlik: uzantısı .png olan ama içeriği betik olan dosya reddedilir; uzantısı .txt olan ama
# içeriği PNG olan kabul edilir. Yani karar içeriğe göredir.
def test_photo_upload_checks_content_not_filename(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    food = make_food(donor)
    url = f"/api/v1/foods/{food['id']}/photo"
    fake = client.post(url, files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")}, headers=donor)
    assert fake.status_code == 415
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    ok = client.post(url, files={"file": ("anything.txt", png, "text/plain")}, headers=donor)
    assert ok.status_code == 200 and ok.json()["photo_url"].endswith(".png")
    assert client.get(ok.json()["photo_url"]).status_code == 200


# EŞZAMANLILIK: 5 porsiyon için 12 thread aynı anda 1'er porsiyon almaya çalışır; tam 5'i başarılı
# olmalı. Atomik UPDATE yoksa bu test rastgele başarısız olurdu. Gerçek dosya veritabanı kullanılır,
# çünkü bellek içi veritabanı tek bağlantıyı paylaşır ve yarışı gerçekçi sınamaz.
def test_take_portions_is_atomic_under_concurrency(tmp_path):
    """Uses a real SQLite file: each thread gets its own connection, like the running server."""
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app.config.settings import load_settings
    from app.main import create_app
    from tests.conftest import Actors

    settings = replace(
        load_settings(secret_key="test-secret-key-with-at-least-32-bytes!"),
        database_url=f"sqlite:///{(tmp_path / 'race.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        maintenance_interval_seconds=0,
    )
    app = create_app(settings)
    client = TestClient(app)
    with app.state.db.session() as setup_session:
        actors = Actors(client, setup_session)
        admin = actors.admin()
        _, donor = actors.donor(admin)
    food = client.post("/api/v1/foods", json=food_payload(portions_total=5, max_per_person=1), headers=donor).json()
    results: list[bool] = []

    def worker():
        with app.state.db.session() as session:
            try:
                inventory.take_portions(session, food["id"], 1)
                session.commit()
                results.append(True)
            except Exception:
                session.rollback()
                results.append(False)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 5
    assert client.get(f"/api/v1/foods/{food['id']}").json()["portions_left"] == 0
    app.state.db.engine.dispose()


# Zamanlı iş: gelecekteki bir saat verip süresi dolmuş durumu BEKLEMEDEN sınarız (zamanı parametre
# yapmanın faydası).
def test_expiry_job_marks_overdue_food(app, client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    make_food(donor)
    with app.state.db.session() as session:
        assert inventory.expire_due(session, utcnow() + timedelta(hours=4)) == 1
    assert client.get("/api/v1/foods/1").json()["status"] == "EXPIRED"
