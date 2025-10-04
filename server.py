import asyncio
import websockets
import socket
import json
import time
from datetime import datetime
# We no longer need MessageHandler, so the import is removed.
from peer_discovery import PeerDiscovery

class LANServer:
    def __init__(self, host='0.0.0.0', port=12345, username="Anonymous"):
        self.host = host
        self.port = port
        self.username = username
        self.peers = {}
        # self.handler is no longer needed.
        self.peer_discovery = PeerDiscovery(username, listen_port=port)
        self.available_peers = {}
        self.loop = asyncio.get_event_loop()

    def on_peer_discovered(self, peer_info):
        self.available_peers[peer_info['ip']] = {
            'username': peer_info['username'],
            'last_seen': time.time()
        }
        asyncio.run_coroutine_threadsafe(self.broadcast_peer_list(), self.loop)

    async def broadcast_peer_list(self):
        current_time = time.time()
        self.available_peers = {
            ip: info for ip, info in self.available_peers.items()
            if current_time - info['last_seen'] < 30
        }
        peer_list_message = {
            'type': 'peer_list',
            'peers': [
                {'ip': ip, 'username': info['username']}
                for ip, info in self.available_peers.items()
            ]
        }
        remove = []
        for peer_info, websocket in list(self.peers.items()):
            try:
                await websocket.send(json.dumps(peer_list_message))
            except Exception as e:
                print(f"Error broadcasting: {e}")
                remove.append(peer_info)
        for p in remove:
            self.peers.pop(p, None)

    async def handle_websocket(self, websocket):
        peer_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.peers[peer_info] = websocket
        print(f"🔗 New connection from {peer_info}")
        try:
            await self.broadcast_peer_list()
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # THIS IS THE KEY CHANGE: We call a method on self, not self.handler
                    await self.process_message(data, websocket)
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON from {peer_info}")
        except websockets.exceptions.ConnectionClosed:
            print(f"👋 Client {peer_info} disconnected")
        finally:
            self.peers.pop(peer_info, None)
            await self.broadcast_peer_list()

    def get_local_ips(self):
        ips = []
        try:
            # Get hostname and resolve to IP - works without internet
            hostname = socket.gethostname()
            # Get all IP addresses for this host
            ip_addresses = socket.getaddrinfo(hostname, None, socket.AF_INET)

            # Collect all private/LAN IPs
            for addr_info in ip_addresses:
                ip = addr_info[4][0]
                # Add LAN IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
                if ip.startswith('192.168.') or ip.startswith('10.') or \
                   (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31):
                    ips.append(ip)

            # If no private IPs found, add any non-localhost IP
            if not ips:
                for addr_info in ip_addresses:
                    ip = addr_info[4][0]
                    if ip != '127.0.0.1':
                        ips.append(ip)

            # If still no IPs found, fallback to localhost
            if not ips:
                ips.append('127.0.0.1')

        except Exception:
            ips.append('127.0.0.1')

        return list(set(ips))

    async def start_server(self):
        try:
            if self.peer_discovery:
                self.peer_discovery.on_peer_discovered = self.on_peer_discovered
                self.peer_discovery.start_discovery()
                print("✅ UDP Peer Discovery started.")
            else:
                print("⚠️ Peer Discovery object not created. Skipping.")
        except Exception as e:
            print(f"❌ Could not start Peer Discovery: {e}")
            print("   The server will run without automatic peer finding.")

        server = await websockets.serve(
            self.handle_websocket,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20
        )
        local_ips = self.get_local_ips()
        print(f"\n🚀 LANServer running at ws://{self.host}:{self.port}")
        print("   LAN Access (enter one of these in the frontend):")
        for ip in local_ips:
            print(f"    ws://{ip}:{self.port}")
        try:
            await server.wait_closed()
        except Exception as e:
            print(f"❌ Server error: {e}")

    # This method is now part of the LANServer class
    async def process_message(self, message, websocket):
        msg_type = message.get('type', 'text')
        timestamp = datetime.now().strftime("%H:%M:%S")
        sender_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        sender_ip = websocket.remote_address[0]
        print(f"Received {msg_type} from {sender_address}")

        # Add sender info to message
        message['sender'] = sender_ip
        message['timestamp'] = timestamp

        # Handle WebRTC signaling messages (route to specific peer)
        if msg_type in ['offer', 'answer', 'ice-candidate']:
            target_ip = message.get('target')
            if target_ip:
                await self.send_to_peer(target_ip, message)
            else:
                print(f"⚠️ No target specified for {msg_type}")
        else:
            # Broadcast text and file messages to all peers
            await self.broadcast_message(message, websocket)

    async def broadcast_message(self, message, sender_socket):
        for peer_info, websocket in list(self.peers.items()):
            if websocket != sender_socket:
                try:
                    await websocket.send(json.dumps(message))
                except Exception as e:
                    print(f"❌ Error broadcasting to {peer_info}: {e}")

    async def send_to_peer(self, target_ip, message):
        """Send message to a specific peer by IP"""
        for peer_info, websocket in list(self.peers.items()):
            if peer_info.startswith(target_ip + ':'):
                try:
                    await websocket.send(json.dumps(message))
                    print(f"✅ Sent {message.get('type')} to {target_ip}")
                    return
                except Exception as e:
                    print(f"❌ Error sending to {target_ip}: {e}")
        print(f"⚠️ Peer {target_ip} not found")

if __name__ == "__main__":
    server = LANServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")