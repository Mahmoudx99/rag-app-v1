import React, { useState } from 'react';
import './AdvancedSearch.css';

function AdvancedSearch({ documents, onFiltersChange, disabled }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [mustInclude, setMustInclude] = useState('');
  const [mustExclude, setMustExclude] = useState('');
  const [anyOf, setAnyOf] = useState('');

  const handleDocumentToggle = (docId) => {
    const newSelection = selectedDocuments.includes(docId)
      ? selectedDocuments.filter(id => id !== docId)
      : [...selectedDocuments, docId];
    setSelectedDocuments(newSelection);
    updateFilters({ documentIds: newSelection });
  };

  const updateFilters = (partialUpdate) => {
    const filters = {
      documentIds: selectedDocuments,
      dateFrom: dateFrom || null,
      dateTo: dateTo || null,
      mustInclude: mustInclude ? mustInclude.split(',').map(s => s.trim()).filter(s => s) : [],
      mustExclude: mustExclude ? mustExclude.split(',').map(s => s.trim()).filter(s => s) : [],
      anyOf: anyOf ? anyOf.split(',').map(s => s.trim()).filter(s => s) : [],
      ...partialUpdate
    };
    onFiltersChange(filters);
  };

  const handleDateFromChange = (value) => {
    setDateFrom(value);
    updateFilters({ dateFrom: value || null });
  };

  const handleDateToChange = (value) => {
    setDateTo(value);
    updateFilters({ dateTo: value || null });
  };

  const handleMustIncludeChange = (value) => {
    setMustInclude(value);
    const terms = value ? value.split(',').map(s => s.trim()).filter(s => s) : [];
    updateFilters({ mustInclude: terms });
  };

  const handleMustExcludeChange = (value) => {
    setMustExclude(value);
    const terms = value ? value.split(',').map(s => s.trim()).filter(s => s) : [];
    updateFilters({ mustExclude: terms });
  };

  const handleAnyOfChange = (value) => {
    setAnyOf(value);
    const terms = value ? value.split(',').map(s => s.trim()).filter(s => s) : [];
    updateFilters({ anyOf: terms });
  };

  const clearAllFilters = () => {
    setSelectedDocuments([]);
    setDateFrom('');
    setDateTo('');
    setMustInclude('');
    setMustExclude('');
    setAnyOf('');
    onFiltersChange({
      documentIds: [],
      dateFrom: null,
      dateTo: null,
      mustInclude: [],
      mustExclude: [],
      anyOf: []
    });
  };

  const hasActiveFilters = selectedDocuments.length > 0 || dateFrom || dateTo || mustInclude || mustExclude || anyOf;

  return (
    <div className="advanced-search">
      <button
        type="button"
        className={`advanced-toggle ${isExpanded ? 'expanded' : ''} ${hasActiveFilters ? 'has-filters' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
        disabled={disabled}
      >
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
        Advanced Search
        {hasActiveFilters && <span className="filter-badge">Filters Active</span>}
      </button>

      {isExpanded && (
        <div className="advanced-panel">
          <div className="filter-section">
            <h4>Filter by Document</h4>
            <div className="document-filters">
              {documents.length === 0 ? (
                <p className="no-documents">No documents available</p>
              ) : (
                documents.map(doc => (
                  <label key={doc.id} className="document-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedDocuments.includes(doc.id)}
                      onChange={() => handleDocumentToggle(doc.id)}
                      disabled={disabled}
                    />
                    <span className="doc-name">{doc.original_filename}</span>
                    <span className="doc-info">({doc.num_chunks} chunks)</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="filter-section">
            <h4>Filter by Date</h4>
            <div className="date-filters">
              <div className="date-input-group">
                <label>From:</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => handleDateFromChange(e.target.value)}
                  disabled={disabled}
                />
              </div>
              <div className="date-input-group">
                <label>To:</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => handleDateToChange(e.target.value)}
                  disabled={disabled}
                />
              </div>
            </div>
          </div>

          <div className="filter-section">
            <h4>Boolean Operators</h4>
            <div className="boolean-filters">
              <div className="boolean-input-group">
                <label>
                  <span className="operator-badge and">AND</span>
                  Must include all (comma-separated):
                </label>
                <input
                  type="text"
                  placeholder="e.g., machine, learning, neural"
                  value={mustInclude}
                  onChange={(e) => handleMustIncludeChange(e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="boolean-input-group">
                <label>
                  <span className="operator-badge not">NOT</span>
                  Must exclude (comma-separated):
                </label>
                <input
                  type="text"
                  placeholder="e.g., deprecated, outdated"
                  value={mustExclude}
                  onChange={(e) => handleMustExcludeChange(e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="boolean-input-group">
                <label>
                  <span className="operator-badge or">OR</span>
                  Any of (comma-separated):
                </label>
                <input
                  type="text"
                  placeholder="e.g., python, javascript, rust"
                  value={anyOf}
                  onChange={(e) => handleAnyOfChange(e.target.value)}
                  disabled={disabled}
                />
              </div>
            </div>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              className="clear-filters-button"
              onClick={clearAllFilters}
              disabled={disabled}
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default AdvancedSearch;
