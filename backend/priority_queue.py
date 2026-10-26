"""
Priority Queue Service for Blood Requests
Implements a min-heap priority queue ordered by:
1. Urgency level: Critical (1) > Urgent (2) > Normal (3)
2. Waiting time (arrival timestamp): Earliest request served first to prevent starvation
Time Complexity: O(log n) for push and pop operations.
"""

import heapq
import time
from typing import Optional, List, Tuple, Dict, Any
from backend.models import BloodRequest, UrgencyLevel


class RequestPriorityQueue:
    # Priority ranks (lower number = higher priority in min-heap)
    URGENCY_RANK = {
        UrgencyLevel.CRITICAL: 1,
        UrgencyLevel.URGENT: 2,
        UrgencyLevel.NORMAL: 3
    }

    def __init__(self):
        # Heap elements: (urgency_rank, arrival_timestamp, entry_count, request_id, BloodRequest)
        self._heap: List[Tuple[int, float, int, str, BloodRequest]] = []
        self._entry_map: Dict[str, Tuple[int, float, int, str, BloodRequest]] = {}
        self._entry_counter: int = 0

    def push(self, request: BloodRequest) -> None:
        """
        Inserts a request into the priority queue.
        Time Complexity: O(log n)
        """
        if request.id in self._entry_map:
            # Update existing
            self.remove(request.id)

        rank = self.URGENCY_RANK.get(request.urgency, 3)
        # Parse or use arrival timestamp
        arrival_ts = time.time()
        self._entry_counter += 1
        entry = (rank, arrival_ts, self._entry_counter, request.id, request)
        self._entry_map[request.id] = entry
        heapq.heappush(self._heap, entry)

    def pop(self) -> Optional[BloodRequest]:
        """
        Extracts the highest priority request.
        Critical requests extracted before Urgent, Urgent before Normal.
        Ties resolved by arrival time (earliest first, preventing starvation).
        Time Complexity: O(log n)
        """
        while self._heap:
            rank, arrival_ts, count, req_id, request = heapq.heappop(self._heap)
            if req_id in self._entry_map and self._entry_map[req_id][2] == count:
                del self._entry_map[req_id]
                # Record queue wait time in milliseconds
                wait_time_ms = (time.time() - arrival_ts) * 1000.0
                request.queue_wait_time_ms = round(wait_time_ms, 2)
                return request
        return None

    def peek(self) -> Optional[BloodRequest]:
        """Returns the highest priority request without removing it. O(1)"""
        while self._heap:
            rank, arrival_ts, count, req_id, request = self._heap[0]
            if req_id in self._entry_map and self._entry_map[req_id][2] == count:
                return request
            heapq.heappop(self._heap)
        return None

    def remove(self, request_id: str) -> bool:
        """Mark item as removed (lazy removal) in O(1)"""
        if request_id in self._entry_map:
            del self._entry_map[request_id]
            return True
        return False

    def size(self) -> int:
        return len(self._entry_map)

    def is_empty(self) -> bool:
        return len(self._entry_map) == 0

    def get_queue_view(self) -> List[Dict[str, Any]]:
        """
        Returns a snapshot of the current queue sorted in exact priority order
        for UI visualization and auditing without mutating the heap.
        """
        valid_entries = [
            e for e in self._heap
            if e[3] in self._entry_map and self._entry_map[e[3]][2] == e[2]
        ]
        sorted_entries = sorted(valid_entries, key=lambda x: (x[0], x[1]))
        now = time.time()
        result = []
        for rank, arrival_ts, _, req_id, req in sorted_entries:
            result.append({
                "request_id": req.id,
                "patient_name": req.patient_name,
                "hospital_name": req.hospital_name,
                "blood_group": req.blood_group.value,
                "urgency": req.urgency.value,
                "urgency_rank": rank,
                "wait_seconds": round(now - arrival_ts, 1),
                "created_at": req.created_at
            })
        return result
