import React, { useState, useEffect } from 'react';
import { useWebSocket } from './contexts/WebSocketContext';
import UserList from './components/Sidebar/UserList';
import ChatWindow from './components/Chat/ChatWindow';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

interface Message {
  id: string;
  sender: string;
  content: string;
  type: 'text' | 'file';
  timestamp: number;
  fileUrl?: string;
  fileName?: string;
}

function App() {
  const {
    connectToServer,
    disconnect,
    isConnected,
    isConnecting,
    connectionError,
    sendMessage,
    onMessage,
  } = useWebSocket();

  const [serverIp, setServerIp] = useState('192.168.29.49');
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  // Handle incoming messages
  useEffect(() => {
    onMessage((data) => {
      if (data.type === 'text' || data.type === 'file') {
        const newMessage: Message = {
          id: Date.now().toString() + Math.random(),
          sender: data.sender || 'Unknown',
          content: data.content || '',
          type: data.type,
          timestamp: data.timestamp || Date.now(),
          fileName: data.filename,
        };
        setMessages((prev) => [...prev, newMessage]);

        if (data.type === 'text') {
          toast.info(`New message from ${data.sender}`);
        } else if (data.type === 'file') {
          toast.info(`${data.sender} sent a file: ${data.filename}`);
        }
      }
    });
  }, [onMessage]);

  const handleConnect = () => {
    connectToServer(serverIp);
  };

  const handleSendMessage = (text: string) => {
    const message: Message = {
      id: Date.now().toString(),
      sender: 'You',
      content: text,
      type: 'text',
      timestamp: Date.now(),
    };

    setMessages([...messages, message]);

    sendMessage({
      type: 'text',
      content: text,
      target: selectedUser || undefined,
    });
  };

  const handleFileUpload = async (file: File) => {
    const reader = new FileReader();

    return new Promise<void>((resolve, reject) => {
      reader.onload = () => {
        const base64Data = reader.result as string;
        const base64Content = base64Data.split(',')[1];

        const message: Message = {
          id: Date.now().toString(),
          sender: 'You',
          content: base64Content,
          type: 'file',
          timestamp: Date.now(),
          fileName: file.name,
        };

        setMessages([...messages, message]);

        sendMessage({
          type: 'file',
          content: base64Content,
          filename: file.name,
          fileSize: file.size,
          mimeType: file.type,
          target: selectedUser || undefined,
        });

        resolve();
      };

      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  };

  // This is the main screen when you are not connected
  if (!isConnected) {
    return (
      <div className="connection-container">
        <div className="connection-card">
          <div className="connection-header">
            <h1>🌐 LAN Chat & Call</h1>
            <p className="subtitle">Connect to start messaging and calling</p>
          </div>
          <div className="connection-body">
            <label htmlFor="server-ip">Server IP Address</label>
            <input
              id="server-ip"
              type="text"
              value={serverIp}
              onChange={(e) => setServerIp(e.target.value)}
              placeholder="e.g., 192.168.1.10"
              disabled={isConnecting}
            />
            <button
              className="connect-button"
              onClick={handleConnect}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <>
                  <span className="spinner"></span>
                  Connecting...
                </>
              ) : (
                'Connect'
              )}
            </button>
            {connectionError && (
              <div className="error-message">
                <span>⚠️</span>
                {connectionError}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // This is the screen you see after you are successfully connected
  return (
    <div className="app-container">
      <ToastContainer position="top-right" autoClose={3000} />
      <div className="app-header">
        <div className="header-content">
          <h1>🌐 LAN Chat & Call</h1>
          <div className="header-actions">
            <span className="status-badge connected">● Connected</span>
            <button onClick={disconnect} className="disconnect-button">
              Disconnect
            </button>
          </div>
        </div>
      </div>
      <main className="app-main">
        <UserList onSelectUser={setSelectedUser} />
        <div className="chat-section">
          {selectedUser ? (
            <ChatWindow
              messages={messages}
              onSendMessage={handleSendMessage}
              onFileUpload={handleFileUpload}
              selectedUser={selectedUser}
            />
          ) : (
            <div className="no-chat-selected">
              <div className="empty-state">
                <span className="empty-icon">💬</span>
                <h2>Select a user to start chatting</h2>
                <p>Choose someone from the list to send messages, files, or start a call</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;