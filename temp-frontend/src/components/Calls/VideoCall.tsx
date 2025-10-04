import React, { useState, useRef, useEffect } from 'react';
import { usePeer } from '../../contexts/PeerContext';
import './VideoCall.css';
import './CallControls.css';

interface CallControlsProps {
  onEndCall: () => void;
  stream: MediaStream | null;
}

const CallControls: React.FC<CallControlsProps> = ({ onEndCall, stream }) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);

  const handleMuteToggle = () => {
    if (stream) {
      const audioTracks = stream.getAudioTracks();
      audioTracks.forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsMuted(!isMuted);
    }
  };

  const handleVideoToggle = () => {
    if (stream) {
      const videoTracks = stream.getVideoTracks();
      videoTracks.forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsVideoOff(!isVideoOff);
    }
  };

  return (
    <div className="call-controls">
      <button
        className={`control-button ${isMuted ? 'active' : ''}`}
        onClick={handleMuteToggle}
        title={isMuted ? 'Unmute' : 'Mute'}
      >
        {isMuted ? '🔇' : '🎤'}
      </button>
      <button
        className="control-button end-call"
        onClick={onEndCall}
        title="End Call"
      >
        📞
      </button>
      <button
        className={`control-button ${isVideoOff ? 'active' : ''}`}
        onClick={handleVideoToggle}
        title={isVideoOff ? 'Turn Video On' : 'Turn Video Off'}
      >
        {isVideoOff ? '🎦' : '📹'}
      </button>
    </div>
  );
};

interface VideoCallProps {
  peerId: string;
  onEndCall: () => void;
}

const VideoCall: React.FC<VideoCallProps> = ({ peerId, onEndCall }) => {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const { peers } = usePeer();

  useEffect(() => {
    let isMounted = true;

    const setupLocalVideo = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });

        if (!isMounted) {
          // Component unmounted, stop the stream right away
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        setLocalStream(stream);

        if (localVideoRef.current) {
          localVideoRef.current.srcObject = stream;
        }

        // Add tracks to peer connection
        const peer = peers.get(peerId);
        if (peer) {
          stream.getTracks().forEach(track => {
            peer.connection.addTrack(track, stream);
          });
        }
      } catch (error) {
        console.error('Error accessing media devices:', error);
      }
    };

    setupLocalVideo();

    return () => {
      isMounted = false;
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        setLocalStream(null);
      }
    };
  // Added localStream to the dependencies because it's used inside cleanup
  }, [peerId, peers, localStream]);

  useEffect(() => {
    const peer = peers.get(peerId);
    if (!peer) return;

    const handleTrack = (event: RTCTrackEvent) => {
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = event.streams[0];
      }
    };

    peer.connection.addEventListener('track', handleTrack);

    return () => {
      peer.connection.removeEventListener('track', handleTrack);
    };
  }, [peerId, peers]);

  return (
    <div className="video-call-container">
      <div className="video-grid">
        <div className="video-wrapper remote">
          <video
            ref={remoteVideoRef}
            autoPlay
            playsInline
            className="remote-video"
          />
          <div className="peer-name">Remote User</div>
        </div>
        <div className="video-wrapper local">
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className="local-video"
          />
          <div className="peer-name">You</div>
        </div>
      </div>
      <CallControls onEndCall={onEndCall} stream={localStream} />
    </div>
  );
};

export default VideoCall;
