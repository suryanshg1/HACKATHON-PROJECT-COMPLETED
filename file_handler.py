import os
import base64
import json
from pathlib import Path
from datetime import datetime

class FileHandler:
    def __init__(self, files_dir="data/files"):
        self.files_dir = files_dir
        self.ensure_files_dir()
        
    def ensure_files_dir(self):
        """Ensure the files directory exists"""
        Path(self.files_dir).mkdir(parents=True, exist_ok=True)
            
    def process_file_upload(self, file_data):
        """Process an uploaded file"""
        try:
            filename = file_data.get('filename')
            if not filename:
                raise ValueError("Filename not provided")
                
            content = file_data.get('content')
            if not content:
                raise ValueError("File content not provided")
                
            # Decode base64 content
            try:
                file_bytes = base64.b64decode(content)
            except Exception as e:
                raise ValueError(f"Invalid file content: {str(e)}")
                
            # Generate unique filename to prevent overwrites
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            file_path = Path(self.files_dir) / unique_filename
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
                
            # Return file info
            return {
                'success': True,
                'filename': unique_filename,
                'originalName': filename,
                'path': str(file_path),
                'size': len(file_bytes),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def read_file(self, filename):
        """Read a file from the files directory"""
        try:
            file_path = Path(self.files_dir) / filename
            if not file_path.exists():
                raise FileNotFoundError(f"File {filename} not found")
                
            if not file_path.is_file():
                raise ValueError(f"{filename} is not a file")
                
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
                
            return {
                'success': True,
                'filename': filename,
                'content': base64.b64encode(file_bytes).decode('utf-8'),
                'size': len(file_bytes)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def list_files(self):
        """List all files in the files directory"""
        try:
            files = []
            for file_path in Path(self.files_dir).iterdir():
                if file_path.is_file():
                    files.append({
                        'filename': file_path.name,
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            return {
                'success': True,
                'files': files
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def delete_file(self, filename):
        """Delete a file from the files directory"""
        try:
            file_path = Path(self.files_dir) / filename
            if not file_path.exists():
                raise FileNotFoundError(f"File {filename} not found")
                
            if not file_path.is_file():
                raise ValueError(f"{filename} is not a file")
                
            file_path.unlink()
            
            return {
                'success': True,
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def clean_old_files(self, max_age_days=7):
        """Clean files older than max_age_days"""
        try:
            threshold = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            deleted_files = []
            
            for file_path in Path(self.files_dir).iterdir():
                if file_path.is_file():
                    if file_path.stat().st_mtime < threshold:
                        file_path.unlink()
                        deleted_files.append(file_path.name)
                        
            return {
                'success': True,
                'deleted_files': deleted_files
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
