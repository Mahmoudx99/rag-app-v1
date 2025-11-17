import React, { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';
import MessageRenderer from './MessageRenderer';
import './ChatInterface.css';

function ChatInterface({ selectedChunks, onClearSelection, onError }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [useSearchTool, setUseSearchTool] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [expandedContexts, setExpandedContexts] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Add user message to display
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      // Prepare context chunks if any are selected
      const contextToSend = selectedChunks.map(chunk => ({
        chunk_id: chunk.chunk_id,
        content: chunk.content,
        metadata: chunk.metadata
      }));

      // Send message to API
      const response = await chatAPI.sendMessage(
        userMessage,
        contextToSend,
        useSearchTool,
        conversationId
      );

      // Update conversation ID
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Add assistant message to display
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date().toISOString(),
        usage: response.usage,
        model: response.model
      };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        role: 'error',
        content: `Failed to get response: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      if (onError) onError(error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    onClearSelection();
  };

  const handleClearContext = () => {
    onClearSelection();
  };

  const formatSource = (source) => {
    const filename = source.metadata?.source || 'Unknown';
    const page = source.metadata?.page_number || 'N/A';
    return `${filename} (Page ${page})`;
  };

  const toggleContextExpand = (messageIndex) => {
    setExpandedContexts(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }));
  };

  const truncateContent = (content, maxLength = 200) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h3>AI Chat</h3>
        <div className="chat-controls">
          <label className="search-tool-toggle">
            <input
              type="checkbox"
              checked={useSearchTool}
              onChange={(e) => setUseSearchTool(e.target.checked)}
              disabled={loading}
            />
            <span>Allow AI to search knowledge base</span>
          </label>
          <button
            className="new-chat-button"
            onClick={handleNewConversation}
            disabled={loading}
          >
            New Chat
          </button>
        </div>
      </div>

      {selectedChunks.length > 0 && (
        <div className="context-indicator">
          <span className="context-badge">
            {selectedChunks.length} chunk{selectedChunks.length > 1 ? 's' : ''} selected as context
          </span>
          <button
            className="clear-context-button"
            onClick={handleClearContext}
            disabled={loading}
          >
            Clear Context
          </button>
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h4>Start a conversation</h4>
            <p>
              {selectedChunks.length > 0
                ? `You have ${selectedChunks.length} chunk(s) selected as context. The AI will use this information to answer your questions.`
                : useSearchTool
                ? 'The AI can search your knowledge base to find relevant information.'
                : 'Type a message to chat directly with the AI.'}
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="message-header">
                <span className="message-role">
                  {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'AI' : 'Error'}
                </span>
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="message-content">
                {msg.role === 'assistant' ? (
                  <MessageRenderer content={msg.content} />
                ) : (
                  msg.content
                )}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <div className="sources-header">
                    <span className="sources-label">Sources ({msg.sources.length}):</span>
                    <button
                      className="view-context-button"
                      onClick={() => toggleContextExpand(index)}
                    >
                      {expandedContexts[index] ? 'Hide Context' : 'View Context'}
                    </button>
                  </div>
                  <ul className="sources-list">
                    {msg.sources.map((source, i) => (
                      <li key={i}>{formatSource(source)}</li>
                    ))}
                  </ul>
                  {expandedContexts[index] && (
                    <div className="context-viewer">
                      <div className="context-viewer-header">
                        Retrieved Context (What AI Sees)
                      </div>
                      <div className="context-chunks">
                        {msg.sources.map((source, i) => (
                          <div key={i} className="context-chunk">
                            <div className="context-chunk-header">
                              <span className="chunk-number">Chunk {i + 1}</span>
                              <span className="chunk-source">{formatSource(source)}</span>
                            </div>
                            <div className="context-chunk-content">
                              {source.content || 'No content available'}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {msg.usage && Object.keys(msg.usage).length > 0 && (
                <div className="message-usage">
                  <span>Tokens: {msg.usage.total_tokens || 'N/A'}</span>
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="message assistant loading">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            selectedChunks.length > 0
              ? 'Ask about the selected content...'
              : useSearchTool
              ? 'Ask anything (AI will search if needed)...'
              : 'Type your message...'
          }
          disabled={loading}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="send-button"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;
