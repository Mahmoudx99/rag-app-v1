import React from 'react';
import './DocumentList.css';

function DocumentList({ documents, onDelete }) {
  if (documents.length === 0) {
    return (
      <div className="document-list empty">
        <p>📭 No documents yet. Upload your first PDF to get started!</p>
      </div>
    );
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getStatusBadge = (status) => {
    const badges = {
      completed: { emoji: '✅', class: 'success', text: 'Completed' },
      processing: { emoji: '⏳', class: 'processing', text: 'Processing' },
      failed: { emoji: '❌', class: 'error', text: 'Failed' },
      pending: { emoji: '⏸️', class: 'pending', text: 'Pending' },
    };
    const badge = badges[status] || badges.pending;
    return (
      <span className={`status-badge ${badge.class}`}>
        {badge.emoji} {badge.text}
      </span>
    );
  };

  return (
    <div className="document-list">
      <h3>📚 Your Documents</h3>

      <div className="documents-grid">
        {documents.map((doc) => (
          <div key={doc.id} className="document-card">
            <div className="document-header">
              <h4>{doc.original_filename}</h4>
              {getStatusBadge(doc.status)}
            </div>

            <div className="document-info">
              {doc.title && (
                <p className="document-title">
                  <strong>Title:</strong> {doc.title}
                </p>
              )}
              {doc.author && (
                <p>
                  <strong>Author:</strong> {doc.author}
                </p>
              )}
              <p>
                <strong>Pages:</strong> {doc.num_pages || 'N/A'}
              </p>
              <p>
                <strong>Chunks:</strong> {doc.num_chunks}
              </p>
              <p>
                <strong>Size:</strong> {formatFileSize(doc.file_size)}
              </p>
              <p>
                <strong>Uploaded:</strong> {formatDate(doc.uploaded_at)}
              </p>
            </div>

            <div className="document-actions">
              <button className="delete-button" onClick={() => onDelete(doc.id)}>
                🗑️ Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DocumentList;
