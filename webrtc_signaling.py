import json
import asyncio
import websockets
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class CallSignaling:
    type: str  # offer, answer, ice-candidate
    sender: str
    target: str
    data: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
            
    def to_json(self):
        return json.dumps(asdict(self))

class RTCSignalingHandler:
    def __init__(self):
        self.connections = {}  # Store active WebSocket connections
        self.calls = {}  # Store active calls
        
    async def handle_connection(self, websocket, path):
        """Handle a new WebSocket connection"""
        client_id = None
        try:
            # Wait for client registration
            async for message in websocket:
                data = json.loads(message)
                
                if data['type'] == 'register':
                    # Register new client
                    client_id = data['username']
                    self.connections[client_id] = websocket
                    await self._broadcast_peer_list()
                    
                elif data['type'] == 'offer':
                    # Handle call offer
                    signaling = CallSignaling(
                        type='offer',
                        sender=client_id,
                        target=data['target'],
                        data=data['sdp']
                    )
                    await self._forward_signaling(signaling)
                    
                elif data['type'] == 'answer':
                    # Handle call answer
                    signaling = CallSignaling(
                        type='answer',
                        sender=client_id,
                        target=data['target'],
                        data=data['sdp']
                    )
                    await self._forward_signaling(signaling)
                    
                elif data['type'] == 'ice-candidate':
                    # Handle ICE candidate
                    signaling = CallSignaling(
                        type='ice-candidate',
                        sender=client_id,
                        target=data['target'],
                        data=data['candidate']
                    )
                    await self._forward_signaling(signaling)
                    
                elif data['type'] == 'end-call':
                    # Handle call end
                    if client_id in self.calls:
                        other_peer = self.calls[client_id]
                        await self._end_call(client_id, other_peer)
                        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if client_id:
                # Clean up when client disconnects
                await self._handle_disconnect(client_id)
                
    async def _forward_signaling(self, signaling: CallSignaling):
        """Forward signaling message to target peer"""
        target_ws = self.connections.get(signaling.target)
        if target_ws:
            try:
                await target_ws.send(signaling.to_json())
            except websockets.exceptions.ConnectionClosed:
                await self._handle_disconnect(signaling.target)
                
    async def _broadcast_peer_list(self):
        """Send updated peer list to all connected clients"""
        peers = list(self.connections.keys())
        message = {
            'type': 'peer-list',
            'peers': peers,
            'timestamp': datetime.now().isoformat()
        }
        
        # Broadcast to all connected clients
        for ws in self.connections.values():
            try:
                await ws.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                continue
                
    async def _handle_disconnect(self, client_id: str):
        """Clean up when a client disconnects"""
        # Remove from connections
        if client_id in self.connections:
            del self.connections[client_id]
            
        # End any active calls
        if client_id in self.calls:
            other_peer = self.calls[client_id]
            await self._end_call(client_id, other_peer)
            
        # Update peer list
        await self._broadcast_peer_list()
        
    async def _end_call(self, peer1: str, peer2: str):
        """End call between two peers"""
        # Send end-call signal to both peers
        end_call_msg = {'type': 'end-call', 'timestamp': datetime.now().isoformat()}
        
        for peer_id in [peer1, peer2]:
            ws = self.connections.get(peer_id)
            if ws:
                try:
                    await ws.send(json.dumps(end_call_msg))
                except websockets.exceptions.ConnectionClosed:
                    continue
                    
        # Clean up call state
        if peer1 in self.calls:
            del self.calls[peer1]
        if peer2 in self.calls:
            del self.calls[peer2]

async def start_signaling_server(host='localhost', port=12346):
    """Start the WebRTC signaling server"""
    handler = RTCSignalingHandler()
    server = await websockets.serve(handler.handle_connection, host, port)
    print(f"🎥 WebRTC signaling server started on ws://{host}:{port}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_signaling_server())