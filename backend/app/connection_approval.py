"""In-memory, single-use approval gate for inbound TCP sessions.

Approval is deliberately per connection and is never persisted as trust.
The API is intended for the receiver's local control panel.
"""
from __future__ import annotations
import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

APPROVAL_TIMEOUT_SECONDS = 30

@dataclass
class ConnectionRequest:
    request_id: str
    client_ip: str
    created_at: float
    loop: asyncio.AbstractEventLoop
    decision_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: Optional[str] = None

    def public(self):
        return {
            "request_id": self.request_id,
            "device_name": "Unverified device",
            "device_type": "Unknown",
            "client_ip": self.client_ip,
            "created_at": self.created_at,
            "expires_in": max(0, int(APPROVAL_TIMEOUT_SECONDS - (time.time() - self.created_at))),
            "status": "pending",
        }

class ApprovalManager:
    def __init__(self):
        self._items: Dict[str, ConnectionRequest] = {}
        self._lock = threading.RLock()

    def create(self, client_ip: str) -> ConnectionRequest:
        loop = asyncio.get_running_loop()
        item = ConnectionRequest(uuid.uuid4().hex, client_ip, time.time(), loop)
        with self._lock:
            self._items[item.request_id] = item
        return item

    async def wait(self, item: ConnectionRequest) -> bool:
        try:
            await asyncio.wait_for(item.decision_event.wait(), timeout=APPROVAL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            item.decision = "timeout"
        finally:
            with self._lock:
                self._items.pop(item.request_id, None)
        return item.decision == "approved"

    def list_pending(self):
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._items.items() if now - v.created_at >= APPROVAL_TIMEOUT_SECONDS]
            for key in expired:
                item = self._items.pop(key)
                item.decision = "timeout"
                item.loop.call_soon_threadsafe(item.decision_event.set)
            return [v.public() for v in self._items.values() if v.decision is None]

    def decide(self, request_id: str, decision: str) -> bool:
        if decision not in {"approved", "rejected"}:
            return False
        with self._lock:
            item = self._items.get(request_id)
            if not item or item.decision is not None or time.time() - item.created_at >= APPROVAL_TIMEOUT_SECONDS:
                return False
            item.decision = decision
            item.loop.call_soon_threadsafe(item.decision_event.set)
            return True

approval_manager = ApprovalManager()
