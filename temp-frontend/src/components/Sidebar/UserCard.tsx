import React from 'react';
import './UserCard.css';

interface User {
  id: string;
  username: string;
  isOnline: boolean;
}

interface UserCardProps {
  user: User;
  isSelected: boolean;
  onClick: () => void;
}

const UserCard: React.FC<UserCardProps> = ({ user, isSelected, onClick }) => {
  return (
    <div 
      className={`user-card ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="user-avatar">
        <div className={`status-indicator ${user.isOnline ? 'online' : 'offline'}`} />
        <span className="avatar-text">{user.username[0].toUpperCase()}</span>
      </div>
      <div className="user-info">
        <span className="username">{user.username}</span>
        <span className="status-text">
          {user.isOnline ? 'Online' : 'Offline'}
        </span>
      </div>
    </div>
  );
};

export default UserCard;