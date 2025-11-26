import React, { useState } from 'react';
import AdvancedSearch from './AdvancedSearch';
import './SearchBar.css';

function SearchBar({ onSearch, loading, documents }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
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
    onSearch(query, topK, advancedFilters);
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
      </form>
    </div>
  );
}

export default SearchBar;
