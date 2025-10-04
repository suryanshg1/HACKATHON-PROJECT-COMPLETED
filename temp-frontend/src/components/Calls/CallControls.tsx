import React, { useState } from 'react';
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
        className={`control-button end-call`}
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

export default CallControls;