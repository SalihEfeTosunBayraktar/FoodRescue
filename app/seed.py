"""Demo data for the local test server. Runs only on an empty database.

Ders notu: tohum (seed) verisi geliştirme/test içindir; asla gerçek şifre içermez. Uygulama
kodunu çalıştırarak veri üretmek (ORM yerine servis katmanını kullanmak) iş kurallarının da
doğru çalıştığını kanıtlar.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.security import hash_password
from app.modules.identity import service as identity
from app.modules.identity.models import AccountStatus, User, UserRole
from app.modules.identity.schemas import RegisterIn
from app.modules.inventory import service as inventory
from app.modules.inventory.models import FoodCategory, StorageCondition
from app.modules.inventory.schemas import FoodCreate
from app.modules.reservation import service as reservation
from app.modules.reservation.schemas import ReservationCreate

# Local test credentials. Printed by run.py so students can log in.
DEMO_PASSWORD = "Demo12345"
ADMIN_EMAIL = "admin@foodrescue.local"
DEMO_ACCOUNTS = {
    "admin": ADMIN_EMAIL,
    "donor": "restoran@foodrescue.local",
    "donor_pending": "yeni.isletme@foodrescue.local",
    "beneficiary": "ogrenci@foodrescue.local",
    "shelter": "barinak@foodrescue.local",
}


def _register(db: Session, **fields) -> User:
    return identity.register(db, RegisterIn(password=DEMO_PASSWORD, **fields))


def seed_demo(db: Session, admin_password: str | None = None) -> bool:
    """`admin_password` lets a publicly shared instance use a private admin password instead of the demo one."""
    if db.scalar(select(func.count()).select_from(User)):
        return False

    db.add(
        User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(admin_password or DEMO_PASSWORD),
            full_name="Sistem Yöneticisi",
            role=UserRole.ADMIN,
            status=AccountStatus.ACTIVE,
        )
    )
    db.commit()
    admin = identity.list_accounts(db, role=UserRole.ADMIN)[0]

    donors = [
        _register(db, email=DEMO_ACCOUNTS["donor"], full_name="Mehmet Demir", role="DONOR",
                  organization_name="Sivas Lezzet Sofrası", license_number="LIC-58-0001",
                  address="Atatürk Cd. No:12, Merkez/Sivas", latitude=39.7505, longitude=37.0150),
        _register(db, email="firin@foodrescue.local", full_name="Ayşe Kaya", role="DONOR",
                  organization_name="Paşabey Ekmek Fırını", license_number="LIC-58-0002",
                  address="Kurtuluş Mh. 5. Sk., Merkez/Sivas", latitude=39.7440, longitude=37.0290),
        _register(db, email="yemekhane@foodrescue.local", full_name="Can Yıldız", role="DONOR",
                  organization_name="Kampüs Yemekhanesi", license_number="LIC-58-0003",
                  address="Cumhuriyet Üniversitesi Kampüsü, Sivas", latitude=39.7280, longitude=37.0520),
    ]
    for donor in donors:
        identity.review_account(db, admin, donor.id, True, None)
    _register(db, email=DEMO_ACCOUNTS["donor_pending"], full_name="Ece Aydın", role="DONOR",
              organization_name="Yeni Bistro", license_number="LIC-58-0099",
              address="Çarşı Cd. No:3, Merkez/Sivas", latitude=39.7490, longitude=37.0200)

    student = _register(db, email=DEMO_ACCOUNTS["beneficiary"], full_name="Ali Yılmaz", role="BENEFICIARY")
    shelter = _register(db, email=DEMO_ACCOUNTS["shelter"], full_name="Zeynep Acar", role="SHELTER",
                        organization_name="Sivas Hayvan Barınağı", license_number="SHL-58-0007",
                        address="Organize Sanayi Yolu, Sivas")
    identity.review_account(db, admin, shelter.id, True, None)

    now = utcnow()

    def publish(donor: User, title: str, category: FoodCategory, storage: StorageCondition, portions: int, hours: float, desc: str):
        return inventory.create_food(
            db, donor,
            FoodCreate(title=title, description=desc, category=category, storage=storage, portions_total=portions,
                       max_per_person=2, pickup_until=now + timedelta(hours=hours), hygiene_confirmed=True),
        )

    soup = publish(donors[0], "Mercimek çorbası", FoodCategory.HUMAN, StorageCondition.HOT, 12, 3, "Gün sonu kalan taze çorba.")
    publish(donors[0], "Pilav ve tavuk", FoodCategory.HUMAN, StorageCondition.HOT, 8, 2.5, "Porsiyonluk paketlenmiş.")
    publish(donors[1], "Günlük ekmek paketi", FoodCategory.HUMAN, StorageCondition.ROOM, 20, 5, "Kapanışta kalan ekmekler.")
    publish(donors[1], "Kuru ekmek (hayvan yemi)", FoodCategory.ANIMAL, StorageCondition.ROOM, 30, 12, "Barınaklar için kuru ekmek.")
    publish(donors[2], "Yemekhane akşam menüsü", FoodCategory.HUMAN, StorageCondition.HOT, 25, 4, "Kuru fasulye, pilav, cacık.")
    publish(donors[2], "Et suyu ve kemik", FoodCategory.ANIMAL, StorageCondition.COLD, 10, 6, "Hayvan beslemeye uygun mutfak artığı.")

    done = reservation.create_reservation(db, student, ReservationCreate(food_id=soup.id, portions=1))
    reservation.verify_pickup(db, donors[0], done.pin)  # one completed pickup so the stats are not empty
    return True
