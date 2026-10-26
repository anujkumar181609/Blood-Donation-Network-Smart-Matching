"""
Event Bus Implementation for Event-Driven Blood Donation Network
Handles decoupled publisher/subscriber communication for:
- RequestCreated
- DonorMatched
- DonorAlerted
- DonorAccepted
- DonorDeclined
- NoResponseTimeout
- DonationCompleted
"""

import asyncio
import logging
from typing import Callable, Dict, List, Any
from datetime import datetime, timezone
import uuid
from backend.models import EventType, SystemEvent

logger = logging.getLogger("EventBus")


class EventBus:
    def __init__(self, max_history: int = 200):
        self._subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.history: List[SystemEvent] = []
        self.max_history = max_history
        self._ws_listeners: List[Callable] = []

    def subscribe(self, event_type: EventType, handler: Callable):
        """Registers a synchronous or asynchronous handler for a given event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler '{handler.__name__}' to {event_type.value}")

    def add_ws_listener(self, listener: Callable):
        """Register listener for real-time streaming to UI/WebSockets."""
        self._ws_listeners.append(listener)

    def remove_ws_listener(self, listener: Callable):
        if listener in self._ws_listeners:
            self._ws_listeners.remove(listener)

    async def publish(self, event_type: EventType, payload: Dict[str, Any], description: str = "") -> SystemEvent:
        """Publishes an event to all registered subscribers asynchronously."""
        event = SystemEvent(
            id=str(uuid.uuid4())[:8],
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
            description=description or f"Event {event_type.value} emitted"
        )

        # Store in circular event history
        self.history.append(event)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        logger.info(f"[EVENT EMITTED] {event.event_type.value}: {event.description}")

        # Notify WebSocket listeners
        for ws_listener in self._ws_listeners:
            try:
                if asyncio.iscoroutinefunction(ws_listener):
                    await ws_listener(event)
                else:
                    ws_listener(event)
            except Exception as e:
                logger.error(f"Error in WS listener: {e}")

        # Invoke all subscribers
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Launch task so handlers don't block one another
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as ex:
                logger.exception(f"Error executing subscriber for {event_type.value}: {ex}")

        return event

    def get_recent_events(self, limit: int = 50) -> List[SystemEvent]:
        return list(reversed(self.history[-limit:]))

    def clear(self):
        self.history.clear()


# Global singleton instance
global_event_bus = EventBus()
