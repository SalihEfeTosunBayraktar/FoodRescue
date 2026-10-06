from datetime import timedelta

from app.core.clock import utcnow
from app.modules.reservation import service as reservations


# Tekrarı azaltan küçük yardımcı.
def _reserve(client, headers, food_id, portions=1):
    return client.post("/api/v1/reservations", json={"food_id": food_id, "portions": portions}, headers=headers)


# Uçtan uca mutlu yol: rezerve et -> stok düşer -> bağışçı gelen listede sır görmez -> PIN ile
# teslim -> aynı kod ikinci kez çalışmaz.
def test_full_pickup_flow_with_qr_and_pin(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor, portions_total=10)

    res = _reserve(client, student, food["id"], portions=2)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "PENDING" and len(body["pin"]) == 6 and body["qr_svg"].lstrip().startswith("<?xml")
    assert client.get(f"/api/v1/foods/{food['id']}").json()["portions_left"] == 8

    incoming = client.get("/api/v1/reservations/incoming", headers=donor).json()
    assert incoming[0]["beneficiary_label"].endswith(".") and "pin" not in incoming[0]

    done = client.post("/api/v1/reservations/verify", json={"code": body["pin"]}, headers=donor)
    assert done.status_code == 200 and done.json()["portions"] == 2
    again = client.post("/api/v1/reservations/verify", json={"code": body["pin"]}, headers=donor)
    assert again.status_code == 404  # a code works exactly once
    mine = client.get("/api/v1/reservations/mine", headers=student).json()[0]
    assert mine["status"] == "COLLECTED" and mine["pin"] is None and mine["qr_svg"] is None


# QR içeriği ('FR:<token>') ile de doğrulama çalışır.
def test_qr_payload_verification(client, actors, make_food, db):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor)
    res = _reserve(client, student, food["id"]).json()
    from app.modules.reservation.models import Reservation
    token = db.get(Reservation, res["id"]).qr_token
    assert client.post("/api/v1/reservations/verify", json={"code": f"FR:{token}"}, headers=donor).status_code == 200


# Sahiplik: başka işletmenin geçerli PIN'i bile 404 verir (rezervasyon hiç görünmez).
def test_other_donor_cannot_verify_someone_elses_reservation(client, actors, make_food):
    admin = actors.admin()
    _, owner = actors.donor(admin)
    _, intruder = actors.donor(admin)
    _, student = actors.beneficiary()
    res = _reserve(client, student, make_food(owner)["id"]).json()
    assert client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=intruder).status_code == 404
    assert client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=owner).status_code == 200


# Hız sınırı: 5 hatalı denemeden sonra doğru PIN de 429 alır.
def test_pin_guessing_is_locked_out(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    res = _reserve(client, student, make_food(donor)["id"]).json()
    wrong = "000000" if res["pin"] != "000000" else "111111"
    codes = [wrong] * 5
    assert [client.post("/api/v1/reservations/verify", json={"code": c}, headers=donor).status_code for c in codes] == [404] * 5
    # Even the correct PIN is refused while locked.
    assert client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=donor).status_code == 429


# Rol-kategori eşleşmesi ve kişi başı porsiyon sınırı.
def test_category_and_portion_rules(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    _, shelter = actors.shelter(admin)
    human = make_food(donor, max_per_person=2)
    animal = make_food(donor, category="ANIMAL", title="Kuru ekmek")
    assert _reserve(client, student, animal["id"]).status_code == 403
    assert _reserve(client, shelter, human["id"]).status_code == 403
    assert _reserve(client, shelter, animal["id"]).status_code == 201
    assert _reserve(client, student, human["id"], portions=3).status_code == 422
    assert client.post("/api/v1/reservations", json={"food_id": human["id"]}).status_code == 401
    assert client.post("/api/v1/reservations", json={"food_id": human["id"]}, headers=donor).status_code == 403


# Aynı anda en fazla 2 aktif rezervasyon; tükenmiş ilan 409 verir.
def test_active_reservation_limit_and_sold_out(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, a = actors.beneficiary()
    _, b = actors.beneficiary()
    foods = [make_food(donor, title=f"Yemek {i}", portions_total=1, max_per_person=1) for i in range(3)]
    assert _reserve(client, a, foods[0]["id"]).status_code == 201
    assert _reserve(client, a, foods[1]["id"]).status_code == 201
    assert _reserve(client, a, foods[2]["id"]).status_code == 409  # limit of 2 active
    assert _reserve(client, b, foods[0]["id"]).status_code == 409  # already taken


# İptalde porsiyonlar stoğa döner; yalnızca sahibi iptal eder; iptal edileni tekrar iptal etmek 409.
def test_cancel_returns_portions_and_only_owner_may_cancel(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, a = actors.beneficiary()
    _, b = actors.beneficiary()
    food = make_food(donor, portions_total=4)
    res = _reserve(client, a, food["id"], 2).json()
    assert client.post(f"/api/v1/reservations/{res['id']}/cancel", headers=b).status_code == 403
    assert client.post(f"/api/v1/reservations/{res['id']}/cancel", headers=a).json()["status"] == "CANCELLED"
    assert client.get(f"/api/v1/foods/{food['id']}").json()["portions_left"] == 4
    assert client.post(f"/api/v1/reservations/{res['id']}/cancel", headers=a).status_code == 409


# Süre dolumu: teslim alınmayan rezervasyonun porsiyonları serbest kalır.
def test_expired_reservation_releases_portions(app, client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor, portions_total=3)
    _reserve(client, student, food["id"], 2)
    with app.state.db.session() as session:
        assert reservations.expire_due(session, utcnow() + timedelta(hours=2)) == 1
    assert client.get(f"/api/v1/foods/{food['id']}").json()["portions_left"] == 3
    assert client.get("/api/v1/reservations/mine", headers=student).json()[0]["status"] == "EXPIRED"


# Olay zinciri: ilan kaldırılır -> reservation dinleyicisi iptal eder -> notification yararlanıcıya
# haber verir. Üç modülün birlikte çalıştığını gösterir.
def test_cancelling_food_cancels_pending_reservations(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor)
    _reserve(client, student, food["id"])
    client.delete(f"/api/v1/foods/{food['id']}", headers=donor)
    assert client.get("/api/v1/reservations/mine", headers=student).json()[0]["status"] == "CANCELLED"
    notes = client.get("/api/v1/notifications", headers=student).json()
    assert any(n["kind"] == "reservation.cancelled.beneficiary" for n in notes["items"])
