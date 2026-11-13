import asyncio
import time
from backend.app.connection_approval import ApprovalManager


def test_request_requires_explicit_approval():
    async def scenario():
        manager = ApprovalManager()
        request = manager.create("192.0.2.10:4321")
        waiter = asyncio.create_task(manager.wait(request))
        await asyncio.sleep(0)
        assert manager.list_pending()[0]["client_ip"] == "192.0.2.10:4321"
        assert manager.decide(request.request_id, "approved") is True
        assert await waiter is True
        assert manager.decide(request.request_id, "approved") is False
    asyncio.run(scenario())


def test_rejection_is_final():
    async def scenario():
        manager = ApprovalManager()
        request = manager.create("192.0.2.11:4321")
        waiter = asyncio.create_task(manager.wait(request))
        await asyncio.sleep(0)
        assert manager.decide(request.request_id, "rejected") is True
        assert await waiter is False
        assert manager.decide(request.request_id, "approved") is False
    asyncio.run(scenario())


def test_expired_request_cannot_be_approved():
    async def scenario():
        manager = ApprovalManager()
        request = manager.create("192.0.2.12:4321")
        request.created_at = time.time() - 31
        assert manager.decide(request.request_id, "approved") is False
        assert manager.list_pending() == []
        assert request.decision == "timeout"
    asyncio.run(scenario())
