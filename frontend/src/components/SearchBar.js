import React, { useState } from 'react';
import AdvancedSearch from './AdvancedSearch';
import './SearchBar.css';

function SearchBar({ onSearch, loading, documents }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [searchMode, setSearchMode] = useState('hybrid');
  const [semanticWeight, setSemanticWeight] = useState(0.7);
  const [advancedFilters, setAdvancedFilters] = useState({
    documentIds: [],
    dateFrom: null,
    dateTo: null,
    mustInclude: [],
    mustExclude: [],
    anyOf: []
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query, topK, searchMode, semanticWeight, advancedFilters);
  };

  const handleFiltersChange = (filters) => {
    setAdvancedFilters(filters);
  };

  return (
    <div className="search-bar">
      <form onSubmit={handleSubmit}>
        <div className="search-input-group">
          <input
            type="text"
            className="search-input"
            placeholder="Ask a question or search for information..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <select
            className="top-k-select"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value))}
            disabled={loading}
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
          </select>
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? '⏳ Searching...' : '🔍 Search'}
          </button>
          <AdvancedSearch
            documents={documents || []}
            onFiltersChange={handleFiltersChange}
            disabled={loading}
          />
        </div>
        <div className="search-mode-group">
          <div className="search-mode-buttons">
            <button
              type="button"
              className={`mode-button ${searchMode === 'hybrid' ? 'active' : ''}`}
              onClick={() => setSearchMode('hybrid')}
              disabled={loading}
            >
              Hybrid
            </button>
            <button
              type="button"
              className={`mode-button ${searchMode === 'semantic' ? 'active' : ''}`}
              onClick={() => setSearchMode('semantic')}
              disabled={loading}
            >
              Semantic
            </button>
            <button
              type="button"
              className={`mode-button ${searchMode === 'keyword' ? 'active' : ''}`}
              onClick={() => setSearchMode('keyword')}
              disabled={loading}
            >
              Keyword
            </button>
          </div>
          {searchMode === 'hybrid' && (
            <div className="semantic-weight-control">
              <label htmlFor="semantic-weight">
                Semantic Weight: {(semanticWeight * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                id="semantic-weight"
                min="0"
                max="1"
                step="0.1"
                value={semanticWeight}
                onChange={(e) => setSemanticWeight(parseFloat(e.target.value))}
                disabled={loading}
              />
              <span className="weight-labels">
                <span>Keyword</span>
                <span>Semantic</span>
              </span>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}

export default SearchBar;
