"""
Unit tests for User Service: Registration & Authentication
Corresponds to Section 5.1 of the Project Synopsis:
"1. User Service: registration, login, and profiles for donors, hospitals, and admins."
"""

import pytest
from backend.models import (
    BloodGroup,
    Gender,
    UserRole,
    DonorRegisterPayload,
    HospitalRegisterPayload,
    LoginPayload
)
from backend.database import AppState


def test_seed_user_authentication():
    state = AppState()
    # 1. Author donor login
    session_anuj = state.authenticate_user("anuj@cu.ac.in", "anuj123")
    assert session_anuj is not None
    assert session_anuj["user"]["name"] == "Anuj Kumar"
    assert session_anuj["role"] == UserRole.DONOR
    assert session_anuj["entity"]["blood_group"] == BloodGroup.O_POS

    # 2. Hospital login
    session_hosp = state.authenticate_user("pgimer@hospital.in", "pgi123")
    assert session_hosp is not None
    assert session_hosp["role"] == UserRole.HOSPITAL
    assert session_hosp["user"]["linked_entity_id"] == "hosp_pgimer"

    # 3. Admin login
    session_admin = state.authenticate_user("admin@bloodnet.org", "admin123")
    assert session_admin is not None
    assert session_admin["role"] == UserRole.ADMIN

    # 4. Wrong password fails
    assert state.authenticate_user("anuj@cu.ac.in", "wrongpass") is None
    # 5. Non-existent email fails
    assert state.authenticate_user("nobody@test.com", "pass") is None


def test_donor_registration_flow():
    state = AppState()

    payload = DonorRegisterPayload(
        name="Harpreet Kaur",
        email="harpreet.kaur@test.com",
        password="securepass123",
        phone="+91-9888877777",
        blood_group=BloodGroup.B_POS,
        gender=Gender.FEMALE,
        age=23,
        weight_kg=58.0,
        address="Sector 35, Chandigarh",
        latitude=30.7245,
        longitude=76.7645,
        is_available=True,
        health_eligible=True
    )

    user, donor = state.register_donor(payload)
    assert user.email == "harpreet.kaur@test.com"
    assert user.role == UserRole.DONOR
    assert donor.blood_group == BloodGroup.B_POS
    assert donor.gender == Gender.FEMALE
    # Female NBTC cooldown period is 120 days
    assert donor.cooldown_days_required() == 120

    # Verify donor is in state.donors and state.users
    assert donor.id in state.donors
    assert user.email in state.users

    # Verify authentication works
    session = state.authenticate_user("harpreet.kaur@test.com", "securepass123")
    assert session is not None
    assert session["user"]["name"] == "Harpreet Kaur"
    assert session["entity"]["is_eligible"] is True

    # Duplicate registration should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        state.register_donor(payload)


def test_hospital_registration_flow():
    state = AppState()

    payload = HospitalRegisterPayload(
        name="Apollo Hospital Chandigarh",
        email="emergency@apollochd.in",
        password="apollopassword",
        phone="+91-172-6000000",
        address="Sector 8, Chandigarh",
        latitude=30.7420,
        longitude=76.7900,
        hospital_type="Tertiary Care Hospital",
        license_number="REG-PB-2026-99"
    )

    user, hospital = state.register_hospital(payload)
    assert user.email == "emergency@apollochd.in"
    assert user.role == UserRole.HOSPITAL
    assert hospital.id in state.hospitals

    session = state.authenticate_user("emergency@apollochd.in", "apollopassword")
    assert session is not None
    assert session["user"]["name"] == "Apollo Hospital Chandigarh"

    # Duplicate registration prevention
    with pytest.raises(ValueError, match="already exists"):
        state.register_hospital(payload)
