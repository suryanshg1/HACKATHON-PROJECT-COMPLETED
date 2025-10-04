import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';

interface PeerConnection {
  connection: RTCPeerConnection;
  dataChannel: RTCDataChannel | null;
}

interface PeerContextType {
  peers: Map<string, PeerConnection>;
  createPeerConnection: (peerId: string) => Promise<{ peerConnection: RTCPeerConnection; dataChannel: RTCDataChannel; }>;
  sendToPeer: (peerId: string, data: any) => void;
  startCall: (peerId: string, isVideo: boolean) => Promise<void>;
  endCall: (peerId: string) => void;
}

// Configuration for LAN-only WebRTC (no internet required)
// Empty iceServers array allows direct peer-to-peer connection on same LAN
const configuration: RTCConfiguration = {
  iceServers: []
};

const PeerContext = createContext<PeerContextType>({
  peers: new Map(),
  createPeerConnection: async () => {
    const pc = new RTCPeerConnection();
    const dc = pc.createDataChannel('default');
    return { peerConnection: pc, dataChannel: dc };
  },
  sendToPeer: () => {},
  startCall: async () => {},
  endCall: () => {},
});

export const usePeer = () => useContext(PeerContext);

interface PeerProviderProps {
  children: ReactNode;
}

export const PeerProvider: React.FC<PeerProviderProps> = ({ children }) => {
  const [peers, setPeers] = useState<Map<string, PeerConnection>>(new Map());
  const { socket, sendMessage } = useWebSocket();

  const createPeerConnection = async (peerId: string) => {
    const peerConnection = new RTCPeerConnection(configuration);
    const dataChannel = peerConnection.createDataChannel('data');
    
    setPeers(new Map(peers.set(peerId, { connection: peerConnection, dataChannel })));

    peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        sendMessage({
          type: 'ice-candidate',
          candidate: event.candidate,
          target: peerId,
        });
      }
    };

    dataChannel.onmessage = (event) => {
      console.log('Received data from peer:', event.data);
    };

    return { peerConnection, dataChannel };
  };

  const sendToPeer = (peerId: string, data: any) => {
    const peer = peers.get(peerId);
    if (peer?.dataChannel?.readyState === 'open') {
      peer.dataChannel.send(JSON.stringify(data));
    }
  };

  const startCall = async (peerId: string, isVideo: boolean) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: isVideo,
        audio: true,
      });

      let peerConnection: RTCPeerConnection;
      const peer = peers.get(peerId);
      if (!peer) {
        const result = await createPeerConnection(peerId);
        peerConnection = result.peerConnection;
      } else {
        peerConnection = peer.connection;
      }

      stream.getTracks().forEach(track => peerConnection.addTrack(track, stream));

      // Create and send offer
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);

      sendMessage({
        type: 'offer',
        offer: offer,
        target: peerId,
      });
    } catch (error) {
      console.error('Error starting call:', error);
      throw error;
    }
  };

  const endCall = (peerId: string) => {
    const peer = peers.get(peerId);
    if (peer) {
      peer.connection.close();
      peers.delete(peerId);
      setPeers(new Map(peers));
    }
  };

  useEffect(() => {
    if (!socket) return;

    const handleSocketMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case 'offer':
            handleOffer(data);
            break;
          case 'answer':
            handleAnswer(data);
            break;
          case 'ice-candidate':
            handleIceCandidate(data);
            break;
        }
      } catch (error) {
        console.error('Error handling socket message:', error);
      }
    };

    socket.addEventListener('message', handleSocketMessage);
    return () => socket.removeEventListener('message', handleSocketMessage);
  }, [socket, peers]);

  const handleOffer = async (data: any) => {
    const peerId = data.sender;
    if (!peerId) return;

    const { peerConnection } = await createPeerConnection(peerId);
    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);

    sendMessage({
      type: 'answer',
      answer: answer,
      target: peerId,
    });
  };

  const handleAnswer = async (data: any) => {
    const peerId = data.sender;
    const peer = peers.get(peerId);
    if (peer) {
      await peer.connection.setRemoteDescription(new RTCSessionDescription(data.answer));
    }
  };

  const handleIceCandidate = async (data: any) => {
    const peerId = data.sender;
    const peer = peers.get(peerId);
    if (peer && data.candidate) {
      await peer.connection.addIceCandidate(new RTCIceCandidate(data.candidate));
    }
  };

  return (
    <PeerContext.Provider value={{ peers, createPeerConnection, sendToPeer, startCall, endCall }}>
      {children}
    </PeerContext.Provider>
  );
};