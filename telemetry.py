import asyncio
from typing import List
from fastapi import WebSocket
from config import logger

# ==========================================
# WEBSOCKET TELEMETRY MANAGER
# ==========================================
class TelemetryManager:
    """
    Manages full-duplex WebSocket connections for streaming real-time 
    logs and metrics to the ops dashboard interface.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts a new connection and adds it to the active pool."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[TELEMETRY] Dashboard node attached. Channels open: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Removes a dropped or closed connection from the pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[TELEMETRY] Dashboard node detached. Channels open: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict):
        """
        Dispatches operational signals concurrently across all channels.
        Uses asyncio.gather to prevent blocking the main event loop if one client is slow.
        """
        if not self.active_connections:
            return
            
        payload = {"type": event_type, "data": data}
        
        # Dispatch JSON payloads to all connected clients simultaneously
        tasks = [connection.send_json(payload) for connection in self.active_connections]
        
        # Return exceptions as values so a single failed socket doesn't crash the broadcast
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up any explicitly broken pipes immediately
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                try:
                    stale_ws = self.active_connections[idx]
                    self.disconnect(stale_ws)
                except (IndexError, ValueError):
                    pass

# Expose a global singleton to be imported by main.py
stream = TelemetryManager()