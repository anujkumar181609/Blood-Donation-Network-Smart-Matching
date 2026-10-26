"""
Notification Service & Escalation Engine
Consumes events and manages multi-channel notifications (In-App, SMS, Email simulation).
Tracks dispatch logs, responses, timeouts, and handles automatic escalation.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import uuid
import logging
from backend.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    BloodRequest,
    BloodMatchScore,
    UrgencyLevel
)

logger = logging.getLogger("NotificationService")


class NotificationService:
    def __init__(self):
        # In-memory storage for notification log
        self._notifications: Dict[str, Notification] = {}
        # Map: request_id -> list of notification_ids
        self._request_notifications: Dict[str, List[str]] = {}

    def send_alert(
        self,
        request: BloodRequest,
        match: BloodMatchScore,
        channel: NotificationChannel = NotificationChannel.IN_APP
    ) -> Notification:
        """
        Dispatches a notification to a matched donor across specified channel.
        Simulates SMS gateway, SMTP Email, and creates In-App alert record.
        """
        notif_id = f"notif_{uuid.uuid4().hex[:8]}"

        urgency_tag = f"🚨 [{request.urgency.value.upper()} EMERGENCY]" if request.urgency == UrgencyLevel.CRITICAL else f"⚠️ [{request.urgency.value}]"

        msg = (
            f"{urgency_tag} Urgent blood requirement for {request.blood_group.value} at "
            f"{request.hospital_name} (~{match.distance_km} km away). "
            f"Patient: {request.patient_name}. "
            f"Your match score: {int(match.total_score * 100)}%. "
            f"Can you donate now?"
        )

        notification = Notification(
            id=notif_id,
            request_id=request.id,
            donor_id=match.donor_id,
            donor_name=match.donor_name,
            donor_phone=match.donor_phone,
            donor_email=f"{match.donor_name.lower().replace(' ', '.')}@example.com",
            blood_group_needed=request.blood_group,
            urgency=request.urgency,
            hospital_name=request.hospital_name,
            distance_km=match.distance_km,
            channel=channel,
            message=msg,
            status=NotificationStatus.DELIVERED,
            sent_at=datetime.now(timezone.utc).isoformat()
        )

        self._notifications[notif_id] = notification
        if request.id not in self._request_notifications:
            self._request_notifications[request.id] = []
        self._request_notifications[request.id].append(notif_id)

        logger.info(
            f"[{channel.value.upper()} SENT] To {match.donor_name} ({match.donor_phone}) "
            f"for Request #{request.id} ({request.urgency.value})"
        )
        return notification

    def dispatch_for_request(
        self,
        request: BloodRequest,
        top_matches: List[BloodMatchScore],
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[Notification]:
        """
        Dispatches alerts according to urgency policy:
        - Critical: Parallel alerts sent to top matches across In-App, SMS, and Email.
        - Urgent: Sequential alert to top 1 candidate.
        - Normal: Alert to top 1 candidate.
        """
        if not top_matches:
            return []

        active_channels = channels or [
            NotificationChannel.IN_APP,
            NotificationChannel.SMS,
            NotificationChannel.EMAIL
        ]
        created_alerts = []

        if request.urgency == UrgencyLevel.CRITICAL:
            # Parallel alerts to top N candidates (up to 3)
            candidates_to_alert = top_matches[:3]
            for cand in candidates_to_alert:
                for ch in active_channels:
                    alert = self.send_alert(request, cand, ch)
                    created_alerts.append(alert)
                if cand.donor_id not in request.current_alerted_donor_ids:
                    request.current_alerted_donor_ids.append(cand.donor_id)
        else:
            # Sequential alert to the highest-ranked candidate
            top_cand = top_matches[0]
            for ch in active_channels:
                alert = self.send_alert(request, top_cand, ch)
                created_alerts.append(alert)
            if top_cand.donor_id not in request.current_alerted_donor_ids:
                request.current_alerted_donor_ids.append(top_cand.donor_id)

        return created_alerts

    def record_response(self, notification_id: str, accepted: bool) -> Optional[Notification]:
        """Records whether donor accepted or declined."""
        if notification_id not in self._notifications:
            return None
        notif = self._notifications[notification_id]
        notif.status = NotificationStatus.ACCEPTED if accepted else NotificationStatus.DECLINED
        notif.responded_at = datetime.now(timezone.utc).isoformat()
        return notif

    def record_timeout(self, notification_id: str) -> Optional[Notification]:
        """Records no-response timeout on a notification."""
        if notification_id not in self._notifications:
            return None
        notif = self._notifications[notification_id]
        notif.status = NotificationStatus.TIMED_OUT
        notif.responded_at = datetime.now(timezone.utc).isoformat()
        return notif

    def get_notifications_for_donor(self, donor_id: str) -> List[Notification]:
        return [
            n for n in self._notifications.values()
            if n.donor_id == donor_id
        ]

    def get_notifications_for_request(self, request_id: str) -> List[Notification]:
        return [
            n for n in self._notifications.values()
            if n.request_id == request_id
        ]

    def get_all_notifications(self, limit: int = 100) -> List[Notification]:
        items = list(self._notifications.values())
        items.sort(key=lambda x: x.sent_at, reverse=True)
        return items[:limit]
