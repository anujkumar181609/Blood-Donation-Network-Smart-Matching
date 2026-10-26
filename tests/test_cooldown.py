"""
Unit tests for Scheduling Service and Donor Cooldown
Verifies:
1. 90-day cooldown for male donors (NBTC India guidelines)
2. 120-day cooldown for female donors
3. Eligibility transitions before and after cooldown expiry
4. Cooldown activation after completed donation
"""

import pytest
from datetime import date, timedelta
from backend.models import Donor, Gender, BloodGroup
from backend.scheduling_service import SchedulingService


def test_male_cooldown_90_days():
    today = date(2026, 10, 15)

    # Donated 40 days ago -> 50 days remaining -> Ineligible
    male_donor = Donor(
        id="d_male",
        name="Test Male",
        email="male@test.com",
        phone="+919800000001",
        blood_group=BloodGroup.O_POS,
        gender=Gender.MALE,
        latitude=30.73,
        longitude=76.78,
        last_donation_date=(today - timedelta(days=40)).isoformat()
    )

    status = SchedulingService.calculate_cooldown_status(male_donor, target_date=today)
    assert status["in_cooldown"] is True
    assert status["days_remaining"] == 50
    assert status["required_cooldown_days"] == 90

    is_eligible, reason = male_donor.is_eligible_to_donate(current_date=today)
    assert is_eligible is False
    assert "In cooldown period (50 days remaining)" in reason

    # Donated 95 days ago -> 0 days remaining -> Eligible
    male_donor.last_donation_date = (today - timedelta(days=95)).isoformat()
    status2 = SchedulingService.calculate_cooldown_status(male_donor, target_date=today)
    assert status2["in_cooldown"] is False
    assert status2["days_remaining"] == 0

    is_eligible2, _ = male_donor.is_eligible_to_donate(current_date=today)
    assert is_eligible2 is True


def test_female_cooldown_120_days():
    today = date(2026, 10, 15)

    # Donated 100 days ago -> 20 days remaining -> Ineligible
    female_donor = Donor(
        id="d_female",
        name="Test Female",
        email="female@test.com",
        phone="+919800000002",
        blood_group=BloodGroup.B_POS,
        gender=Gender.FEMALE,
        latitude=30.73,
        longitude=76.78,
        last_donation_date=(today - timedelta(days=100)).isoformat()
    )

    status = SchedulingService.calculate_cooldown_status(female_donor, target_date=today)
    assert status["in_cooldown"] is True
    assert status["days_remaining"] == 20
    assert status["required_cooldown_days"] == 120

    is_eligible, _ = female_donor.is_eligible_to_donate(current_date=today)
    assert is_eligible is False

    # Donated 125 days ago -> 0 remaining -> Eligible
    female_donor.last_donation_date = (today - timedelta(days=125)).isoformat()
    is_eligible2, _ = female_donor.is_eligible_to_donate(current_date=today)
    assert is_eligible2 is True


def test_record_completed_donation():
    donor = Donor(
        id="d_fresh",
        name="Fresh Donor",
        email="fresh@test.com",
        phone="+919800000003",
        blood_group=BloodGroup.A_POS,
        gender=Gender.MALE,
        latitude=30.73,
        longitude=76.78,
        last_donation_date=None,
        total_donations=0
    )

    today_str = date.today().isoformat()
    SchedulingService.record_completed_donation(donor, donation_date=today_str)

    assert donor.last_donation_date == today_str
    assert donor.total_donations == 1
    assert donor.cooldown_days_remaining() == 90
