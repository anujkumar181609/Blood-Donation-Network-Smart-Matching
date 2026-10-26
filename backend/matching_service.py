"""
Matching Service & Algorithm Implementation
Implements the 4-step smart matching algorithm from Section 5.2:
Step 1: Blood compatibility filter (compatibility map)
Step 2: Eligibility & cooldown filter (90d male / 120d female NBTC)
Step 3: Distance calculation using the Haversine formula
Step 4: Dynamic weighted scoring & ranking with urgency-based weight shifts:
        Score = w1 * BloodMatch + w2 * (1 / Distance) + w3 * Availability + w4 * ResponseHistory
"""

import math
from typing import List, Dict, Tuple, Optional
from datetime import date
from backend.models import (
    BloodGroup,
    UrgencyLevel,
    Donor,
    BloodMatchScore,
    BloodRequest
)

# Comprehensive Blood Compatibility Map: Recipient Blood Group -> Compatible Donor Blood Groups
COMPATIBILITY_MAP: Dict[BloodGroup, List[BloodGroup]] = {
    BloodGroup.AB_POS: [
        BloodGroup.O_NEG, BloodGroup.O_POS,
        BloodGroup.B_NEG, BloodGroup.B_POS,
        BloodGroup.A_NEG, BloodGroup.A_POS,
        BloodGroup.AB_NEG, BloodGroup.AB_POS
    ],  # Universal recipient
    BloodGroup.AB_NEG: [
        BloodGroup.O_NEG, BloodGroup.B_NEG,
        BloodGroup.A_NEG, BloodGroup.AB_NEG
    ],
    BloodGroup.A_POS: [
        BloodGroup.O_NEG, BloodGroup.O_POS,
        BloodGroup.A_NEG, BloodGroup.A_POS
    ],
    BloodGroup.A_NEG: [
        BloodGroup.O_NEG, BloodGroup.A_NEG
    ],
    BloodGroup.B_POS: [
        BloodGroup.O_NEG, BloodGroup.O_POS,
        BloodGroup.B_NEG, BloodGroup.B_POS
    ],
    BloodGroup.B_NEG: [
        BloodGroup.O_NEG, BloodGroup.B_NEG
    ],
    BloodGroup.O_POS: [
        BloodGroup.O_NEG, BloodGroup.O_POS
    ],
    BloodGroup.O_NEG: [
        BloodGroup.O_NEG
    ],  # Universal donor (can only receive from O-)
}

# Dynamic Weights shifting with urgency level
URGENCY_WEIGHTS: Dict[UrgencyLevel, Dict[str, float]] = {
    UrgencyLevel.CRITICAL: {
        "w_blood": 0.20,
        "w_distance": 0.45,       # Proximity prioritized for active bleeding / accidents
        "w_availability": 0.25,   # Immediate availability prioritized
        "w_response": 0.10,
        "radius_km": 50.0,
        "alert_mode": "parallel",
        "top_n_alerts": 3
    },
    UrgencyLevel.URGENT: {
        "w_blood": 0.35,
        "w_distance": 0.30,
        "w_availability": 0.20,
        "w_response": 0.15,
        "radius_km": 30.0,
        "alert_mode": "sequential",
        "top_n_alerts": 1
    },
    UrgencyLevel.NORMAL: {
        "w_blood": 0.50,          # Exact match prioritized to conserve universal O- blood
        "w_distance": 0.20,
        "w_availability": 0.15,
        "w_response": 0.15,
        "radius_km": 20.0,
        "alert_mode": "batch",
        "top_n_alerts": 1
    }
}


def is_blood_compatible(donor_bg: BloodGroup, recipient_bg: BloodGroup) -> bool:
    """Step 1: Blood compatibility filter."""
    compatible_list = COMPATIBILITY_MAP.get(recipient_bg, [])
    return donor_bg in compatible_list


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Step 3: Distance calculation using the Haversine formula from Section 5.2:
    d = 2R * arcsin( sqrt( sin^2(Δφ/2) + cos φ1 * cos φ2 * sin^2(Δλ/2) ) )
    where R = 6371.0 km (Earth's radius).
    """
    R = 6371.0  # Earth's radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    sin_half_dphi = math.sin(delta_phi / 2.0)
    sin_half_dlam = math.sin(delta_lambda / 2.0)

    val = (sin_half_dphi ** 2) + math.cos(phi1) * math.cos(phi2) * (sin_half_dlam ** 2)
    # Ensure domain clamping to avoid floating-point rounding errors outside [0.0, 1.0]
    val = min(1.0, max(0.0, val))
    d = 2.0 * R * math.asin(math.sqrt(val))
    return round(d, 3)


class MatchingService:
    @staticmethod
    def calculate_scores(
        donors: List[Donor],
        request: BloodRequest,
        current_date: Optional[date] = None,
        top_n: int = 10
    ) -> List[BloodMatchScore]:
        """
        Executes the full 4-step matching pipeline:
        1. Compatibility filter
        2. Eligibility & cooldown filter
        3. Haversine distance computation and radius filter
        4. Scoring & ranking
        """
        config = URGENCY_WEIGHTS.get(request.urgency, URGENCY_WEIGHTS[UrgencyLevel.NORMAL])
        w1 = config["w_blood"]
        w2 = config["w_distance"]
        w3 = config["w_availability"]
        w4 = config["w_response"]
        max_radius = config["radius_km"]

        scored_donors: List[BloodMatchScore] = []

        for donor in donors:
            # Step 1: Compatibility Filter
            if not is_blood_compatible(donor.blood_group, request.blood_group):
                continue

            # Step 2: Eligibility & Cooldown Filter
            is_eligible, _ = donor.is_eligible_to_donate(current_date)
            if not is_eligible:
                continue

            # Step 3: Distance Calculation (Haversine)
            dist_km = haversine_distance(
                donor.latitude, donor.longitude,
                request.latitude, request.longitude
            )

            # Check radius bounds
            if dist_km > max_radius:
                continue

            # Step 4: Scoring and Ranking
            # BloodMatch: 1.0 for exact group match, 0.75 for compatible non-identical
            blood_match = 1.0 if donor.blood_group == request.blood_group else 0.75

            # Distance normalization: smooth decay so closer donors score higher
            # Normalized distance factor between 0.0 and 1.0
            distance_factor = 1.0 / (1.0 + (dist_km / 10.0))

            # Availability factor (1.0 for currently available)
            availability_factor = 1.0 if donor.is_available else 0.0

            # Response history (historical response/acceptance rate)
            response_history = max(0.0, min(1.0, donor.response_history_rate))

            # Weighted sum:
            total_score = (
                w1 * blood_match +
                w2 * distance_factor +
                w3 * availability_factor +
                w4 * response_history
            )

            score_record = BloodMatchScore(
                donor_id=donor.id,
                donor_name=donor.name,
                donor_phone=donor.phone,
                donor_blood_group=donor.blood_group,
                distance_km=dist_km,
                blood_match_score=round(blood_match, 3),
                distance_score=round(distance_factor, 3),
                availability_score=round(availability_factor, 3),
                response_score=round(response_history, 3),
                total_score=round(total_score, 4),
                rank=0,
                weights_used={
                    "w1_blood": w1,
                    "w2_distance": w2,
                    "w3_availability": w3,
                    "w4_response": w4
                }
            )
            scored_donors.append(score_record)

        # Sort descending by total_score
        scored_donors.sort(key=lambda x: x.total_score, reverse=True)

        # Assign ranks
        for idx, item in enumerate(scored_donors[:top_n], start=1):
            item.rank = idx

        return scored_donors[:top_n]
