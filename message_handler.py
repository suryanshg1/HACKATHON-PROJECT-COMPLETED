import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import threading
import shutil

class Message:
    def __init__(self, sender_ip: str, sender_username: str, content: str, msg_type: str = "text"):
        self.sender_ip = sender_ip
        self.sender_username = sender_username
        self.content = content
        self.type = msg_type
        self.timestamp = datetime.now().isoformat()
        self.read = False
        self.id = f"{int(datetime.now().timestamp() * 1000)}_{sender_ip}"
        
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'sender_ip': self.sender_ip,
            'sender_username': self.sender_username,
            'content': self.content,
            'type': self.type,
            'timestamp': self.timestamp,
            'read': self.read
        }
        
    @staticmethod
    def from_dict(data: Dict) -> 'Message':
        msg = Message(
            data['sender_ip'],
            data['sender_username'],
            data['content'],
            data.get('type', 'text')
        )
        msg.timestamp = data['timestamp']
        msg.read = data.get('read', False)
        msg.id = data.get('id', msg.id)
        return msg

class MessageHandler:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.messages_file = self.data_dir / "messages.json"
        self.backup_dir = self.data_dir / "backups"
        self.ensure_directories()
        self.lock = threading.Lock()
        self.load_messages()  # Load messages at initialization
        
    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self):
        """Create a backup of the messages file."""
        if not self.messages_file.exists():
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"messages_{timestamp}.json"
        shutil.copy2(self.messages_file, backup_path)
        
        # Clean old backups (keep last 5)
        backups = sorted(self.backup_dir.glob("messages_*.json"))
        for old_backup in backups[:-5]:
            old_backup.unlink()
            
    def load_messages(self) -> List[Message]:
        """Load all messages from the JSON file."""
        try:
            if self.messages_file.exists():
                with open(self.messages_file, 'r') as f:
                    data = json.load(f)
                    return [Message.from_dict(msg_data) for msg_data in data]
            return []
        except Exception as e:
            print(f"❌ Failed to load messages: {e}")
            # Try to restore from latest backup
            self._restore_from_backup()
            return []
            
    def _restore_from_backup(self):
        """Attempt to restore messages from the latest backup."""
        try:
            backups = sorted(self.backup_dir.glob("messages_*.json"))
            if backups:
                latest_backup = backups[-1]
                shutil.copy2(latest_backup, self.messages_file)
                print(f"✅ Restored messages from backup: {latest_backup.name}")
        except Exception as e:
            print(f"❌ Failed to restore from backup: {e}")
            
    def save_message(self, message_data: dict) -> Message:
        """Save a new message from WebSocket data."""
        sender_ip = message_data.get('sender_ip', message_data.get('peer', 'unknown'))
        sender_username = message_data.get('username', 'Anonymous')
        content = message_data.get('content', '')
        msg_type = message_data.get('type', 'text')
        
        message = Message(sender_ip, sender_username, content, msg_type)
        
        with self.lock:
            messages = self.load_messages()
            messages.append(message)
            
            try:
                # Create backup before saving
                self.create_backup()
                
                # Save messages
                with open(self.messages_file, 'w') as f:
                    json.dump([msg.to_dict() for msg in messages], f, indent=2)
                    
                return message
            except Exception as e:
                print(f"❌ Failed to save message: {e}")
                return None
                
    def get_messages_with_peer(self, peer_ip: str, limit: Optional[int] = None) -> List[Message]:
        """Retrieve messages exchanged with a specific peer."""
        messages = self.load_messages()
        peer_messages = [msg for msg in messages if msg.sender_ip == peer_ip]
        
        if limit:
            return peer_messages[-limit:]
        return peer_messages
        
    def mark_messages_read(self, peer_ip: str) -> bool:
        """Mark all messages from a specific peer as read."""
        with self.lock:
            messages = self.load_messages()
            changed = False
            
            for msg in messages:
                if msg.sender_ip == peer_ip and not msg.read:
                    msg.read = True
                    changed = True
                    
            if changed:
                try:
                    with open(self.messages_file, 'w') as f:
                        json.dump([msg.to_dict() for msg in messages], f, indent=2)
                    return True
                except Exception as e:
                    print(f"❌ Failed to update read status: {e}")
                    
            return False
            
    def delete_messages(self, peer_ip: Optional[str] = None, before_date: Optional[datetime] = None):
        """Delete messages matching criteria."""
        with self.lock:
            messages = self.load_messages()
            original_count = len(messages)
            
            if peer_ip:
                messages = [msg for msg in messages if msg.sender_ip != peer_ip]
                
            if before_date:
                messages = [
                    msg for msg in messages 
                    if datetime.fromisoformat(msg.timestamp) >= before_date
                ]
                
            if len(messages) < original_count:
                try:
                    self.create_backup()
                    with open(self.messages_file, 'w') as f:
                        json.dump([msg.to_dict() for msg in messages], f, indent=2)
                    return True
                except Exception as e:
                    print(f"❌ Failed to delete messages: {e}")
                    
            return False
            
    def get_message_stats(self, peer_ip: Optional[str] = None) -> Dict:
        """Get message statistics."""
        messages = self.load_messages()
        
        if peer_ip:
            messages = [msg for msg in messages if msg.sender_ip == peer_ip]
            
        return {
            'total_messages': len(messages),
            'unread_messages': len([msg for msg in messages if not msg.read]),
            'text_messages': len([msg for msg in messages if msg.type == 'text']),
            'file_messages': len([msg for msg in messages if msg.type == 'file']),
            'last_message_time': max([msg.timestamp for msg in messages]) if messages else None
        }
