import React, { useState, useEffect } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { documentsAPI, searchAPI } from './services/api';
import DocumentList from './components/DocumentList';
import SearchBar from './components/SearchBar';
import UploadArea from './components/UploadArea';
import SearchResults from './components/SearchResults';
import ChatInterface from './components/ChatInterface';
import WatcherActivity from './components/WatcherActivity';
import './App.css';

function App() {
  const [documents, setDocuments] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('search'); // search, documents, chat
  const [selectedChunks, setSelectedChunks] = useState([]);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    try {
      const docs = await documentsAPI.list();
      setDocuments(docs);
    } catch (error) {
      toast.error('Failed to load documents');
      console.error(error);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await documentsAPI.getStats();
      // Only update stats if we got valid data
      if (statsData && statsData.total_documents !== undefined) {
        setStats(statsData);
      }
    } catch (error) {
      console.error('Failed to load stats', error);
      // Don't clear stats on error - keep showing last known values
    }
  };

  const handleUpload = async (file) => {
    setLoading(true);
    try {
      const result = await documentsAPI.upload(file, (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload progress: ${percentCompleted}%`);
      });

      toast.success(`Document "${result.filename}" uploaded successfully!`);
      await loadDocuments();
      await loadStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      await documentsAPI.delete(documentId);
      toast.success('Document deleted successfully');
      await loadDocuments();
      await loadStats();
    } catch (error) {
      toast.error('Failed to delete document');
      console.error(error);
    }
  };

  const handleSearch = async (query, topK, searchMode = 'hybrid', semanticWeight = 0.7, advancedFilters = {}) => {
    if (!query.trim()) {
      toast.warning('Please enter a search query');
      return;
    }

    setLoading(true);
    try {
      const results = await searchAPI.search(query, topK, null, searchMode, semanticWeight, advancedFilters);
      setSearchResults(results);

      if (results.total_results === 0) {
        toast.info('No results found');
      }
    } catch (error) {
      toast.error('Search failed');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleChunkSelect = (chunk) => {
    setSelectedChunks(prev => {
      const exists = prev.some(c => c.chunk_id === chunk.chunk_id);
      if (exists) {
        return prev.filter(c => c.chunk_id !== chunk.chunk_id);
      } else {
        return [...prev, chunk];
      }
    });
  };

  const handleClearSelection = () => {
    setSelectedChunks([]);
  };

  const handleChatError = (error) => {
    toast.error(`Chat error: ${error.message}`);
  };

  const handleNewWatcherDocument = async () => {
    // Reload documents and stats when watcher processes a new file
    try {
      await loadDocuments();
      await loadStats();
      toast.success('New document processed by file watcher!');
    } catch (error) {
      console.error('Error refreshing after watcher update:', error);
    }
  };

  return (
    <div className="App">
      <ToastContainer position="top-right" autoClose={3000} />

      {/* File Watcher Activity Monitor */}
      <WatcherActivity onNewDocument={handleNewWatcherDocument} />

      {/* Header */}
      <header className="app-header">
        <div className="container header-content">
          <div className="header-left">
            <img src="/logo.png" alt="Knowledge Base" className="app-logo" />
            <div className="header-text">
              <h1>Knowledge Base</h1>
              <p>Semantic search across your documents</p>
            </div>
          </div>

          {/* Stats inline on the right */}
          {stats && (
            <div className="header-stats">
              <div className="stat">
                <span className="stat-icon">📚</span>
                <div className="stat-content">
                  <span className="stat-value">{stats.total_documents}</span>
                  <span className="stat-label">Documents</span>
                </div>
              </div>

              <div className="stat">
                <span className="stat-icon">📦</span>
                <div className="stat-content">
                  <span className="stat-value">{stats.total_chunks}</span>
                  <span className="stat-label">Chunks</span>
                </div>
              </div>

              <div className="stat">
                <span className="stat-icon">
                  <img src="/nn.svg" alt="Neural Network" width="80" height="80" />
                </span>
                <div className="stat-content">
                  <span className="stat-value">{stats.vector_store.count}</span>
                  <span className="stat-label">Embeddings</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="container">
        {/* Tab Navigation */}
        <div className="tabs">
          <button
            className={`tab search-tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search
          </button>
          <button
            className={`tab chat-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat {selectedChunks.length > 0 && `(${selectedChunks.length})`}
          </button>
          <button
            className={`tab documents-tab ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            📚 Documents ({documents.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'search' && (
            <>
              <SearchBar onSearch={handleSearch} loading={loading} documents={documents} />
              {searchResults && (
                <SearchResults
                  results={searchResults}
                  onChunkSelect={handleChunkSelect}
                  selectedChunks={selectedChunks}
                  onChatWithSelected={() => setActiveTab('chat')}
                  onClearSelection={handleClearSelection}
                />
              )}
            </>
          )}
          {activeTab === 'chat' && (
            <ChatInterface
              selectedChunks={selectedChunks}
              onClearSelection={handleClearSelection}
              onError={handleChatError}
            />
          )}
          {activeTab === 'documents' && (
            <>
              <UploadArea onUpload={handleUpload} loading={loading} />
              <DocumentList documents={documents} onDelete={handleDelete} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
