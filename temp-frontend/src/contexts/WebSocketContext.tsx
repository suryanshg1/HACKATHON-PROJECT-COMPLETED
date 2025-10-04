import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';

// Type definitions remain the same
type PeerInfo = {
  ip: string;
  username: string;
};

type MessageData = {
  type: 'text' | 'file' | 'discovery' | 'peer_list' | 'ice-candidate' | 'offer' | 'answer';
  content?: string;
  filename?: string;
  fileSize?: number;
  mimeType?: string;
  timestamp?: number;
  username?: string;
  peer?: string;
  peers?: PeerInfo[];
  candidate?: any;
  offer?: RTCSessionDescriptionInit;
  answer?: RTCSessionDescriptionInit;
  target?: string;
  sender?: string;
  [key: string]: any;
};

// Add new functions to the context type
interface WebSocketContextType {
  socket: WebSocket | null;
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;
  availablePeers: PeerInfo[];
  sendMessage: (message: MessageData) => void;
  connectToServer: (ip: string) => void;
  disconnect: () => void;
  onMessage: (handler: (data: MessageData) => void) => void;
}

const WebSocketContext = createContext<WebSocketContextType>({
  socket: null,
  isConnected: false,
  isConnecting: false,
  connectionError: null,
  availablePeers: [],
  sendMessage: () => {},
  connectToServer: () => {},
  disconnect: () => {},
  onMessage: () => {},
});

export const useWebSocket = () => useContext(WebSocketContext);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [availablePeers, setAvailablePeers] = useState<PeerInfo[]>([]);
  const [messageHandlers, setMessageHandlers] = useState<Array<(data: MessageData) => void>>([]);

  const onMessage = useCallback((handler: (data: MessageData) => void) => {
    setMessageHandlers(prev => [...prev, handler]);
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: MessageData = JSON.parse(event.data);
      if (message.type === 'peer_list' && message.peers) {
        setAvailablePeers(message.peers);
      } else {
        // Call all registered message handlers
        messageHandlers.forEach(handler => handler(message));
      }
    } catch (error) {
      console.error('Error parsing message:', error);
    }
  }, [messageHandlers]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.close();
      setSocket(null);
      setIsConnected(false);
    }
  }, [socket]);

  const connectToServer = useCallback((ip: string) => {
    if (socket || isConnecting) return;

    setIsConnecting(true);
    setConnectionError(null);
    const url = `ws://${ip}:12345`;
    console.log(`Attempting to connect to ${url}...`);

    const newSocket = new WebSocket(url);

    const timeoutId = setTimeout(() => {
        if (newSocket.readyState !== WebSocket.OPEN) {
            newSocket.close();
            setIsConnecting(false);
            setConnectionError(`Connection to ${url} timed out.`);
        }
    }, 5000); // 5-second timeout

    newSocket.onopen = () => {
      clearTimeout(timeoutId);
      console.log(`Successfully connected to ${url}`);
      setSocket(newSocket);
      setIsConnected(true);
      setIsConnecting(false);
      setConnectionError(null);
      newSocket.onmessage = handleMessage;
    };

    newSocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setIsConnecting(false);
      setSocket(null);
    };

    newSocket.onerror = (event) => {
      clearTimeout(timeoutId);
      console.error('WebSocket error:', event);
      setIsConnecting(false);
      setConnectionError(`Failed to connect to ${url}. Check the IP and if the server is running.`);
      newSocket.close();
    };
  }, [socket, isConnecting, handleMessage]);


  const sendMessage = useCallback((message: MessageData) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message));
    } else {
      console.error('Cannot send message: WebSocket is not connected.');
    }
  }, [socket, isConnected]);

  const value = {
    socket,
    isConnected,
    isConnecting,
    connectionError,
    availablePeers,
    sendMessage,
    connectToServer,
    disconnect,
    onMessage,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};