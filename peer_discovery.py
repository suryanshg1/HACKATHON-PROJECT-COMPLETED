import socket
import threading
import json
import time

class PeerDiscovery:
    def __init__(self, username, broadcast_port=50000, listen_port=12345):
        self.username = username
        self.broadcast_port = broadcast_port
        self.listen_port = listen_port
        self.peers = {}
        self.running = False
        
    def start_discovery(self):
        self.running = True
        
        # Start broadcasting presence
        broadcast_thread = threading.Thread(target=self.broadcast_presence)
        broadcast_thread.daemon = True
        broadcast_thread.start()
        
        # Start listening for broadcasts
        listen_thread = threading.Thread(target=self.listen_for_peers)
        listen_thread.daemon = True
        listen_thread.start()
        
        print(f"🔍 Peer discovery started for {self.username}")
        
    def get_broadcast_addresses(self):
        """Get all possible broadcast addresses for local network interfaces"""
        broadcast_addrs = ['255.255.255.255']  # Default broadcast
        
        try:
            # Get all network interfaces that support broadcast
            interfaces = socket.if_nameindex()
            for interface in interfaces:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    # Get interface broadcast address
                    addr = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                    for ip in addr:
                        # Convert IP to broadcast address
                        ip_parts = ip[4][0].split('.')
                        if len(ip_parts) == 4:
                            broadcast_addr = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
                            if broadcast_addr not in broadcast_addrs:
                                broadcast_addrs.append(broadcast_addr)
                except:
                    continue
        except:
            pass
        
        return broadcast_addrs

    def broadcast_presence(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = {
            'type': 'discovery',
            'username': self.username,
            'port': self.listen_port,
            'ws_port': self.listen_port,  # WebSocket port same as listen port
            'timestamp': time.time()
        }
        
        broadcast_addrs = self.get_broadcast_addresses()
        
        while self.running:
            try:
                # Broadcast to all possible network interfaces
                for addr in broadcast_addrs:
                    try:
                        broadcast_socket.sendto(
                            json.dumps(message).encode('utf-8'),
                            (addr, self.broadcast_port)
                        )
                    except:
                        continue
                time.sleep(2)  # Broadcast every 2 seconds
            except Exception as e:
                print(f"❌ Broadcast error: {e}")
                
        broadcast_socket.close()
        
    def listen_for_peers(self):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('', self.broadcast_port))
        
        while self.running:
            try:
                data, addr = listen_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                if message['type'] == 'discovery' and addr[0] != self.get_local_ip():
                    peer_info = {
                        'username': message['username'],
                        'ip': addr[0],
                        'port': message['port'],
                        'last_seen': time.time()
                    }
                    
                    self.peers[addr[0]] = peer_info
                    print(f"👋 Discovered peer: {message['username']} at {addr[0]}")
                    
            except Exception as e:
                if self.running:
                    print(f"❌ Listen error: {e}")
                    
        listen_socket.close()
        
    def get_local_ip(self):
        try:
            # Get hostname and resolve to IP - works without internet
            hostname = socket.gethostname()
            # Get all IP addresses for this host
            ip_addresses = socket.getaddrinfo(hostname, None, socket.AF_INET)

            # Filter out localhost and get LAN IP (192.168.x.x or 10.x.x.x or 172.16-31.x.x)
            for addr_info in ip_addresses:
                ip = addr_info[4][0]
                if ip.startswith('192.168.') or ip.startswith('10.') or \
                   (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31):
                    return ip

            # If no private IP found, return first non-localhost IP
            for addr_info in ip_addresses:
                ip = addr_info[4][0]
                if ip != '127.0.0.1':
                    return ip

            return "127.0.0.1"
        except:
            return "127.0.0.1"
            
    def get_active_peers(self):
        current_time = time.time()
        active_peers = {}
        
        for ip, peer in self.peers.items():
            if current_time - peer['last_seen'] < 30:  # 30 seconds timeout
                active_peers[ip] = peer
                
        return active_peers
        
    def stop_discovery(self):
        self.running = False

if __name__ == "__main__":
    username = input("Enter your username: ")
    discovery = PeerDiscovery(username)
    discovery.start_discovery()
    
    try:
        while True:
            time.sleep(10)
            peers = discovery.get_active_peers()
            print(f"\n📱 Active peers: {len(peers)}")
            for ip, peer in peers.items():
                print(f"  - {peer['username']} ({ip})")
    except KeyboardInterrupt:
        discovery.stop_discovery()
