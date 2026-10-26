"""
Integration tests for the Event-Driven Life Cycle
Tests Section 5.4 event flow:
RequestCreated -> DonorMatched -> DonorAlerted -> DonorDeclined
  -> Escalation -> DonorAccepted -> DonationCompleted -> Cooldown
"""

import pytest
import asyncio
from backend.models import BloodGroup, UrgencyLevel, RequestStatus, EventType
from backend.database import AppState


@pytest.mark.asyncio
async def test_full_event_driven_escalation_flow():
    # Fresh test state with 15 donors
    state = AppState()
    state.reset_to_default_seed(donor_count=15)

    # 1. Create a Blood Request
    req = await state.create_request(
        patient_name="Pooja Sharma",
        hospital_id="hosp_pgimer",
        blood_group=BloodGroup.O_POS,
        units_required=1,
        urgency=UrgencyLevel.URGENT,
        notes="Accident surgery case"
    )
    assert req.status == RequestStatus.QUEUED
    assert state.priority_queue.size() == 1

    # 2. Process matching via priority queue
    processed_req = await state.process_next_queued_request()
    assert processed_req.id == req.id
    assert processed_req.status == RequestStatus.NOTIFYING
    assert len(processed_req.matched_donors) > 0

    first_donor_id = processed_req.matched_donors[0].donor_id
    donor_alerts = state.notifications.get_notifications_for_donor(first_donor_id)
    assert len(donor_alerts) > 0
    first_notif = donor_alerts[0]

    # 3. First donor declines -> triggers automatic escalation
    await state.donor_respond(first_notif.id, accept=False)

    # Small sleep to allow async event bus subscriber task to run
    await asyncio.sleep(0.05)

    # Escalation should have alerted the second donor
    assert len(processed_req.current_alerted_donor_ids) >= 2
    second_donor_id = processed_req.current_alerted_donor_ids[1]
    second_donor_alerts = state.notifications.get_notifications_for_donor(second_donor_id)
    assert len(second_donor_alerts) > 0
    second_notif = second_donor_alerts[0]

    # 4. Second donor accepts!
    await state.donor_respond(second_notif.id, accept=True)
    await asyncio.sleep(0.05)

    assert processed_req.status == RequestStatus.ACCEPTED
    assert processed_req.accepted_donor_id == second_donor_id

    # 5. Complete donation procedure
    accepted_donor = state.donors[second_donor_id]
    donations_before = accepted_donor.total_donations

    await state.complete_donation(processed_req.id)
    await asyncio.sleep(0.05)

    assert processed_req.status == RequestStatus.FULFILLED
    assert accepted_donor.total_donations == donations_before + 1
    assert accepted_donor.cooldown_days_remaining() > 0


@pytest.mark.asyncio
async def test_no_response_timeout_escalation():
    """Simulates a donor timing out and verifies automatic escalation."""
    state = AppState()
    state.reset_to_default_seed(donor_count=15)

    req = await state.create_request(
        patient_name="Vikram Singh",
        hospital_id="hosp_fortis",
        blood_group=BloodGroup.B_POS,
        units_required=1,
        urgency=UrgencyLevel.URGENT
    )

    await state.process_matching_for_request(req)
    assert len(req.matched_donors) >= 2

    first_donor_id = req.matched_donors[0].donor_id
    notif = state.notifications.get_notifications_for_donor(first_donor_id)[0]

    # Trigger timeout
    await state.simulate_donor_timeout(notif.id)
    await asyncio.sleep(0.05)

    # Verified that second candidate was alerted
    assert len(req.current_alerted_donor_ids) >= 2
