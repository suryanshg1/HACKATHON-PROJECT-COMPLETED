import React, { useEffect } from 'react';
import './FilePreview.css';

interface FilePreviewProps {
  file: File;
  progress?: number;
  onCancel?: () => void;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, progress, onCancel }) => {
  const isImage = file.type.startsWith('image/');
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);

  useEffect(() => {
    if (!isImage) return;

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file, isImage]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="file-preview">
      <div className="file-preview-content">
        {isImage && previewUrl ? (
          <img src={previewUrl} alt={file.name} className="file-thumbnail" />
        ) : (
          <div className="file-icon">
            {file.type.includes('pdf') ? '📄' : 
             file.type.includes('video') ? '🎥' : 
             file.type.includes('audio') ? '🎵' : '📁'}
          </div>
        )}
        <div className="file-info">
          <div className="file-name">{file.name}</div>
          <div className="file-size">{formatFileSize(file.size)}</div>
        </div>
      </div>
      {typeof progress === 'number' && (
        <div className="progress-bar-container">
          <div 
            className="progress-bar"
            style={{ width: `${progress}%` }}
          />
          <div className="progress-text">{progress}%</div>
        </div>
      )}
      {onCancel && (
        <button 
          className="cancel-button"
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          title="Cancel"
        >
          ✕
        </button>
      )}
    </div>
  );
};

export default FilePreview;