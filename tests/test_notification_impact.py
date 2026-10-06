from tests.conftest import food_payload


def _reserve(client, headers, food_id):
    return client.post("/api/v1/reservations", json={"food_id": food_id, "portions": 1}, headers=headers)


def test_notifications_follow_the_reservation_lifecycle(client, actors, make_food):
    admin = actors.admin()
    donor_user, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor)
    res = _reserve(client, student, food["id"]).json()

    donor_inbox = client.get("/api/v1/notifications", headers=donor).json()
    assert donor_inbox["unread"] >= 1
    assert any(n["kind"] == "reservation.created.donor" for n in donor_inbox["items"])

    client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=donor)
    student_inbox = client.get("/api/v1/notifications", headers=student).json()
    assert any(n["kind"] == "reservation.collected.beneficiary" for n in student_inbox["items"])

    first = donor_inbox["items"][0]
    assert client.post(f"/api/v1/notifications/{first['id']}/read", headers=donor).json()["read_at"]
    assert client.post("/api/v1/notifications/read-all", headers=donor).status_code == 200
    assert client.get("/api/v1/notifications", headers=donor).json()["unread"] == 0


def test_notifications_are_private(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    _reserve(client, student, make_food(donor)["id"])
    note_id = client.get("/api/v1/notifications", headers=donor).json()["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{note_id}/read", headers=student).status_code == 404


def test_approval_notifies_the_applicant(client, actors):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    kinds = [n["kind"] for n in client.get("/api/v1/notifications", headers=donor).json()["items"]]
    assert "account.approved" in kinds


def test_public_summary_counts_only_collected_pickups(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    food = make_food(donor, portions_total=10)
    pending = _reserve(client, student, food["id"]).json()
    before = client.get("/api/v1/impact/summary").json()
    assert before["portions_rescued"] == 0 and before["active_donors"] == 1 and before["foods_available"] == 1
    client.post("/api/v1/reservations/verify", json={"code": pending["pin"]}, headers=donor)
    after = client.get("/api/v1/impact/summary").json()
    assert after["portions_rescued"] == 1 and after["pickups_completed"] == 1
    mine = client.get("/api/v1/impact/mine", headers=donor).json()
    assert mine["portions_rescued"] == 1 and mine["foods_published"] == 1


def test_three_complaints_suspend_the_donor_and_cancel_their_food(client, actors, make_food):
    admin = actors.admin()
    donor_user, donor = actors.donor(admin)
    food = make_food(donor, portions_total=10)
    reporters = [actors.beneficiary() for _ in range(3)]
    waiting = actors.beneficiary()[1]
    held = _reserve(client, waiting, food["id"]).json()

    for index, (_, headers) in enumerate(reporters):
        res = _reserve(client, headers, food["id"]).json()
        client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=donor)
        status = client.post("/api/v1/complaints", json={"reservation_id": res["id"], "reason": "Yemek bozuktu ve soguktu"}, headers=headers)
        assert status.status_code == 201
        state = client.get("/api/v1/admin/accounts", params={"role": "DONOR"}, headers=admin).json()[0]["status"]
        assert state == ("SUSPENDED" if index == 2 else "ACTIVE")

    assert client.get(f"/api/v1/foods/{food['id']}").json()["status"] == "CANCELLED"
    assert client.get("/api/v1/reservations/mine", headers=waiting).json()[0]["status"] == "CANCELLED"
    assert held["id"]
    assert client.get("/api/v1/auth/me", headers=donor).status_code == 403


def test_complaint_rules(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    _, other = actors.beneficiary()
    res = _reserve(client, student, make_food(donor)["id"]).json()
    body = {"reservation_id": res["id"], "reason": "Yeterince uzun bir gerekce"}
    assert client.post("/api/v1/complaints", json=body, headers=other).status_code == 404  # not their reservation
    assert client.post("/api/v1/complaints", json={**body, "reason": "kisa"}, headers=student).status_code == 422
    created = client.post("/api/v1/complaints", json=body, headers=student)
    assert created.status_code == 201
    assert client.post("/api/v1/complaints", json=body, headers=student).status_code == 409

    resolved = client.post(f"/api/v1/admin/complaints/{created.json()['id']}/resolve", json={"action": "DISMISS", "note": "yersiz"}, headers=admin)
    assert resolved.json()["status"] == "DISMISSED"
    assert client.post(f"/api/v1/admin/complaints/{created.json()['id']}/resolve", json={"action": "RESOLVE"}, headers=admin).status_code == 409
    assert client.get("/api/v1/admin/complaints", headers=student).status_code == 403


def test_audit_trail_records_actions_and_is_admin_only(client, actors, make_food):
    admin = actors.admin()
    _, donor = actors.donor(admin)
    _, student = actors.beneficiary()
    res = _reserve(client, student, make_food(donor)["id"]).json()
    client.post("/api/v1/reservations/verify", json={"code": res["pin"]}, headers=donor)
    actions = {row["action"] for row in client.get("/api/v1/admin/audit", headers=admin).json()}
    assert {"account.registered", "account.reviewed", "food.published", "reservation.created", "reservation.collected"} <= actions
    assert client.get("/api/v1/admin/audit", headers=donor).status_code == 403
    overview = client.get("/api/v1/admin/overview", headers=admin).json()
    assert overview["reservations_by_status"]["COLLECTED"] == 1 and overview["users_by_role"]["DONOR"] == 1
    # keep food_payload import meaningful for linters
    assert food_payload()["hygiene_confirmed"] is True


def test_health_and_seed_smoke(app, client):
    from app.seed import seed_demo
    with app.state.db.session() as session:
        assert seed_demo(session) is True
        assert seed_demo(session) is False  # idempotent
    health = client.get("/api/v1/health").json()
    assert health["modules"] == ["identity", "inventory", "reservation", "notification", "impact"]
    assert client.get("/api/v1/impact/summary").json()["pickups_completed"] == 1
    assert len(client.get("/api/v1/foods").json()) >= 5


def test_seed_accepts_private_admin_password(app, client):
    from app.seed import ADMIN_EMAIL, DEMO_PASSWORD, seed_demo
    with app.state.db.session() as session:
        seed_demo(session, admin_password="Private-Admin-Pass-1")
    assert client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "Private-Admin-Pass-1"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": DEMO_PASSWORD}).status_code == 401
