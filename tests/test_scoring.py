"""
Unit tests for Smart Matching Scoring Algorithm
Validates dynamic urgency weights, exact vs compatible blood scoring,
and ranking order.
"""

import pytest
from backend.models import Donor, BloodRequest, BloodGroup, Gender, UrgencyLevel
from backend.matching_service import MatchingService, URGENCY_WEIGHTS


def create_sample_donor(donor_id: str, bg: BloodGroup, lat: float, lon: float, available: bool = True, resp_rate: float = 0.9):
    return Donor(
        id=donor_id,
        name=f"Donor {donor_id}",
        email=f"{donor_id}@test.com",
        phone="+919800000000",
        blood_group=bg,
        gender=Gender.MALE,
        age=25,
        weight_kg=70.0,
        latitude=lat,
        longitude=lon,
        is_available=available,
        last_donation_date=None,
        health_eligible=True,
        response_history_rate=resp_rate
    )


def test_exact_vs_compatible_match_score():
    """Exact blood match gives 1.0; compatible non-identical gives 0.75."""
    req = BloodRequest(
        id="req_test_1",
        patient_name="Test Patient",
        hospital_id="hosp_test",
        hospital_name="City Hospital",
        blood_group=BloodGroup.A_POS,
        urgency=UrgencyLevel.NORMAL,
        latitude=30.70,
        longitude=76.70
    )

    # Donor 1: exact match A+, identical location
    donor_exact = create_sample_donor("d_exact", BloodGroup.A_POS, lat=30.70, lon=76.70)
    # Donor 2: compatible match O-, identical location
    donor_comp = create_sample_donor("d_comp", BloodGroup.O_NEG, lat=30.70, lon=76.70)

    matches = MatchingService.calculate_scores([donor_exact, donor_comp], req)
    assert len(matches) == 2

    match_dict = {m.donor_id: m for m in matches}
    assert match_dict["d_exact"].blood_match_score == 1.0
    assert match_dict["d_comp"].blood_match_score == 0.75
    # Exact match should rank #1
    assert matches[0].donor_id == "d_exact"


def test_critical_urgency_prioritizes_proximity():
    """
    In Critical urgency, a closer donor with compatible blood
    can outrank a distant donor with exact blood match due to high w2 weight.
    """
    req = BloodRequest(
        id="req_crit",
        patient_name="Critical Patient",
        hospital_id="hosp_crit",
        hospital_name="Trauma Center",
        blood_group=BloodGroup.A_POS,
        urgency=UrgencyLevel.CRITICAL,
        latitude=30.70,
        longitude=76.70
    )

    # Donor 1: Exact A+, but 35 km away
    # 0.35 degrees latitude is ~39 km
    donor_far_exact = create_sample_donor("d_far", BloodGroup.A_POS, lat=30.70 + 0.32, lon=76.70)

    # Donor 2: Compatible O-, right next to hospital (0.5 km away)
    donor_close_comp = create_sample_donor("d_close", BloodGroup.O_NEG, lat=30.70 + 0.004, lon=76.70)

    matches = MatchingService.calculate_scores([donor_far_exact, donor_close_comp], req)
    assert len(matches) == 2
    # The close donor should rank first in Critical scenario!
    assert matches[0].donor_id == "d_close"
