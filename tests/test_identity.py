from tests.conftest import PASSWORD


# ARRANGE-ACT-ASSERT: hazırla, çalıştır, doğrula. Burada: yararlanıcı kaydolur, giriş yapar ve kendi
# bilgisini görür; yanıtta parola veya hash'in OLMADIĞI da kanıtlanır.
def test_beneficiary_registers_active_and_logs_in(client, actors):
    user, headers = actors.beneficiary()
    assert user["status"] == "ACTIVE"
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == user["email"]
    assert "password" not in me and "password_hash" not in me


# Güvenlik: kimse kendini yönetici yapamaz.
def test_admin_role_cannot_be_self_registered(client):
    res = client.post("/api/v1/auth/register", json={"email": "x@t.test", "password": PASSWORD, "full_name": "Evil Admin", "role": "ADMIN"})
    assert res.status_code == 403


# Aynı e-posta büyük harfle bile ikinci kez kaydedilemez (409).
def test_duplicate_email_conflict(client, actors):
    user, _ = actors.beneficiary()
    res = client.post("/api/v1/auth/register", json={"email": user["email"].upper(), "password": PASSWORD, "full_name": "Other Person", "role": "BENEFICIARY"})
    assert res.status_code == 409


# Bağışçı için zorunlu alanlar eksikse Pydantic 422 döner ve servise hiç ulaşılmaz.
def test_donor_registration_requires_organization_fields(client):
    res = client.post("/api/v1/auth/register", json={"email": "d@t.test", "password": PASSWORD, "full_name": "Don Or", "role": "DONOR"})
    assert res.status_code == 422


# Onay iş akışı: onaylanmadan 403, onaylanınca ilan açılır.
def test_pending_donor_cannot_publish_until_approved(client, actors, make_food):
    admin = actors.admin()
    user, headers = actors.donor(admin, approve=False)
    assert user["status"] == "PENDING_REVIEW"
    from tests.conftest import food_payload
    assert client.post("/api/v1/foods", json=food_payload(), headers=headers).status_code == 403
    client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=admin)
    assert make_food(headers)["status"] == "AVAILABLE"


# Kaba kuvvet koruması: 8 hatalı denemeden sonra DOĞRU parola bile 429 alır.
def test_login_lockout_after_repeated_failures(client, actors):
    user, _ = actors.beneficiary()
    for _ in range(8):
        assert client.post("/api/v1/auth/login", json={"email": user["email"], "password": "wrong-password"}).status_code == 401
    locked = client.post("/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert locked.status_code == 429


# Hesap varlığı sızdırılmaz: iki durumda yanıt birebir aynıdır.
def test_wrong_password_and_unknown_email_look_the_same(client, actors):
    user, _ = actors.beneficiary()
    a = client.post("/api/v1/auth/login", json={"email": user["email"], "password": "nope-nope"})
    b = client.post("/api/v1/auth/login", json={"email": "ghost@t.test", "password": "nope-nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


# Rol kontrolü: bağışçı yönetici uç noktalarına 403 alır.
def test_only_admin_can_review_and_list_accounts(client, actors):
    admin = actors.admin()
    user, headers = actors.donor(admin, approve=False)
    assert client.get("/api/v1/admin/accounts", headers=headers).status_code == 403
    assert client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "APPROVE"}, headers=headers).status_code == 403
    pending = client.get("/api/v1/admin/accounts", params={"status": "PENDING_REVIEW"}, headers=admin).json()
    assert [u["id"] for u in pending] == [user["id"]]


# Reddedilen girişte, askıya alınan eski biletle bile 403 alır; yeniden etkinleştirilince erişim
# geri gelir.
def test_rejected_and_suspended_accounts_cannot_log_in(client, actors):
    admin = actors.admin()
    user, _ = actors.donor(admin, approve=False)
    client.post(f"/api/v1/admin/accounts/{user['id']}/review", json={"decision": "REJECT", "note": "eksik belge"}, headers=admin)
    res = client.post("/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert res.status_code == 403

    other, other_headers = actors.beneficiary()
    client.post(f"/api/v1/admin/accounts/{other['id']}/suspend", json={"reason": "test sebebi"}, headers=admin)
    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 403
    client.post(f"/api/v1/admin/accounts/{other['id']}/reinstate", headers=admin)
    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 200


# Bilet yoksa veya bozuksa 401.
def test_missing_and_garbage_tokens_are_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
