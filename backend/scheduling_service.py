"""
Scheduling Service
Manages donor availability schedules, cooldown calculation (NBTC guidelines:
90 days for men, 120 days for women), and donation history tracking.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from backend.models import Donor, Gender


class SchedulingService:
    @staticmethod
    def calculate_cooldown_status(donor: Donor, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Calculates cooldown days, eligibility, and the exact next eligible donation date.
        """
        today = target_date or date.today()
        cooldown_required = donor.cooldown_days_required()

        if not donor.last_donation_date:
            return {
                "in_cooldown": False,
                "days_since_last": None,
                "days_remaining": 0,
                "required_cooldown_days": cooldown_required,
                "next_eligible_date": today.isoformat(),
                "status_label": "Ready to Donate"
            }

        last_dt = datetime.strptime(donor.last_donation_date, "%Y-%m-%d").date()
        days_passed = (today - last_dt).days
        days_remaining = max(0, cooldown_required - days_passed)
        next_date = last_dt + timedelta(days=cooldown_required)

        return {
            "in_cooldown": days_remaining > 0,
            "days_since_last": days_passed,
            "days_remaining": days_remaining,
            "required_cooldown_days": cooldown_required,
            "next_eligible_date": next_date.isoformat(),
            "status_label": f"Cooling Down ({days_remaining}d left)" if days_remaining > 0 else "Ready to Donate"
        }

    @staticmethod
    def record_completed_donation(donor: Donor, donation_date: Optional[str] = None) -> Donor:
        """
        Invoked on DonationCompleted event:
        1. Updates donor last_donation_date to today (or donation_date).
        2. Increments total_donations count.
        3. Sets donor into cooldown period.
        """
        d_date = donation_date or date.today().isoformat()
        donor.last_donation_date = d_date
        donor.total_donations += 1
        return donor
