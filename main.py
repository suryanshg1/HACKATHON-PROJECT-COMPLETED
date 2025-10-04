import socket
import threading
import json
import time
import os
import base64
from datetime import datetime
from message_handler import MessageHandler
from file_handler import FileHandler
from voicevideo_handler import VoiceVideoHandler  # Import our new handler

class LANMessenger:
    def __init__(self, username, server_port=12345, broadcast_port=50000):
        self.username = username
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.local_ip = self._get_local_ip()
        self.peers = {}  # Stores discovered peers {ip: {'username': name, ...}}
        self.running = False

        # Handlers for messages, files, and voice/video
        self.message_handler = MessageHandler()
        self.file_handler = FileHandler()
        self.voice_video_handler = VoiceVideoHandler(username, base_port=13000)

    def _get_local_ip(self):
        try:
            # First try to get the IP using a local network approach
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # UDP doesn't actually connect but gets local IP
                s.connect(('192.168.1.1', 1))  # This doesn't need to be reachable
                local_ip = s.getsockname()[0]
                if not local_ip.startswith('127.'):
                    return local_ip
            
            # Fallback: get all network interfaces
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith('127.'):
                    return ip
            return '127.0.0.1'  # Last resort: localhost
        except Exception:
            return "127.0.0.1"

    # SERVER FUNCTIONALITY
    def _start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', self.server_port))
        server_socket.listen(5)
        print(f"✅ Server is listening on {self.local_ip}:{self.server_port}")
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                if addr[0] in self.peers:
                    threading.Thread(target=self._handle_client, args=(client_socket, addr), daemon=True).start()
                else:
                    client_socket.close()
            except Exception:
                if self.running:
                    print("❌ Server socket closed.")
                break
        server_socket.close()

    def _recv_all(self, sock, length):
        data = b''
        while len(data) < length:
            more = sock.recv(length - len(data))
            if not more:
                raise EOFError("Socket closed before receiving required data")
            data += more
        return data

    def _handle_client(self, client_socket, addr):
        try:
            # Read first 8 bytes for length header
            length_bytes = self._recv_all(client_socket, 8)
            msg_length = int(length_bytes.decode('utf-8'))
            # Read the full JSON message now
            data_bytes = self._recv_all(client_socket, msg_length)
            message = json.loads(data_bytes.decode('utf-8'))
            msg_type = message.get('type', 'text')
            
            if msg_type == 'file':
                # Handle file reception directly here instead of using file_handler
                try:
                    filename = message['filename']
                    file_data = base64.b64decode(message['content'])  # Use 'content' key
                    
                    # Ensure files directory exists
                    files_dir = "data/files"
                    if not os.path.exists(files_dir):
                        os.makedirs(files_dir)
                    
                    # Save file
                    file_path = os.path.join(files_dir, filename)
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    sender_username = message.get('username', 'Unknown')
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n📎 [{timestamp}] File received from {sender_username} ({addr[0]}):")
                    print(f"   > {filename} saved to {file_path}")
                    
                except Exception as e:
                    print(f"❌ Error processing file: {e}")
            else:
                timestamp = datetime.now().strftime("%H:%M:%S")
                sender_username = message.get('username', 'Unknown')
                content = message.get('content', '')
                print(f"\n💬 [{timestamp}] New message from {sender_username} ({addr[0]}):")
                print(f"   > {content}")
                self.message_handler.save_message(addr[0], sender_username, content)
        except Exception as e:
            print(f"❌ Error handling client {addr}: {e}")
        finally:
            client_socket.close()

    # PEER DISCOVERY
    def _start_discovery(self):
        threading.Thread(target=self._broadcast_presence, daemon=True).start()
        threading.Thread(target=self._listen_for_peers, daemon=True).start()
        print(f"🔍 Peer discovery started for '{self.username}'")

    def _broadcast_presence(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = json.dumps({
            'type': 'discovery',
            'username': self.username,
            'port': self.server_port
        }).encode('utf-8')
        while self.running:
            try:
                broadcast_socket.sendto(message, ('<broadcast>', self.broadcast_port))
                time.sleep(5)
            except Exception as e:
                print(f"❌ Broadcast error: {e}")
                break
        broadcast_socket.close()

    def _listen_for_peers(self):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('', self.broadcast_port))
        while self.running:
            try:
                data, addr = listen_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                if message.get('type') == 'discovery' and addr[0] != self.local_ip:
                    self.peers[addr[0]] = {
                        'username': message['username'],
                        'port': message['port'],
                        'last_seen': time.time()
                    }
            except Exception:
                if self.running:
                    print("❌ Peer listener closed.")
                break
        listen_socket.close()

    def _prune_inactive_peers(self):
        while self.running:
            current_time = time.time()
            inactive_peers = [ip for ip, data in list(self.peers.items())
                              if current_time - data['last_seen'] > 30]
            for ip in inactive_peers:
                print(f"\n👋 Peer '{self.peers[ip]['username']}' has gone offline.")
                del self.peers[ip]
            time.sleep(10)

    # SEND WITH LENGTH HEADER
    def _send_with_length(self, peer_ip, peer_port, json_bytes):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((peer_ip, peer_port))
            length_header = f"{len(json_bytes):08}".encode('utf-8')
            s.sendall(length_header + json_bytes)

    # CLIENT FUNCTIONALITY
    def send_message(self, peer_ip, message_content):
        peer_info = self.peers.get(peer_ip)
        if not peer_info:
            print("❌ Peer not found or is inactive.")
            return
        try:
            data = json.dumps({
                'type': 'text',
                'content': message_content,
                'username': self.username
            }).encode('utf-8')
            self._send_with_length(peer_ip, peer_info['port'], data)
            print(f"✅ Message sent to '{peer_info['username']}' ({peer_ip})")
        except Exception as e:
            print(f"❌ Failed to send message to {peer_ip}: {e}")

    def send_file_to_peer(self, peer_ip, filepath):
        peer_info = self.peers.get(peer_ip)
        if not peer_info:
            print("❌ Peer not found or is inactive.")
            return
        if not os.path.exists(filepath):
            print("❌ File does not exist.")
            return
        try:
            with open(filepath, "rb") as f:
                encoded_content = base64.b64encode(f.read()).decode('utf-8')
            filename = os.path.basename(filepath)
            data = json.dumps({
                'type': 'file',
                'username': self.username,
                'filename': filename,
                'content': encoded_content  # Keep using 'content' key consistently
            }).encode('utf-8')
            self._send_with_length(peer_ip, peer_info['port'], data)
            print(f"✅ File '{filename}' sent to '{peer_info['username']}' ({peer_ip})")
        except Exception as e:
            print(f"❌ Failed to send file to {peer_ip}: {e}")

    # VOICE/VIDEO CALL FUNCTIONALITY
    def make_voice_call(self, peer_ip):
        """Make a voice-only call to peer"""
        if peer_ip not in self.peers:
            print("❌ Peer not found or is inactive.")
            return
        print(f"📞 Making voice call to {self.peers[peer_ip]['username']}...")
        self.voice_video_handler.make_call(peer_ip, 'audio')

    def make_video_call(self, peer_ip):
        """Make a video call to peer"""
        if peer_ip not in self.peers:
            print("❌ Peer not found or is inactive.")
            return
        print(f"📹 Making video call to {self.peers[peer_ip]['username']}...")
        self.voice_video_handler.make_call(peer_ip, 'both')

    # MAIN LOGIC
    def start(self):
        self.running = True
        threading.Thread(target=self._start_server, daemon=True).start()
        self._start_discovery()
        threading.Thread(target=self._prune_inactive_peers, daemon=True).start()
        
        # Start voice/video server
        self.voice_video_handler.start_call_server()
        
        self.run_cli()

    def stop(self):
        print("\n🛑 Shutting down...")
        self.running = False
        self.voice_video_handler.stop_server()
        time.sleep(0.1)

    def run_cli(self):
        while self.running:
            command = input(
                "\n> Enter a command:\n" +
                "  l - List peers\n" +
                "  s - Send message\n" +
                "  f - Send file\n" +
                "  v - Voice call\n" +
                "  c - Video call\n" +
                "  q - Quit\n" +
                "Your choice: "
            ).lower()
            
            if command == 'l':
                if not self.peers:
                    print("\n[ No active peers found. Still searching... ]")
                else:
                    print("\n📱 Active Peers:")
                    for i, (ip, data) in enumerate(self.peers.items(), 1):
                        print(f"  {i}. {data['username']} ({ip})")
            elif command == 's':
                self.list_and_send()
            elif command == 'f':
                self.list_and_send_file()
            elif command == 'v':
                self.list_and_call('voice')
            elif command == 'c':
                self.list_and_call('video')
            elif command == 'q':
                self.stop()
                break
            else:
                print("❓ Unknown command.")

    def list_and_send(self):
        if not self.peers:
            print("\n[ No peers to send a message to. ]")
            return
        peers_list = list(self.peers.items())
        print("\n📱 Select a peer to message:")
        for i, (ip, data) in enumerate(peers_list, 1):
            print(f"  {i}. {data['username']} ({ip})")
        try:
            choice = int(input("> Enter peer number: "))
            if 1 <= choice <= len(peers_list):
                peer_ip, _ = peers_list[choice - 1]
                message = input(f"> Enter message for {self.peers[peer_ip]['username']}: ")
                self.send_message(peer_ip, message)
            else:
                print("❌ Invalid number.")
        except ValueError:
            print("❌ Please enter a valid number.")

    def list_and_send_file(self):
        if not self.peers:
            print("\n[ No peers to send a file to. ]")
            return
        peers_list = list(self.peers.items())
        print("\n📱 Select a peer to send a file:")
        for i, (ip, data) in enumerate(peers_list, 1):
            print(f"  {i}. {data['username']} ({ip})")
        try:
            choice = int(input("> Enter peer number: "))
            if 1 <= choice <= len(peers_list):
                peer_ip, _ = peers_list[choice - 1]
                filepath = input("Enter full path of file to send: ")
                self.send_file_to_peer(peer_ip, filepath)
            else:
                print("❌ Invalid number.")
        except ValueError:
            print("❌ Please enter a valid number.")

    def list_and_call(self, call_type):
        if not self.peers:
            print(f"\n[ No peers to {call_type} call. ]")
            return
        peers_list = list(self.peers.items())
        print(f"\n📱 Select a peer to {call_type} call:")
        for i, (ip, data) in enumerate(peers_list, 1):
            print(f"  {i}. {data['username']} ({ip})")
        try:
            choice = int(input("> Enter peer number: "))
            if 1 <= choice <= len(peers_list):
                peer_ip, _ = peers_list[choice - 1]
                if call_type == 'voice':
                    self.make_voice_call(peer_ip)
                else:
                    self.make_video_call(peer_ip)
            else:
                print("❌ Invalid number.")
        except ValueError:
            print("❌ Please enter a valid number.")

if __name__ == "__main__":
    try:
        username = input("Enter your username: ")
        messenger = LANMessenger(username=username)
        messenger.start()
    except KeyboardInterrupt:
        messenger.stop()