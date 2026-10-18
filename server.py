"""
server.py
FastAPI + WebSocket Server for Robuverse Robot QR Scanner.

Serves the live real-time dashboard to any connected laptop or mobile device
and broadcasts QR scans instantly as they happen.
"""

import os
import sys
import socket
import asyncio
import datetime
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from scanner_reader import QRScannerListener

# App configuration
PORT = 8000
HOST = "0.0.0.0"

# State
connected_websockets: List[WebSocket] = []
scan_history: List[Dict[str, Any]] = []
main_loop: asyncio.AbstractEventLoop = None
scanner_listener: QRScannerListener = None


def get_local_ip() -> str:
    """Detect the local IP address on the Wi-Fi network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def broadcast_scan(data: Dict[str, Any]):
    """Broadcast scan event to all connected WebSocket clients."""
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


def on_hardware_scan(scanned_value: str, source: str = "USB Scanner"):
    """Callback fired when a physical or simulated scan occurs."""
    scan_item = {
        "id": len(scan_history) + 1,
        "value": scanned_value,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_short": datetime.datetime.now().strftime("%H:%M:%S"),
        "source": source
    }
    scan_history.insert(0, scan_item)
    if len(scan_history) > 100:
        scan_history.pop()

    payload = {
        "type": "NEW_SCAN",
        "data": scan_item,
        "total_scans": len(scan_history)
    }

    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_scan(payload), main_loop)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop, scanner_listener
    main_loop = asyncio.get_running_loop()
    
    # Start scanner hardware reader
    scanner_listener = QRScannerListener(on_scan_callback=on_hardware_scan)
    scanner_listener.start()
    
    local_ip = get_local_ip()
    print("=" * 60)
    print(" ROBUVERSE QR SCANNER SERVER STARTED")
    print("=" * 60)
    print(f" Local Web Dashboard : http://localhost:{PORT}")
    print(f" Network Dashboard   : http://{local_ip}:{PORT}")
    print(f" System Mode         : {'Linux / Raspberry Pi' if sys.platform.startswith('linux') else 'Windows / Dev'}")
    print("=" * 60)
    
    yield
    
    if scanner_listener:
        scanner_listener.stop()


app = FastAPI(title="Robuverse QR Scanner", lifespan=lifespan)

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def get_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Robuverse QR Scanner Server Running"}


@app.get("/api/info")
async def get_info():
    return {
        "local_ip": get_local_ip(),
        "port": PORT,
        "platform": sys.platform,
        "scanner_device": scanner_listener.device_name if scanner_listener else "Unknown",
        "connected_clients": len(connected_websockets),
        "total_scans": len(scan_history)
    }


@app.get("/api/history")
async def get_history():
    return {"history": scan_history}


class ManualScanPayload(BaseModel):
    value: str
    source: str = "Manual Simulation"


@app.post("/api/scan")
async def trigger_scan(payload: ManualScanPayload):
    if not payload.value.strip():
        return JSONResponse(status_code=400, content={"error": "Value cannot be empty"})
    on_hardware_scan(payload.value.strip(), source=payload.source)
    return {"status": "success", "scanned": payload.value}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    
    # Send initial status & history on connection
    await websocket.send_json({
        "type": "INIT_STATE",
        "local_ip": get_local_ip(),
        "port": PORT,
        "history": scan_history[:10],
        "total_scans": len(scan_history)
    })
    
    try:
        while True:
            # Keep connection alive & handle incoming pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
