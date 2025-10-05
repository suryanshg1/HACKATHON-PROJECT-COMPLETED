import asyncio
import websockets
import json
from datetime import datetime

class WebRTCSignalingServer:
    def __init__(self):
        self.clients = {}  # Maps client_ip -> websocket connection
        self.usernames = {}  # Maps client_ip -> username

    async def handle_websocket(self, websocket, path):
        client_ip = websocket.remote_address[0]
        print(f"New client connected: {client_ip}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')

                    print(f"Received {msg_type} from {client_ip}: {message[:100]}...")

                    if msg_type == 'register':
                        # Register client
                        username = data.get('username', client_ip)
                        self.clients[client_ip] = websocket
                        self.usernames[client_ip] = username
                        print(f"Registered {username} ({client_ip})")

                        # Send peer list
                        await self._broadcast_peer_list()

                    elif msg_type in ['offer', 'answer', 'ice-candidate', 'call-rejected']:
                        # Forward WebRTC signaling messages to target peer
                        target_ip = data.get('target')
                        if target_ip and target_ip in self.clients:
                            # Add sender info
                            data['sender'] = client_ip
                            target_ws = self.clients[target_ip]
                            await target_ws.send(json.dumps(data))
                            print(f"Forwarded {msg_type} from {client_ip} to {target_ip}")
                        else:
                            print(f"Target {target_ip} not found or not connected")

                    else:
                        # Echo unknown message types
                        await websocket.send(f"Echo: {message}")

                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")
                except Exception as e:
                    print(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_ip} disconnected.")
        finally:
            # Clean up on disconnect
            if client_ip in self.clients:
                del self.clients[client_ip]
            if client_ip in self.usernames:
                del self.usernames[client_ip]
            await self._broadcast_peer_list()

    async def _broadcast_peer_list(self):
        """Send updated peer list to all connected clients"""
        peers = [
            {'ip': ip, 'username': username}
            for ip, username in self.usernames.items()
        ]

        message = {
            'type': 'peer_list',
            'peers': peers,
            'timestamp': datetime.now().isoformat()
        }

        # Broadcast to all connected clients
        disconnected = []
        for client_ip, ws in self.clients.items():
            try:
                await ws.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client_ip)

        # Clean up disconnected clients
        for client_ip in disconnected:
            if client_ip in self.clients:
                del self.clients[client_ip]
            if client_ip in self.usernames:
                del self.usernames[client_ip]

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 12345
    server = WebRTCSignalingServer()
    start_server = websockets.serve(server.handle_websocket, host, port)
    print(f"WebSocket server running at ws://{host}:{port}")
    print("Ready to handle WebRTC signaling and peer discovery")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
