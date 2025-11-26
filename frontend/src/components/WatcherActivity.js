import React, { useState, useEffect, useRef } from 'react';
import { documentsAPI } from '../services/api';

const WatcherActivity = ({ onNewDocument }) => {
  const [activity, setActivity] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const lastProcessedCountRef = useRef(0);
  const onNewDocumentRef = useRef(onNewDocument);

  // Keep the callback ref updated
  useEffect(() => {
    onNewDocumentRef.current = onNewDocument;
  }, [onNewDocument]);

  useEffect(() => {
    let isMounted = true;

    const fetchActivity = async () => {
      try {
        const data = await documentsAPI.getWatcherActivity();
        if (!isMounted) return;

        setActivity(data);

        // Check for new completions
        if (data.total_processed > lastProcessedCountRef.current && lastProcessedCountRef.current > 0) {
          // New document was processed, notify parent
          if (onNewDocumentRef.current) {
            onNewDocumentRef.current();
          }
        }
        lastProcessedCountRef.current = data.total_processed;
      } catch (error) {
        console.error('Error fetching watcher activity:', error);
        // Don't break the UI on error, just log it
      }
    };

    fetchActivity();
    // Poll every 3 seconds
    const interval = setInterval(fetchActivity, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []); // Empty dependency array - only run once

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTime = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleTimeString();
  };

  const formatDuration = (seconds) => {
    if (!seconds || seconds < 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatETA = (seconds) => {
    if (!seconds || seconds < 0) return 'calculating...';
    if (seconds < 60) return `~${Math.round(seconds)}s`;
    const mins = Math.ceil(seconds / 60);
    return `~${mins}m`;
  };

  const getStatusBadge = (status) => {
    const styles = {
      processing: {
        background: '#fef3c7',
        color: '#92400e',
        border: '1px solid #fcd34d'
      },
      completed: {
        background: '#d1fae5',
        color: '#065f46',
        border: '1px solid #6ee7b7'
      },
      failed: {
        background: '#fee2e2',
        color: '#991b1b',
        border: '1px solid #fca5a5'
      },
      deleted: {
        background: '#fef2f2',
        color: '#dc2626',
        border: '1px solid #f87171'
      }
    };

    const statusStyle = styles[status] || styles.failed;

    return (
      <span style={{
        ...statusStyle,
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '12px',
        fontWeight: '500',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px'
      }}>
        {status === 'processing' && (
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#f59e0b',
            animation: 'pulse 1.5s infinite'
          }} />
        )}
        {status === 'deleted' && (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        )}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Clear all watcher activity history?')) return;
    setIsLoading(true);
    try {
      await documentsAPI.clearWatcherActivity();
      setActivity(prev => ({
        ...prev,
        recent_activities: [],
        total_processed: 0,
        total_failed: 0
      }));
    } catch (error) {
      console.error('Error clearing history:', error);
    } finally {
      setIsLoading(false);
    }
  };


  if (!activity) {
    return null;
  }

  const hasActivity = activity.recent_activities.length > 0;
  const processingCount = activity.recent_activities.filter(a => a.status === 'processing').length;
  const completedCount = activity.recent_activities.filter(a => a.status === 'completed').length;
  const totalInBatch = processingCount + completedCount;

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      zIndex: 1000,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Notification Badge */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: activity.is_active ? '#f59e0b' : '#6b7280',
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          width: '56px',
          height: '56px',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          fontWeight: '600',
          transition: 'all 0.3s ease',
          position: 'relative'
        }}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
        {processingCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '-4px',
            right: '-4px',
            background: '#ef4444',
            borderRadius: '50%',
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '11px',
            fontWeight: 'bold'
          }}>
            {processingCount}
          </span>
        )}
      </button>

      {/* Activity Panel */}
      {isExpanded && (
        <div style={{
          position: 'absolute',
          bottom: '70px',
          right: '0',
          width: '400px',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            background: '#f8fafc',
            padding: '16px',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#1e293b' }}>
                File Watcher Activity
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
                {activity.total_processed} processed, {activity.total_failed} failed
                {activity.recent_activities.filter(a => a.status === 'deleted').length > 0 && (
                  <>, <span style={{ color: '#dc2626' }}>
                    {activity.recent_activities.filter(a => a.status === 'deleted').length} deleted
                  </span></>
                )}
              </p>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              {activity.is_active && (
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  color: '#f59e0b',
                  fontWeight: '500'
                }}>
                  <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: '#f59e0b',
                    animation: 'pulse 1.5s infinite'
                  }} />
                  Processing
                </span>
              )}
            </div>
          </div>

          {/* Batch Progress Summary - shown when processing */}
          {processingCount > 0 && (
            <div style={{
              background: '#fef3c7',
              padding: '12px 16px',
              borderBottom: '1px solid #fcd34d'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#92400e'
                }}>
                  Batch Progress
                </span>
                <span style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#92400e'
                }}>
                  {completedCount}/{totalInBatch} documents
                </span>
              </div>
              {/* Overall batch progress bar */}
              <div style={{
                width: '100%',
                height: '8px',
                background: '#fde68a',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${totalInBatch > 0 ? (completedCount / totalInBatch) * 100 : 0}%`,
                  height: '100%',
                  background: '#f59e0b',
                  borderRadius: '4px',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}

          {/* Activity List */}
          <div style={{
            maxHeight: '300px',
            overflowY: 'auto',
            padding: '8px'
          }}>
            {!hasActivity ? (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                color: '#94a3b8'
              }}>
                <p style={{ margin: 0, fontSize: '14px' }}>No recent activity</p>
                <p style={{ margin: '8px 0 0', fontSize: '12px' }}>
                  Drop PDF files into <code style={{ background: '#f1f5f9', padding: '2px 4px', borderRadius: '4px' }}>./data/watch/</code> to process automatically
                </p>
              </div>
            ) : (
              activity.recent_activities.slice(0, 10).map((item) => (
                <div
                  key={item.event_id}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: item.status === 'processing' ? '#fffbeb' : '#f8fafc',
                    marginBottom: '8px',
                    border: item.status === 'processing' ? '1px solid #fcd34d' : '1px solid #e2e8f0'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '8px'
                  }}>
                    <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontWeight: '500',
                          fontSize: '14px',
                          color: '#1e293b',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {item.filename}
                        </div>
                        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                          {formatFileSize(item.file_size)}
                        </div>
                      </div>
                    </div>
                    {getStatusBadge(item.status)}
                  </div>

                  {/* Progress Bar for Processing Items */}
                  {item.status === 'processing' && (
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '11px',
                        color: '#92400e',
                        marginBottom: '4px'
                      }}>
                        <span style={{ fontWeight: '500' }}>
                          {item.chunks_processed}/{item.chunks_estimated || '?'} chunks
                        </span>
                        <span style={{ fontWeight: '600' }}>
                          {item.progress_percent ? `${item.progress_percent.toFixed(1)}%` : 'Starting...'}
                        </span>
                      </div>
                      <div style={{
                        width: '100%',
                        height: '6px',
                        background: '#fde68a',
                        borderRadius: '3px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${item.progress_percent || 0}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #f59e0b, #fbbf24)',
                          borderRadius: '3px',
                          transition: 'width 0.5s ease',
                          animation: 'progressPulse 2s infinite'
                        }} />
                      </div>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '10px',
                        color: '#92400e',
                        marginTop: '4px'
                      }}>
                        <span>
                          ⏱️ {formatDuration(item.elapsed_seconds)}
                        </span>
                        {item.processing_rate && (
                          <span>
                            ⚡ {item.processing_rate} chunks/s
                          </span>
                        )}
                        {item.estimated_remaining_seconds && (
                          <span>
                            🏁 ETA: {formatETA(item.estimated_remaining_seconds)}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    color: '#64748b'
                  }}>
                    <span>
                      {item.status === 'deleted' ? 'Deleted' :
                       item.status === 'reprocessed' ? 'Reprocessed' :
                       item.status === 'processing' ? 'Started' : 'Started'}: {formatTime(item.started_at)}
                    </span>
                    {item.status === 'completed' && (
                      <span>{item.num_chunks} chunks</span>
                    )}
                    {item.status === 'deleted' && (
                      <span style={{ color: '#dc2626' }}>
                        Removed {item.num_chunks} chunks
                      </span>
                    )}
                    {item.status === 'failed' && item.error_message && (
                      <span style={{ color: '#dc2626' }} title={item.error_message}>
                        Error
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer with Actions */}
          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid #e2e8f0',
            background: '#f8fafc'
          }}>
            <div style={{
              display: 'flex',
              gap: '8px',
              marginBottom: '8px'
            }}>
              <button
                onClick={handleClearHistory}
                disabled={isLoading || !hasActivity}
                style={{
                  width: '100%',
                  padding: '6px 12px',
                  fontSize: '11px',
                  fontWeight: '500',
                  background: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  cursor: isLoading || !hasActivity ? 'not-allowed' : 'pointer',
                  opacity: isLoading || !hasActivity ? 0.5 : 1,
                  color: '#475569'
                }}
              >
                Clear History
              </button>
            </div>
            <div style={{
              fontSize: '11px',
              color: '#64748b',
              textAlign: 'center'
            }}>
              Auto-refreshing every 3 seconds
            </div>
          </div>
        </div>
      )}

      {/* CSS Animation */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
          @keyframes progressPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.85; }
          }
        `}
      </style>
    </div>
  );
};

export default WatcherActivity;
