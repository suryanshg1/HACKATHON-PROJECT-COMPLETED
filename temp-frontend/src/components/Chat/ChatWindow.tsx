import React, { useState, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';

import { useWebSocket } from '../../contexts/WebSocketContext';
import { usePeer } from '../../contexts/PeerContext';

import MessageBubble from './MessageBubble';
import VideoCall from '../Calls/VideoCall';

import './ChatWindow.css';

interface Message {
  id: string;
  sender: string;
  content: string;
  type: 'text' | 'file';      // Use a string literal union!
  timestamp: number;
  fileUrl?: string;
  fileName?: string;
}

interface ChatWindowProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  onFileUpload: (file: File) => void;
  selectedUser: string | null;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, onSendMessage, onFileUpload, selectedUser }) => {
  const { sendMessage } = useWebSocket();
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      handleFileUpload(acceptedFiles);
    },
    noClick: true,
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return;

    onSendMessage(inputMessage);
    setInputMessage('');
  };

  const handleFileUpload = async (files: File[]) => {
    for (const file of files) {
      try {
        const reader = new FileReader();
        const filePromise = new Promise((resolve, reject) => {
          reader.onload = () => resolve(reader.result);
          reader.onerror = () => reject(reader.error);
        });

        reader.readAsDataURL(file);
        const base64Data = await filePromise;
        const base64Content = (base64Data as string).split(',')[1];

        // Fixed: Provide the proper type!
        const fileMessage: Message = {
          id: Date.now().toString(),
          sender: 'You',
          content: base64Content,
          type: 'file',                      // Fix here: 'file' is a literal, not a string variable!
          timestamp: Date.now(),
          fileUrl: '',                       // set this only if you have a URL
          fileName: file.name
        };

        await onFileUpload(file);
        sendMessage(fileMessage);
        toast.success(`File ${file.name} sent successfully!`);
      } catch (error) {
        console.error('Error sending file:', error);
        toast.error(`Failed to send file ${file.name}`);
      }
    }
  };

  const [isInCall, setIsInCall] = useState(false);
  const [activeCallPeer, setActiveCallPeer] = useState<string | null>(null);
  const [isVideoCall, setIsVideoCall] = useState(false);
  const { startCall, endCall, incomingCall, acceptCall, rejectCall } = usePeer();

  const handleStartCall = async (withVideo: boolean) => {
    try {
      if (!selectedUser) {
        toast.error('Please select a user to call');
        return;
      }
      await startCall(selectedUser, withVideo);
      setActiveCallPeer(selectedUser);
      setIsInCall(true);
      setIsVideoCall(withVideo);
      toast.success(`Starting ${withVideo ? 'video' : 'voice'} call...`);
    } catch (error) {
      toast.error('Failed to start call');
      console.error('Call error:', error);
    }
  };

  const handleAcceptCall = async () => {
    try {
      await acceptCall();
      if (incomingCall) {
        setActiveCallPeer(incomingCall.peerId);
        setIsInCall(true);
        setIsVideoCall(incomingCall.isVideo);
      }
    } catch (error) {
      toast.error('Failed to accept call');
      console.error('Accept call error:', error);
    }
  };

  const handleRejectCall = () => {
    rejectCall();
    toast.info('Call rejected');
  };

  const handleEndCall = () => {
    if (activeCallPeer) {
      endCall(activeCallPeer);
      setIsInCall(false);
      setActiveCallPeer(null);
    }
  };

  return (
    <div className="chat-window" {...getRootProps()}>
      {/* Incoming Call Modal */}
      {incomingCall && !isInCall && (
        <div className="incoming-call-modal">
          <div className="incoming-call-content">
            <h3>{incomingCall.isVideo ? '📹 Incoming Video Call' : '🎤 Incoming Voice Call'}</h3>
            <p>From: {incomingCall.peerId}</p>
            <div className="incoming-call-buttons">
              <button className="accept-button" onClick={handleAcceptCall}>
                Accept
              </button>
              <button className="reject-button" onClick={handleRejectCall}>
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {isInCall && activeCallPeer ? (
        <VideoCall
          peerId={activeCallPeer}
          onEndCall={handleEndCall}
          isVideo={isVideoCall}
        />
      ) : (
        <>
          <input {...getInputProps()} />
          <div className="chat-header">
            <h2>Chat</h2>
            <div className="call-buttons">
              <button
                className="call-button voice"
                onClick={() => handleStartCall(false)}
                title="Start Voice Call"
              >
                🎤
              </button>
              <button
                className="call-button video"
                onClick={() => handleStartCall(true)}
                title="Start Video Call"
              >
                📹
              </button>
            </div>
          </div>
          <div className="chat-messages">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
          <div className={`file-drop-overlay ${isDragActive ? 'active' : ''}`}>
            <div className="drop-message">
              Drop files here to send
            </div>
          </div>
          <div className="chat-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type a message..."
            />
            <label htmlFor="file-input" className="file-button" title="Send File">
              📎
            </label>
            <input
              id="file-input"
              type="file"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileUpload(Array.from(e.target.files));
                }
              }}
            />
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={!inputMessage.trim()}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatWindow;
