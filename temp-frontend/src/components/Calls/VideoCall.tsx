import React, { useState, useRef, useEffect } from 'react';
import { usePeer } from '../../contexts/PeerContext';
import './VideoCall.css';
import './CallControls.css';

interface CallControlsProps {
  onEndCall: () => void;
  stream: MediaStream | null;
  isVideo: boolean;
}

const CallControls: React.FC<CallControlsProps> = ({ onEndCall, stream, isVideo }) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(!isVideo);

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
    if (stream && isVideo) {
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
      {isVideo && (
        <button
          className={`control-button ${isVideoOff ? 'active' : ''}`}
          onClick={handleVideoToggle}
          title={isVideoOff ? 'Turn Video On' : 'Turn Video Off'}
        >
          {isVideoOff ? '🎦' : '📹'}
        </button>
      )}
    </div>
  );
};

interface VideoCallProps {
  peerId: string;
  onEndCall: () => void;
  isVideo: boolean;
}

const VideoCall: React.FC<VideoCallProps> = ({ peerId, onEndCall, isVideo }) => {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const { peers } = usePeer();

  useEffect(() => {
    let isMounted = true;

    const setupLocalVideo = async () => {
      try {
        // Optimized constraints to reduce buffering
        const constraints = {
          video: isVideo ? {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 30, max: 30 }
          } : false,
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);

        if (!isMounted) {
          // Component unmounted, stop the stream right away
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        setLocalStream(stream);

        if (localVideoRef.current && isVideo) {
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
      }
    };
  }, [peerId, peers, isVideo]);

  useEffect(() => {
    const peer = peers.get(peerId);
    if (!peer) return;

    const handleTrack = (event: RTCTrackEvent) => {
      if (remoteVideoRef.current) {
        const [remoteStream] = event.streams;
        remoteVideoRef.current.srcObject = remoteStream;
      }
    };

    peer.connection.addEventListener('track', handleTrack);

    return () => {
      peer.connection.removeEventListener('track', handleTrack);
    };
  }, [peerId, peers]);

  return (
    <div className="video-call-container">
      {isVideo ? (
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
      ) : (
        <div className="audio-call-display">
          <div className="audio-call-info">
            <div className="call-icon">🎤</div>
            <div className="call-status">Voice Call in Progress</div>
            <div className="peer-name">{peerId}</div>
          </div>
          {/* Hidden video elements for audio streams */}
          <video ref={remoteVideoRef} autoPlay playsInline style={{ display: 'none' }} />
          <video ref={localVideoRef} autoPlay playsInline muted style={{ display: 'none' }} />
        </div>
      )}
      <CallControls onEndCall={onEndCall} stream={localStream} isVideo={isVideo} />
    </div>
  );
};

export default VideoCall;
