import React, { useState } from 'react';
import PDFViewer from './PDFViewer';
import './SearchResults.css';

function SearchResults({ results, onChunkSelect, selectedChunks = [], onChatWithSelected, onClearSelection }) {
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [selectedPage, setSelectedPage] = useState(1);
  const [highlightText, setHighlightText] = useState('');

  if (!results || results.total_results === 0) {
    return (
      <div className="search-results empty">
        <p>No results found. Try a different query.</p>
      </div>
    );
  }

  const handleResultClick = (result, e) => {
    // Don't open PDF viewer if clicking on checkbox
    if (e.target.type === 'checkbox') return;

    setSelectedDocument(result.metadata.document_id);
    setSelectedPage(result.metadata.page_number || 1);
    setHighlightText(result.content);
    setPdfViewerOpen(true);
  };

  const closePdfViewer = () => {
    setPdfViewerOpen(false);
    setSelectedDocument(null);
    setSelectedPage(1);
    setHighlightText('');
  };

  const handleChunkToggle = (result, e) => {
    e.stopPropagation();
    if (onChunkSelect) {
      onChunkSelect(result);
    }
  };

  const isChunkSelected = (chunkId) => {
    return selectedChunks.some(chunk => chunk.chunk_id === chunkId);
  };

  return (
    <div className="search-results">
      <div className="results-header">
        <h3>Found {results.total_results} relevant results</h3>
        <div className="results-header-right">
          {selectedChunks.length > 0 && (
            <span className="selected-count">
              {selectedChunks.length} selected for chat
            </span>
          )}
        </div>
      </div>

      <div className="results-list">
        {results.results.map((result, index) => (
          <div
            key={result.chunk_id}
            className={`result-card clickable ${isChunkSelected(result.chunk_id) ? 'selected' : ''}`}
            onClick={(e) => handleResultClick(result, e)}
          >
            <div className="result-header">
              <div className="result-left">
                <label className="chunk-select-checkbox" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isChunkSelected(result.chunk_id)}
                    onChange={(e) => handleChunkToggle(result, e)}
                  />
                </label>
                <span className="result-rank">#{index + 1}</span>
              </div>
              <div className="result-scores">
                <span className="result-score">
                  Score: {(result.score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="result-content">
              {result.content}
            </div>

            <div className="result-metadata">
              <span>📄 {result.metadata.source}</span>
              {result.metadata.page_number && (
                <span>📖 Page {result.metadata.page_number}</span>
              )}
              <span>📍 Chunk {result.metadata.chunk_index + 1}</span>
              <span>📊 {result.metadata.word_count} words</span>
            </div>

            <div className="click-hint">
              Click to view in PDF | Check to use as AI context
            </div>
          </div>
        ))}
      </div>

      <PDFViewer
        isOpen={pdfViewerOpen}
        onClose={closePdfViewer}
        documentId={selectedDocument}
        pageNumber={selectedPage}
        highlightText={highlightText}
      />

      {/* Floating action bar when chunks are selected */}
      {selectedChunks.length > 0 && (
        <div className="selection-action-bar">
          <div className="selection-info">
            <span className="selection-count">{selectedChunks.length}</span>
            <span className="selection-label">chunk{selectedChunks.length > 1 ? 's' : ''} selected</span>
          </div>
          <div className="selection-actions">
            <button
              className="clear-selection-btn"
              onClick={onClearSelection}
            >
              Clear
            </button>
            <button
              className="chat-with-selected-btn"
              onClick={onChatWithSelected}
            >
              Chat with Selected
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchResults;
