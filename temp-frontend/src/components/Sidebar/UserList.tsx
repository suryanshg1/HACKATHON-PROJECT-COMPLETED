import React, { useState } from 'react';
import UserCard from './UserCard';
import { useWebSocket } from '../../contexts/WebSocketContext';
import './UserList.css';

interface User {
  id: string;
  username: string;
  isOnline: boolean;
}

interface UserListProps {
  onSelectUser: (userId: string) => void;
}

const UserList: React.FC<UserListProps> = ({ onSelectUser }) => {
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const { isConnected, availablePeers } = useWebSocket();

  // Convert availablePeers to User format
  const users: User[] = availablePeers.map((peer) => ({
    id: peer.ip,
    username: peer.username,
    isOnline: true,
  }));

  return (
    <div className="user-list">
      <div className="user-list-header">
        <h2>Available Peers</h2>
        <span className="peer-count">{users.length} online</span>
      </div>
      <div className="user-list-content">
        {users.length > 0 ? (
          users.map((user) => (
            <UserCard
              key={user.id}
              user={user}
              isSelected={selectedUser === user.id}
              onClick={() => {
                setSelectedUser(user.id);
                onSelectUser(user.id);
              }}
            />
          ))
        ) : (
          <div className="empty-users">
            <p>🔍 Searching for peers...</p>
            <small>Make sure other devices are connected to the server</small>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserList;