import socket
import json
import time

class LANClient:
    def __init__(self, username="Anonymous"):
        self.username = username
        
    def send_message(self, peer_ip, message, port=12345):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((peer_ip, port))
                
                data = {
                    'type': 'text',
                    'content': message,
                    'username': self.username,
                    'timestamp': time.time()
                }
                
                s.sendall(json.dumps(data).encode('utf-8'))
                print(f"✅ Message sent to {peer_ip}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to send message to {peer_ip}: {e}")
            return False

if __name__ == "__main__":
    client = LANClient("TestUser")
    
    peer_ip = input("Enter peer IP: ")
    message = input("Enter message: ")
    
    client.send_message(peer_ip, message)
