"""
Data Models for Blood Donation Network with Smart Matching
Defines Pydantic models and Enums for Donors, Hospitals, Requests,
Priority Queue Items, Scores, Notifications, and Events.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field


class BloodGroup(str, Enum):
    O_NEG = "O-"
    O_POS = "O+"
    A_NEG = "A-"
    A_POS = "A+"
    B_NEG = "B-"
    B_POS = "B+"
    AB_NEG = "AB-"
    AB_POS = "AB+"


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class UrgencyLevel(str, Enum):
    CRITICAL = "Critical"  # Accident, active bleeding - immediate matching, wider radius, parallel alerts
    URGENT = "Urgent"      # Scheduled surgery within 24h - sequential alerts
    NORMAL = "Normal"      # Routine transfusion - matched in batches


class RequestStatus(str, Enum):
    QUEUED = "Queued"
    MATCHING = "Matching"
    NOTIFYING = "Notifying"
    ACCEPTED = "Accepted"
    FULFILLED = "Fulfilled"
    CANCELLED = "Cancelled"


class NotificationChannel(str, Enum):
    IN_APP = "In-App"
    SMS = "SMS"
    EMAIL = "Email"


class NotificationStatus(str, Enum):
    PENDING = "Pending"
    DELIVERED = "Delivered"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    TIMED_OUT = "Timed Out"


class EventType(str, Enum):
    REQUEST_CREATED = "RequestCreated"
    DONOR_MATCHED = "DonorMatched"
    DONOR_ALERTED = "DonorAlerted"
    DONOR_ACCEPTED = "DonorAccepted"
    DONOR_DECLINED = "DonorDeclined"
    NO_RESPONSE_TIMEOUT = "NoResponseTimeout"
    DONATION_COMPLETED = "DonationCompleted"


class Donor(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    blood_group: BloodGroup
    gender: Gender
    age: int = 25
    weight_kg: float = 65.0
    latitude: float
    longitude: float
    address: str = "Chandigarh Tricity"
    is_available: bool = True
    last_donation_date: Optional[str] = None  # YYYY-MM-DD
    health_eligible: bool = True
    response_history_rate: float = 0.90  # Historical acceptance/response rate (0.0 - 1.0)
    total_donations: int = 0

    # Cooldown computation helper
    def cooldown_days_required(self) -> int:
        """NBTC India guidelines: 90 days for men, 120 days for women."""
        return 90 if self.gender == Gender.MALE else 120

    def days_since_last_donation(self, current_date: Optional[date] = None) -> Optional[int]:
        if not self.last_donation_date:
            return None
        today = current_date or date.today()
        last_dt = datetime.strptime(self.last_donation_date, "%Y-%m-%d").date()
        return (today - last_dt).days

    def cooldown_days_remaining(self, current_date: Optional[date] = None) -> int:
        days = self.days_since_last_donation(current_date)
        if days is None:
            return 0
        required = self.cooldown_days_required()
        return max(0, required - days)

    def is_eligible_to_donate(self, current_date: Optional[date] = None) -> (bool, str):
        if not self.health_eligible:
            return False, "Health screening criteria not met"
        if not (18 <= self.age <= 65):
            return False, f"Age {self.age} outside eligible range (18-65)"
        if self.weight_kg < 45.0:
            return False, f"Weight {self.weight_kg}kg below minimum 45kg"
        if not self.is_available:
            return False, "Donor has marked themselves unavailable"
        rem = self.cooldown_days_remaining(current_date)
        if rem > 0:
            return False, f"In cooldown period ({rem} days remaining)"
        return True, "Eligible"


class Hospital(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    address: str
    latitude: float
    longitude: float
    hospital_type: str = "Multi-Specialty Hospital"


class BloodMatchScore(BaseModel):
    donor_id: str
    donor_name: str
    donor_phone: str
    donor_blood_group: BloodGroup
    distance_km: float
    blood_match_score: float      # w1 component
    distance_score: float         # w2 component
    availability_score: float     # w3 component
    response_score: float         # w4 component
    total_score: float            # Weighted sum
    rank: int = 0
    weights_used: Dict[str, float] = {}


class BloodRequest(BaseModel):
    id: str
    patient_name: str
    hospital_id: str
    hospital_name: str
    blood_group: BloodGroup
    units_required: int = 1
    urgency: UrgencyLevel
    latitude: float
    longitude: float
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: RequestStatus = RequestStatus.QUEUED
    matched_donors: List[BloodMatchScore] = []
    current_alerted_donor_ids: List[str] = []
    accepted_donor_id: Optional[str] = None
    completed_at: Optional[str] = None
    queue_wait_time_ms: Optional[float] = None
    notes: Optional[str] = None


class Notification(BaseModel):
    id: str
    request_id: str
    donor_id: str
    donor_name: str
    donor_phone: str
    donor_email: str
    blood_group_needed: BloodGroup
    urgency: UrgencyLevel
    hospital_name: str
    distance_km: float
    channel: NotificationChannel
    message: str
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    responded_at: Optional[str] = None


class SystemEvent(BaseModel):
    id: str
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any]
    description: str


class UserRole(str, Enum):
    DONOR = "donor"
    HOSPITAL = "hospital"
    ADMIN = "admin"


class User(BaseModel):
    id: str
    email: str
    password_hash: str
    role: UserRole
    name: str
    linked_entity_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DonorRegisterPayload(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    blood_group: BloodGroup
    gender: Gender
    age: int = 22
    weight_kg: float = 65.0
    address: str = "Chandigarh Tricity"
    latitude: float = 30.7333
    longitude: float = 76.7794
    is_available: bool = True
    last_donation_date: Optional[str] = None
    health_eligible: bool = True


class HospitalRegisterPayload(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    address: str
    latitude: float = 30.7333
    longitude: float = 76.7794
    hospital_type: str = "Multi-Specialty Hospital"
    license_number: str = "REG-CU-2026-01"


class LoginPayload(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    entity: Optional[Dict[str, Any]] = None
    role: UserRole

