"""
Unit tests for Min-Heap Priority Queue
Verifies:
1. Urgency priority: Critical (1) > Urgent (2) > Normal (3)
2. Starvation prevention: Tie-breaking by arrival time (FIFO within urgency level)
3. Heap insertion and extraction correctness.
"""

import pytest
import time
from backend.models import BloodRequest, BloodGroup, UrgencyLevel
from backend.priority_queue import RequestPriorityQueue


def create_req(req_id: str, urgency: UrgencyLevel) -> BloodRequest:
    return BloodRequest(
        id=req_id,
        patient_name=f"Patient {req_id}",
        hospital_id="hosp_1",
        hospital_name="Hospital 1",
        blood_group=BloodGroup.O_POS,
        urgency=urgency,
        latitude=30.73,
        longitude=76.78
    )


def test_urgency_ordering():
    """Verify that Critical requests pop before Urgent, and Urgent before Normal."""
    pq = RequestPriorityQueue()

    req_norm = create_req("req_normal", UrgencyLevel.NORMAL)
    req_urg = create_req("req_urgent", UrgencyLevel.URGENT)
    req_crit = create_req("req_critical", UrgencyLevel.CRITICAL)

    # Push in reverse order
    pq.push(req_norm)
    pq.push(req_urg)
    pq.push(req_crit)

    assert pq.size() == 3

    popped1 = pq.pop()
    assert popped1.id == "req_critical"
    assert popped1.urgency == UrgencyLevel.CRITICAL

    popped2 = pq.pop()
    assert popped2.id == "req_urgent"
    assert popped2.urgency == UrgencyLevel.URGENT

    popped3 = pq.pop()
    assert popped3.id == "req_normal"
    assert popped3.urgency == UrgencyLevel.NORMAL

    assert pq.is_empty() is True


def test_waiting_time_tiebreaker_prevents_starvation():
    """Two requests with the same urgency level must be popped in FIFO order of arrival."""
    pq = RequestPriorityQueue()

    r1 = create_req("r1_first", UrgencyLevel.NORMAL)
    pq.push(r1)
    time.sleep(0.01)  # Ensure distinct arrival timestamp
    r2 = create_req("r2_second", UrgencyLevel.NORMAL)
    pq.push(r2)

    assert pq.pop().id == "r1_first"
    assert pq.pop().id == "r2_second"


def test_remove_by_id():
    """Removing a request from queue updates size and avoids popping it."""
    pq = RequestPriorityQueue()
    r1 = create_req("req_1", UrgencyLevel.CRITICAL)
    r2 = create_req("req_2", UrgencyLevel.NORMAL)
    pq.push(r1)
    pq.push(r2)

    assert pq.remove("req_1") is True
    assert pq.size() == 1
    assert pq.pop().id == "req_2"
