import React from 'react';
import './MessageBubble.css';

interface Message {
  id: string;
  sender: string;
  content: string;
  type: 'text' | 'file';
  timestamp: number;
  fileUrl?: string;
  fileName?: string;
}

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isMe = message.sender === 'You';
  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const renderContent = () => {
    if (message.type === 'file') {
      return (
        <div className="file-message">
          <i className="file-icon">📎</i>
          <span className="file-name">{message.fileName}</span>
          {message.fileUrl && (
            <a 
              href={message.fileUrl}
              download
              className="download-link"
              onClick={(e) => e.stopPropagation()}
            >
              Download
            </a>
          )}
        </div>
      );
    }
    return <div className="text-content">{message.content}</div>;
  };

  return (
    <div className={`message-bubble ${isMe ? 'sent' : 'received'}`}>
      <div className="message-content">
        {renderContent()}
      </div>
      <div className="message-time">{formattedTime}</div>
    </div>
  );
};

export default MessageBubble;