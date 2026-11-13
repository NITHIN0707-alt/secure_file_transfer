import time
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from backend.app.database import get_db

router = APIRouter(prefix="/devices", tags=["devices"])

class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str
    device_type: Optional[str] = "desktop"

class DeviceRename(BaseModel):
    device_id: str
    new_name: str

@router.post("/heartbeat")
def device_heartbeat(data: DeviceHeartbeat, request: Request):
    """
    Registers or refreshes device presence on the local network.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO connected_devices (device_id, device_name, device_type, client_ip, last_seen)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(device_id) DO UPDATE SET
        device_name = excluded.device_name,
        device_type = excluded.device_type,
        client_ip = excluded.client_ip,
        last_seen = CURRENT_TIMESTAMP
    """, (data.device_id, data.device_name, data.device_type, client_ip))

    conn.commit()
    conn.close()

    return {"status": "ok", "device_id": data.device_id, "device_name": data.device_name}

@router.get("")
def list_devices():
    """
    Lists all devices active within the last 60 seconds.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Clean up devices not seen for over 2 minutes
    cursor.execute("DELETE FROM connected_devices WHERE last_seen < datetime('now', '-2 minutes')")
    conn.commit()

    # Active devices in last 60 seconds
    cursor.execute("""
    SELECT device_id, device_name, device_type, client_ip, last_seen
    FROM connected_devices
    WHERE last_seen >= datetime('now', '-60 seconds')
    ORDER BY last_seen DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

@router.post("/rename")
def rename_device(data: DeviceRename):
    """
    Renames a specific device.
    """
    if not data.new_name.strip():
        raise HTTPException(status_code=400, detail="Device name cannot be empty")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE connected_devices SET device_name = ? WHERE device_id = ?",
        (data.new_name.strip(), data.device_id)
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "device_id": data.device_id, "new_name": data.new_name.strip()}

# Receiver-controlled, one-time TCP connection approval.
from pydantic import BaseModel
from backend.app.connection_approval import approval_manager

class ConnectionDecision(BaseModel):
    decision: str

def _require_local_receiver(request: Request):
    # The current control plane has no administrator session system. Keep
    # approval controls loopback-only rather than exposing them to LAN clients.
    import ipaddress
    host = request.client.host if request.client else ""
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise HTTPException(status_code=403, detail="Connection approval is available only from the receiver machine")
    except ValueError:
        raise HTTPException(status_code=403, detail="Unable to verify local receiver access")

@router.get("/connection-requests/pending")
def pending_connection_requests(request: Request):
    _require_local_receiver(request)
    return approval_manager.list_pending()

@router.post("/connection-requests/{request_id}/decision")
def decide_connection_request(request_id: str, data: ConnectionDecision, request: Request):
    _require_local_receiver(request)
    if data.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Decision must be approved or rejected")
    if not approval_manager.decide(request_id, data.decision):
        raise HTTPException(status_code=404, detail="Request expired or no longer pending")
    return {"status": data.decision, "request_id": request_id}
