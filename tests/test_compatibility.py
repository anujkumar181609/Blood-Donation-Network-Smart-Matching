"""
Unit tests for Blood Compatibility Matrix
Verifies universal donor (O-), universal recipient (AB+),
and all ABO / Rh compatibility rules.
"""

import pytest
from backend.models import BloodGroup
from backend.matching_service import is_blood_compatible, COMPATIBILITY_MAP


def test_o_negative_universal_donor():
    """O- should be compatible with every blood group."""
    all_groups = list(BloodGroup)
    for bg in all_groups:
        assert is_blood_compatible(BloodGroup.O_NEG, bg) is True, f"O- should donate to {bg.value}"


def test_ab_positive_universal_recipient():
    """AB+ should be able to receive from every blood group."""
    all_groups = list(BloodGroup)
    for bg in all_groups:
        assert is_blood_compatible(bg, BloodGroup.AB_POS) is True, f"AB+ should receive from {bg.value}"


def test_o_positive_rules():
    """O+ can donate to O+, A+, B+, AB+, but NOT to any Rh- group."""
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.O_POS) is True
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.A_POS) is True
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.B_POS) is True
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.AB_POS) is True

    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.O_NEG) is False
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.A_NEG) is False
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.B_NEG) is False
    assert is_blood_compatible(BloodGroup.O_POS, BloodGroup.AB_NEG) is False


def test_incompatible_cross_types():
    """Verify incompatible ABO cross donations."""
    # A cannot donate to B
    assert is_blood_compatible(BloodGroup.A_POS, BloodGroup.B_POS) is False
    assert is_blood_compatible(BloodGroup.A_NEG, BloodGroup.B_NEG) is False

    # B cannot donate to A
    assert is_blood_compatible(BloodGroup.B_POS, BloodGroup.A_POS) is False
    assert is_blood_compatible(BloodGroup.B_NEG, BloodGroup.A_NEG) is False

    # AB can only donate to AB
    assert is_blood_compatible(BloodGroup.AB_POS, BloodGroup.A_POS) is False
    assert is_blood_compatible(BloodGroup.AB_POS, BloodGroup.B_POS) is False
    assert is_blood_compatible(BloodGroup.AB_POS, BloodGroup.O_POS) is False


def test_o_negative_recipient_restrictions():
    """O- recipient can ONLY receive from O-."""
    for bg in BloodGroup:
        if bg == BloodGroup.O_NEG:
            assert is_blood_compatible(bg, BloodGroup.O_NEG) is True
        else:
            assert is_blood_compatible(bg, BloodGroup.O_NEG) is False
