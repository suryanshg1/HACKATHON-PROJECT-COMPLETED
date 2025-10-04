import socket
import threading
import time
import pyaudio
import cv2
import pickle
import struct
import json
import numpy as np
from datetime import datetime

class VoiceVideoHandler:
    def __init__(self, username, base_port=13000):
        self.username = username
        self.base_port = base_port
        self.audio_port = base_port
        self.video_port = base_port + 1
        self.control_port = base_port + 2
        
        # Audio settings
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 1
        self.audio_rate = 44100
        self.audio_chunk = 1024
        
        # Video settings
        self.video_width = 640
        self.video_height = 480
        self.video_fps = 15
        
        # Call state
        self.in_call = False
        self.is_caller = False
        self.call_peer_ip = None
        self.call_peer_ports = None
        self.current_call_type = 'both'
        
        # Sockets
        self.audio_socket = None
        self.video_socket = None
        self.control_socket = None
        
        # Streams
        self.audio_input = None
        self.audio_output = None
        self.video_capture = None
        
        # Threading
        self.running = False
        
    def start_call_server(self):
        """Start listening for incoming calls"""
        self.running = True
        
        # Start control server for call signaling
        threading.Thread(target=self._control_server, daemon=True).start()
        print(f"📞 Voice/Video server ready on ports {self.audio_port}-{self.control_port}")
        
    def _control_server(self):
        """Handle call control messages (call, accept, reject, hangup)"""
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.control_socket.bind(('', self.control_port))
        
        while self.running:
            try:
                data, addr = self.control_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                self._handle_call_control(message, addr)
            except Exception as e:
                if self.running:
                    print(f"❌ Call control error: {e}")
                    
    def _handle_call_control(self, message, addr):
        """Process call control messages"""
        msg_type = message.get('type')
        
        if msg_type == 'call_request':
            if not self.in_call:
                print(f"\n📞 Incoming call from {message['username']} ({addr[0]})")
                response = input("Accept call? (y/n): ").lower()
                
                if response == 'y':
                    self._accept_call(message, addr)
                else:
                    self._reject_call(addr)
            else:
                self._send_control_message(addr[0], {'type': 'busy'})
                
        elif msg_type == 'call_accepted':
            print("✅ Call accepted! Starting voice/video...")
            self._start_media_streams(addr[0], message['ports'], self.current_call_type)
            
        elif msg_type == 'call_rejected':
            print("❌ Call rejected")
            
        elif msg_type == 'call_ended':
            print("📞 Call ended by peer")
            self._end_call()
            
        elif msg_type == 'busy':
            print("📞 Peer is busy")
            
    def make_call(self, peer_ip, call_type='both'):
        """Initiate a call to peer"""
        if self.in_call:
            print("❌ Already in a call")
            return
            
        print(f"📞 Calling {peer_ip}...")
        
        call_request = {
            'type': 'call_request',
            'username': self.username,
            'call_type': call_type,  # 'audio', 'video', 'both'
            'ports': {
                'audio': self.audio_port,
                'video': self.video_port,
                'control': self.control_port
            }
        }
        
        self.is_caller = True
        self.call_peer_ip = peer_ip
        self.current_call_type = call_type
        self._send_control_message(peer_ip, call_request)
        
    def _accept_call(self, message, addr):
        """Accept incoming call"""
        self.in_call = True
        self.is_caller = False
        self.call_peer_ip = addr[0]
        self.call_peer_ports = message['ports']
        
        # Send acceptance
        accept_message = {
            'type': 'call_accepted',
            'ports': {
                'audio': self.audio_port,
                'video': self.video_port,
                'control': self.control_port
            }
        }
        self._send_control_message(addr[0], accept_message)
        
        # Start media streams
        self._start_media_streams(addr[0], message['ports'], message['call_type'])
        
    def _reject_call(self, addr):
        """Reject incoming call"""
        reject_message = {'type': 'call_rejected'}
        self._send_control_message(addr[0], reject_message)
        
    def _start_media_streams(self, peer_ip, peer_ports, call_type='both'):
        """Start audio and video streaming"""
        self.in_call = True
        
        try:
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            
            # Audio input (microphone)
            self.audio_input = audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                input=True,
                frames_per_buffer=self.audio_chunk
            )
            
            # Audio output (speakers)
            self.audio_output = audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                output=True,
                frames_per_buffer=self.audio_chunk
            )
            
            # Create UDP socket for audio
            self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Video-specific setup (only for 'both' call type)
            if call_type == 'both':
                # Video capture
                self.video_capture = cv2.VideoCapture(0)
                self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_width)
                self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_height)
                self.video_capture.set(cv2.CAP_PROP_FPS, self.video_fps)
                
                # Create UDP socket for video
                self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Start streaming threads
            threading.Thread(target=self._send_audio, args=(peer_ip, peer_ports['audio']), daemon=True).start()
            threading.Thread(target=self._receive_audio, daemon=True).start()
            
            # Start video threads only for 'both' call type
            if call_type == 'both':
                threading.Thread(target=self._send_video, args=(peer_ip, peer_ports['video']), daemon=True).start()
                threading.Thread(target=self._receive_video, daemon=True).start()
            
            if call_type == 'both':
                print("🎥 Voice/Video call started!")
            else:
                print("🎤 Voice call started!")
            print("Press 'q' to end call")
            
            # Simple call control loop
            while self.in_call:
                if input().lower() == 'q':
                    self.end_call()
                    break
                    
        except Exception as e:
            print(f"❌ Failed to start media streams: {e}")
            self._end_call()
            
    def _send_audio(self, peer_ip, peer_port):
        """Send audio data to peer"""
        while self.in_call:
            try:
                data = self.audio_input.read(self.audio_chunk, exception_on_overflow=False)
                self.audio_socket.sendto(data, (peer_ip, peer_port))
            except Exception as e:
                if self.in_call:
                    print(f"❌ Audio send error: {e}")
                break
                
    def _receive_audio(self):
        """Receive and play audio from peer"""
        receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receive_socket.bind(('', self.audio_port))
        
        while self.in_call:
            try:
                data, addr = receive_socket.recvfrom(self.audio_chunk * 4)
                if self.in_call and self.audio_output:
                    self.audio_output.write(data)
            except Exception as e:
                if self.in_call:
                    print(f"❌ Audio receive error: {e}")
                break
                
        receive_socket.close()
        
    def _send_video(self, peer_ip, peer_port):
        """Send video frames to peer"""
        while self.in_call:
            try:
                ret, frame = self.video_capture.read()
                if ret:
                    # Compress frame
                    frame = cv2.resize(frame, (self.video_width, self.video_height))
                    _, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    # Send frame in chunks if too large
                    frame_data = encoded_frame.tobytes()
                    chunk_size = 60000  # UDP limit consideration
                    
                    if len(frame_data) <= chunk_size:
                        header = struct.pack('!I', len(frame_data))
                        self.video_socket.sendto(header + frame_data, (peer_ip, peer_port))
                    else:
                        # Handle large frames (split into chunks)
                        for i in range(0, len(frame_data), chunk_size):
                            chunk = frame_data[i:i + chunk_size]
                            is_last = i + chunk_size >= len(frame_data)
                            chunk_header = struct.pack('!II?', len(chunk), i, is_last)
                            self.video_socket.sendto(chunk_header + chunk, (peer_ip, peer_port))
                            
                time.sleep(1.0 / self.video_fps)
                
            except Exception as e:
                if self.in_call:
                    print(f"❌ Video send error: {e}")
                break
                
    def _receive_video(self):
        """Receive and display video from peer"""
        receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receive_socket.bind(('', self.video_port))
        
        frame_buffer = {}
        
        while self.in_call:
            try:
                data, addr = receive_socket.recvfrom(65535)
                
                if len(data) < 4:
                    continue
                
                # Try to determine frame type based on header size
                if len(data) >= 9:  # Check if it could be a chunked frame header (4 + 4 + 1 bytes)
                    # Try to unpack as chunked frame header
                    try:
                        chunk_size, offset, is_last = struct.unpack('!II?', data[:9])
                        if chunk_size <= len(data) - 9:  # Valid chunk header
                            chunk_data = data[9:9 + chunk_size]
                            
                            # Initialize frame buffer for this frame if not exists
                            frame_id = addr  # Use sender address as frame identifier
                            if frame_id not in frame_buffer:
                                frame_buffer[frame_id] = {}
                            
                            # Store chunk at correct offset
                            frame_buffer[frame_id][offset] = chunk_data
                            
                            # If this is the last chunk, reassemble the frame
                            if is_last:
                                # Sort chunks by offset and concatenate
                                sorted_chunks = sorted(frame_buffer[frame_id].items())
                                complete_frame_data = b''.join([chunk for offset, chunk in sorted_chunks])
                                
                                # Decode and display the complete frame
                                frame = cv2.imdecode(np.frombuffer(complete_frame_data, np.uint8), cv2.IMREAD_COLOR)
                                if frame is not None:
                                    cv2.imshow(f'Video Call - {self.call_peer_ip}', frame)
                                    if cv2.waitKey(1) & 0xFF == ord('q'):
                                        self.end_call()
                                        break
                                
                                # Clear buffer for this frame
                                del frame_buffer[frame_id]
                            
                            continue  # Successfully processed as chunked frame
                    except struct.error:
                        pass  # Not a chunked frame, try single frame format
                
                # Handle as single-packet frame
                frame_size = struct.unpack('!I', data[:4])[0]
                if frame_size <= len(data) - 4:  # Valid single frame
                    frame_data = data[4:4 + frame_size]
                    
                    # Decode and display
                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow(f'Video Call - {self.call_peer_ip}', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.end_call()
                            break
                            
            except Exception as e:
                if self.in_call:
                    print(f"❌ Video receive error: {e}")
                break
                
        receive_socket.close()
        cv2.destroyAllWindows()
        
    def _send_control_message(self, peer_ip, message):
        """Send control message to peer"""
        try:
            control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data = json.dumps(message).encode('utf-8')
            control_socket.sendto(data, (peer_ip, self.control_port))
            control_socket.close()
        except Exception as e:
            print(f"❌ Failed to send control message: {e}")
            
    def end_call(self):
        """End the current call"""
        if self.in_call:
            # Notify peer
            end_message = {'type': 'call_ended'}
            self._send_control_message(self.call_peer_ip, end_message)
            
        self._end_call()
        
    def _end_call(self):
        """Clean up call resources"""
        self.in_call = False
        
        # Close audio streams
        if self.audio_input:
            self.audio_input.stop_stream()
            self.audio_input.close()
            self.audio_input = None
            
        if self.audio_output:
            self.audio_output.stop_stream()
            self.audio_output.close()
            self.audio_output = None
            
        # Close video capture
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            
        # Close sockets
        if self.audio_socket:
            self.audio_socket.close()
            self.audio_socket = None
            
        if self.video_socket:
            self.video_socket.close()
            self.video_socket = None
            
        cv2.destroyAllWindows()
        print("📞 Call ended")
        
    def stop_server(self):
        """Stop the voice/video server"""
        self.running = False
        if self.control_socket:
            self.control_socket.close()
        self._end_call()

# Usage example
if __name__ == "__main__":
    import numpy as np
    
    username = input("Enter your username: ")
    handler = VoiceVideoHandler(username)
    handler.start_call_server()
    
    try:
        while True:
            command = input("\nCommands: 'call <ip>' to call, 'quit' to exit: ").strip()
            
            if command.startswith('call '):
                peer_ip = command.split(' ')[1]
                handler.make_call(peer_ip)
            elif command == 'quit':
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        handler.stop_server()