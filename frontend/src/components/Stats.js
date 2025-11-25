import React from 'react';
import './Stats.css';

function Stats({ stats }) {
  return (
    <div className="stats-bar">
      <div className="container">
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
      </div>
    </div>
  );
}

export default Stats;
