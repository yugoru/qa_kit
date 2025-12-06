from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from fastapi import WebSocket


@dataclass
class ChannelHub:
    channels: Dict[str, Set[WebSocket]] = field(default_factory=dict)

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        self.channels.setdefault(channel, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if channel in self.channels:
            self.channels[channel].discard(websocket)
            if not self.channels[channel]:
                self.channels.pop(channel, None)

    async def broadcast_text(self, channel: str, message: str) -> int:
        """Return number of connections attempted."""
        conns = list(self.channels.get(channel, set()))
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                # silently drop dead sockets
                self.disconnect(ws, channel)
        return len(conns)

    async def broadcast_json(self, channel: str, payload: dict) -> int:
        conns = list(self.channels.get(channel, set()))
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(ws, channel)
        return len(conns)

    def stats(self) -> dict:
        return {
            "channels": {
                name: len(conns) for name, conns in self.channels.items()
            },
            "total_connections": sum(len(c) for c in self.channels.values()),
        }


hub = ChannelHub()
