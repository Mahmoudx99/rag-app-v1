import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './UploadArea.css';

function UploadArea({ onUpload, loading }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onUpload(acceptedFiles[0]);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: false,
    disabled: loading,
  });

  return (
    <div className="upload-area">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${loading ? 'loading' : ''}`}
      >
        <input {...getInputProps()} />
        {loading ? (
          <>
            <div className="spinner"></div>
            <p>Processing your document...</p>
            <p className="upload-hint">Extracting text and generating embeddings</p>
          </>
        ) : isDragActive ? (
          <>
            <p>📥 Drop the PDF here</p>
          </>
        ) : (
          <>
            <p>📄 Drag & drop a PDF here, or click to select</p>
            <p className="upload-hint">Only PDF files are supported (max 50MB)</p>
          </>
        )}
      </div>
    </div>
  );
}

export default UploadArea;
