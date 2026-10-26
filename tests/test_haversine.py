"""
Unit tests for Haversine Distance Formula
Validates distance calculations between real-world coordinates,
symmetry, and zero-distance edge cases.
"""

import pytest
import math
from backend.matching_service import haversine_distance


def test_zero_distance_identical_coords():
    """Distance between the same coordinates must be 0.0."""
    lat, lon = 30.7333, 76.7794
    dist = haversine_distance(lat, lon, lat, lon)
    assert dist == 0.0


def test_symmetry():
    """Distance from A to B must equal distance from B to A."""
    lat1, lon1 = 30.7628, 76.7766  # PGIMER
    lat2, lon2 = 30.7082, 76.7820  # GMCH Sector 32
    d1 = haversine_distance(lat1, lon1, lat2, lon2)
    d2 = haversine_distance(lat2, lon2, lat1, lon1)
    assert abs(d1 - d2) < 1e-4
    # Distance between PGI and GMCH 32 is approximately 6.1 km
    assert 5.5 <= d1 <= 6.8


def test_chandigarh_to_cu_distance():
    """Verify distance between PGIMER Chandigarh and Chandigarh University Campus Gharuan (~20 km)."""
    pgi_lat, pgi_lon = 30.7628, 76.7766
    cu_lat, cu_lon = 30.7699, 76.5760
    dist = haversine_distance(pgi_lat, pgi_lon, cu_lat, cu_lon)
    assert 18.0 <= dist <= 22.0
