"""
Application State and Data Store
Maintains in-memory registries for Donors, Hospitals, Requests,
wires up the EventBus, PriorityQueue, NotificationService, and SchedulingService.
"""

import uuid
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import logging

from backend.models import (
    Donor,
    Hospital,
    BloodRequest,
    RequestStatus,
    UrgencyLevel,
    EventType,
    NotificationChannel,
    NotificationStatus,
    BloodGroup,
    Gender,
    User,
    UserRole,
    DonorRegisterPayload,
    HospitalRegisterPayload
)
from backend.priority_queue import RequestPriorityQueue
from backend.matching_service import MatchingService
from backend.scheduling_service import SchedulingService
from backend.notification_service import NotificationService
from backend.event_bus import global_event_bus
from backend.synthetic_data import DEFAULT_HOSPITALS, generate_synthetic_donors

logger = logging.getLogger("Database")


class AppState:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.donors: Dict[str, Donor] = {}
        self.hospitals: Dict[str, Hospital] = {}
        self.requests: Dict[str, BloodRequest] = {}
        self.priority_queue = RequestPriorityQueue()
        self.notifications = NotificationService()
        self.event_bus = global_event_bus
        self.matching_service = MatchingService()
        self.scheduling_service = SchedulingService()

        # Seed default data
        self.reset_to_default_seed()

        # Wire up event subscribers
        self._setup_event_subscriptions()

    def reset_to_default_seed(self, donor_count: int = 60):
        """Initializes or resets the in-memory database with realistic seed data."""
        self.donors.clear()
        self.hospitals.clear()
        self.requests.clear()
        self.priority_queue = RequestPriorityQueue()
        self.event_bus.clear()

        for hosp in DEFAULT_HOSPITALS:
            self.hospitals[hosp.id] = hosp

        seed_donors = generate_synthetic_donors(count=donor_count, seed=42)
        for d in seed_donors:
            self.donors[d.id] = d

        # Add predefined demonstration donors:
        # 1. Anuj Kumar (AIT-CSE-AIML, 24BAI70735) - O+ Available donor near CU/Mohali
        anuj = Donor(
            id="donor_anuj",
            name="Anuj Kumar",
            email="anuj.kumar@cumail.in",
            phone="+91-9876543210",
            blood_group=BloodGroup.O_POS,
            gender=Gender.MALE,
            age=21,
            weight_kg=68.0,
            latitude=30.7680,
            longitude=76.5775,
            address="Chandigarh University Campus, Gharuan",
            is_available=True,
            last_donation_date=None,  # Ready to donate
            health_eligible=True,
            response_history_rate=0.98,
            total_donations=2
        )
        self.donors[anuj.id] = anuj

        # 2. Shlok Kandola (AIT-CSE-AIML, 24BAI70823) - O- Universal donor near Mohali/PGI
        shlok = Donor(
            id="donor_shlok",
            name="Shlok Kandola",
            email="shlok.kandola@cumail.in",
            phone="+91-9812345678",
            blood_group=BloodGroup.O_NEG,
            gender=Gender.MALE,
            age=21,
            weight_kg=72.0,
            latitude=30.7100,
            longitude=76.7200,
            address="Phase 7, Mohali",
            is_available=True,
            last_donation_date=None,  # Universal donor ready
            health_eligible=True,
            response_history_rate=0.99,
            total_donations=3
        )
        self.donors[shlok.id] = shlok

        # Seed Default User Accounts for System Architecture (Section 5.1)
        self.users.clear()
        # 1. Lead Author Donor (Anuj Kumar)
        self.users["anuj@cu.ac.in"] = User(
            id="usr_anuj",
            email="anuj@cu.ac.in",
            password_hash=self.hash_password("anuj123"),
            role=UserRole.DONOR,
            name="Anuj Kumar",
            linked_entity_id=anuj.id
        )
        # 2. Co-Author Donor (Shlok Kandola)
        self.users["shlok@cu.ac.in"] = User(
            id="usr_shlok",
            email="shlok@cu.ac.in",
            password_hash=self.hash_password("shlok123"),
            role=UserRole.DONOR,
            name="Shlok Kandola",
            linked_entity_id=shlok.id
        )
        # 3. Hospital Requester (PGIMER)
        self.users["pgimer@hospital.in"] = User(
            id="usr_pgimer",
            email="pgimer@hospital.in",
            password_hash=self.hash_password("pgi123"),
            role=UserRole.HOSPITAL,
            name="PGIMER Emergency",
            linked_entity_id="hosp_pgimer"
        )
        # 4. System Administrator
        self.users["admin@bloodnet.org"] = User(
            id="usr_admin",
            email="admin@bloodnet.org",
            password_hash=self.hash_password("admin123"),
            role=UserRole.ADMIN,
            name="Network Administrator"
        )

        logger.info(f"Initialized database with {len(self.hospitals)} hospitals, {len(self.donors)} donors, and {len(self.users)} auth users.")

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(f"salt_agy_{password}".encode()).hexdigest()

    def register_donor(self, payload: DonorRegisterPayload) -> Tuple[User, Donor]:
        """Registers a new voluntary donor and generates authentication credentials."""
        email_clean = payload.email.strip().lower()
        if email_clean in self.users:
            raise ValueError(f"An account with email '{email_clean}' already exists.")

        donor_id = f"donor_{uuid.uuid4().hex[:6]}"
        donor = Donor(
            id=donor_id,
            name=payload.name.strip(),
            email=email_clean,
            phone=payload.phone.strip(),
            blood_group=payload.blood_group,
            gender=payload.gender,
            age=payload.age,
            weight_kg=payload.weight_kg,
            latitude=payload.latitude,
            longitude=payload.longitude,
            address=payload.address,
            is_available=payload.is_available,
            last_donation_date=payload.last_donation_date,
            health_eligible=payload.health_eligible,
            response_history_rate=0.95,
            total_donations=0
        )
        self.donors[donor_id] = donor

        user = User(
            id=f"usr_{uuid.uuid4().hex[:6]}",
            email=email_clean,
            password_hash=self.hash_password(payload.password),
            role=UserRole.DONOR,
            name=payload.name.strip(),
            linked_entity_id=donor_id
        )
        self.users[email_clean] = user
        logger.info(f"Successfully registered Donor account: {donor.name} ({email_clean})")
        return user, donor

    def register_hospital(self, payload: HospitalRegisterPayload) -> Tuple[User, Hospital]:
        """Registers a new hospital/requester institution and generates credentials."""
        email_clean = payload.email.strip().lower()
        if email_clean in self.users:
            raise ValueError(f"An account with email '{email_clean}' already exists.")

        hosp_id = f"hosp_{uuid.uuid4().hex[:6]}"
        hospital = Hospital(
            id=hosp_id,
            name=payload.name.strip(),
            email=email_clean,
            phone=payload.phone.strip(),
            address=payload.address.strip(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            hospital_type=payload.hospital_type
        )
        self.hospitals[hosp_id] = hospital

        user = User(
            id=f"usr_{uuid.uuid4().hex[:6]}",
            email=email_clean,
            password_hash=self.hash_password(payload.password),
            role=UserRole.HOSPITAL,
            name=payload.name.strip(),
            linked_entity_id=hosp_id
        )
        self.users[email_clean] = user
        logger.info(f"Successfully registered Hospital account: {hospital.name} ({email_clean})")
        return user, hospital

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifies email and password credentials, returning user session details."""
        email_clean = email.strip().lower()
        user = self.users.get(email_clean)
        if not user:
            return None

        expected_hash = self.hash_password(password)
        if user.password_hash != expected_hash:
            return None

        # Resolve linked entity
        entity_data = None
        if user.role == UserRole.DONOR and user.linked_entity_id:
            donor = self.donors.get(user.linked_entity_id)
            if donor:
                cooldown_info = self.scheduling_service.calculate_cooldown_status(donor)
                is_eligible, reason = donor.is_eligible_to_donate()
                entity_data = {
                    **donor.model_dump(),
                    "cooldown_info": cooldown_info,
                    "is_eligible": is_eligible,
                    "eligibility_reason": reason
                }
        elif user.role == UserRole.HOSPITAL and user.linked_entity_id:
            hosp = self.hospitals.get(user.linked_entity_id)
            if hosp:
                entity_data = hosp.model_dump()

        # Session token
        token = f"token_{user.id}_{uuid.uuid4().hex[:12]}"

        return {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "linked_entity_id": user.linked_entity_id
            },
            "role": user.role,
            "entity": entity_data
        }

    def _setup_event_subscriptions(self):
        """Wires up event-driven consumers as described in Section 5.4."""
        # On RequestCreated -> Automatically schedule matching via priority queue
        self.event_bus.subscribe(EventType.REQUEST_CREATED, self._handle_request_created)
        # On DonorDeclined or NoResponseTimeout -> Escalate to next best donor
        self.event_bus.subscribe(EventType.DONOR_DECLINED, self._handle_escalation)
        self.event_bus.subscribe(EventType.NO_RESPONSE_TIMEOUT, self._handle_escalation)
        # On DonationCompleted -> Update donor cooldown
        self.event_bus.subscribe(EventType.DONATION_COMPLETED, self._handle_donation_completed)

    async def _handle_request_created(self, event):
        req_id = event.payload.get("request_id")
        logger.info(f"[Subscriber: RequestCreated] Processing request {req_id}")
        # Immediately process critical requests; others are queued in heap
        req = self.requests.get(req_id)
        if req and req.urgency == UrgencyLevel.CRITICAL:
            await self.process_matching_for_request(req)

    async def _handle_escalation(self, event):
        req_id = event.payload.get("request_id")
        donor_id = event.payload.get("donor_id")
        logger.info(f"[Subscriber: Escalation] Triggered for Request {req_id} after donor {donor_id}")
        req = self.requests.get(req_id)
        if not req or req.status in [RequestStatus.ACCEPTED, RequestStatus.FULFILLED, RequestStatus.CANCELLED]:
            return

        # Find next available candidate that hasn't been alerted yet
        already_alerted = set(req.current_alerted_donor_ids)
        next_candidate = None
        for cand in req.matched_donors:
            if cand.donor_id not in already_alerted:
                next_candidate = cand
                break

        if next_candidate:
            req.current_alerted_donor_ids.append(next_candidate.donor_id)
            notifs = self.notifications.dispatch_for_request(
                request=req,
                top_matches=[next_candidate]
            )
            await self.event_bus.publish(
                EventType.DONOR_ALERTED,
                {
                    "request_id": req.id,
                    "donor_id": next_candidate.donor_id,
                    "donor_name": next_candidate.donor_name,
                    "rank": next_candidate.rank,
                    "escalated": True
                },
                description=f"Escalated alert to #{next_candidate.rank} ranked donor: {next_candidate.donor_name}"
            )
        else:
            logger.warning(f"No further ranked candidates available for Request {req.id}")

    async def _handle_donation_completed(self, event):
        donor_id = event.payload.get("donor_id")
        req_id = event.payload.get("request_id")
        donor = self.donors.get(donor_id)
        if donor:
            self.scheduling_service.record_completed_donation(donor)
            logger.info(f"[Subscriber: DonationCompleted] Donor {donor.name} entered cooldown. Total donations: {donor.total_donations}")

    async def create_request(
        self,
        patient_name: str,
        hospital_id: str,
        blood_group: BloodGroup,
        units_required: int,
        urgency: UrgencyLevel,
        notes: Optional[str] = None
    ) -> BloodRequest:
        hosp = self.hospitals.get(hospital_id)
        if not hosp:
            raise ValueError(f"Hospital with id '{hospital_id}' not found")

        req_id = f"req_{uuid.uuid4().hex[:8]}"
        request = BloodRequest(
            id=req_id,
            patient_name=patient_name,
            hospital_id=hosp.id,
            hospital_name=hosp.name,
            blood_group=blood_group,
            units_required=units_required,
            urgency=urgency,
            latitude=hosp.latitude,
            longitude=hosp.longitude,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=RequestStatus.QUEUED,
            notes=notes
        )

        self.requests[req_id] = request
        # Insert into Priority Queue (O(log n))
        self.priority_queue.push(request)

        # Publish RequestCreated event
        await self.event_bus.publish(
            EventType.REQUEST_CREATED,
            {
                "request_id": req_id,
                "urgency": urgency.value,
                "blood_group": blood_group.value,
                "hospital": hosp.name,
                "patient": patient_name
            },
            description=f"New {urgency.value} Blood Request #{req_id} for {blood_group.value} at {hosp.name}"
        )

        return request

    async def process_next_queued_request(self) -> Optional[BloodRequest]:
        """Pops highest priority request from Priority Queue and triggers smart matching."""
        request = self.priority_queue.pop()
        if not request:
            return None
        await self.process_matching_for_request(request)
        return request

    async def process_matching_for_request(self, request: BloodRequest):
        """Runs the 4-step smart matching pipeline and notifies top donors."""
        request.status = RequestStatus.MATCHING

        # Calculate scores using MatchingService
        all_donors = list(self.donors.values())
        ranked_matches = self.matching_service.calculate_scores(
            donors=all_donors,
            request=request,
            top_n=10
        )
        request.matched_donors = ranked_matches

        # Publish DonorMatched event
        await self.event_bus.publish(
            EventType.DONOR_MATCHED,
            {
                "request_id": request.id,
                "urgency": request.urgency.value,
                "matched_count": len(ranked_matches),
                "top_donor": ranked_matches[0].donor_name if ranked_matches else "None"
            },
            description=f"Matched {len(ranked_matches)} eligible donors for Request #{request.id}"
        )

        if ranked_matches:
            request.status = RequestStatus.NOTIFYING
            # Dispatch alerts via NotificationService
            self.notifications.dispatch_for_request(request, ranked_matches)

            # Publish DonorAlerted
            alerted_names = [m.donor_name for m in ranked_matches if m.donor_id in request.current_alerted_donor_ids]
            await self.event_bus.publish(
                EventType.DONOR_ALERTED,
                {
                    "request_id": request.id,
                    "alerted_donors": alerted_names,
                    "mode": "parallel" if request.urgency == UrgencyLevel.CRITICAL else "sequential"
                },
                description=f"Alerted donors ({', '.join(alerted_names)}) for Request #{request.id}"
            )
        else:
            logger.warning(f"No eligible matching donors found for Request #{request.id}")

    async def donor_respond(self, notification_id: str, accept: bool) -> Optional[BloodRequest]:
        """Processes a donor's Accept or Decline action on an alert."""
        notif = self.notifications.record_response(notification_id, accepted=accept)
        if not notif:
            return None

        req = self.requests.get(notif.request_id)
        if not req:
            return None

        donor = self.donors.get(notif.donor_id)
        donor_name = donor.name if donor else notif.donor_name

        if accept:
            # First donor to accept claims request
            if req.status != RequestStatus.ACCEPTED and req.status != RequestStatus.FULFILLED:
                req.status = RequestStatus.ACCEPTED
                req.accepted_donor_id = notif.donor_id
                # Remove from priority queue if still present
                self.priority_queue.remove(req.id)

                await self.event_bus.publish(
                    EventType.DONOR_ACCEPTED,
                    {
                        "request_id": req.id,
                        "donor_id": notif.donor_id,
                        "donor_name": donor_name,
                        "hospital": req.hospital_name,
                        "blood_group": req.blood_group.value
                    },
                    description=f"Donor {donor_name} accepted blood donation for Request #{req.id}!"
                )
        else:
            # Donor declined -> publish event, triggers escalation
            await self.event_bus.publish(
                EventType.DONOR_DECLINED,
                {
                    "request_id": req.id,
                    "donor_id": notif.donor_id,
                    "donor_name": donor_name
                },
                description=f"Donor {donor_name} declined Request #{req.id} - initiating automatic escalation"
            )

        return req

    async def simulate_donor_timeout(self, notification_id: str) -> Optional[BloodRequest]:
        """Simulates donor failing to respond within timeout window, triggering escalation."""
        notif = self.notifications.record_timeout(notification_id)
        if not notif:
            return None

        req = self.requests.get(notif.request_id)
        if not req:
            return None

        donor = self.donors.get(notif.donor_id)
        donor_name = donor.name if donor else notif.donor_name

        await self.event_bus.publish(
            EventType.NO_RESPONSE_TIMEOUT,
            {
                "request_id": req.id,
                "donor_id": notif.donor_id,
                "donor_name": donor_name
            },
            description=f"Response timed out for {donor_name} on Request #{req.id} - escalating to next donor"
        )
        return req

    async def complete_donation(self, request_id: str) -> Optional[BloodRequest]:
        """Hospital marks the donation procedure fulfilled upon blood collection."""
        req = self.requests.get(request_id)
        if not req:
            return None

        req.status = RequestStatus.FULFILLED
        req.completed_at = datetime.now(timezone.utc).isoformat()

        donor_id = req.accepted_donor_id
        donor = self.donors.get(donor_id) if donor_id else None
        donor_name = donor.name if donor else "Unknown Donor"

        await self.event_bus.publish(
            EventType.DONATION_COMPLETED,
            {
                "request_id": req.id,
                "donor_id": donor_id,
                "donor_name": donor_name,
                "hospital": req.hospital_name,
                "units": req.units_required
            },
            description=f"Donation successfully completed for Request #{req.id}! Donor cooldown activated."
        )

        return req


# Global Application State singleton
app_state = AppState()
