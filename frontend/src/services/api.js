/**
 * API service for communicating with backend
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Documents API
export const documentsAPI = {
  // Upload a document
  upload: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
    return response.data;
  },

  // Get all documents
  list: async () => {
    const response = await api.get('/documents/');
    return response.data;
  },

  // Get a specific document
  get: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  // Delete a document
  delete: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },

  // Get stats
  getStats: async () => {
    const response = await api.get('/documents/stats/overview');
    return response.data;
  },

  // Get watcher activity
  getWatcherActivity: async () => {
    const response = await api.get('/documents/watcher/activity');
    return response.data;
  },

  // Clear watcher activity
  clearWatcherActivity: async () => {
    const response = await api.delete('/documents/watcher/activity');
    return response.data;
  },

  // Reprocess deleted files (remove deleted status from tracker)
  reprocessDeletedFiles: async (eventIds = null) => {
    const response = await api.post('/documents/watcher/reprocess-deleted', {
      event_ids: eventIds || []
    });
    return response.data;
  },
};

// Search API
export const searchAPI = {
  search: async (query, topK = 5, documentId = null, searchMode = 'hybrid', semanticWeight = 0.7, advancedFilters = {}) => {
    const requestBody = {
      query,
      top_k: topK,
      search_mode: searchMode,
      semantic_weight: semanticWeight,
    };

    // Handle document filtering
    if (advancedFilters.documentIds && advancedFilters.documentIds.length > 0) {
      requestBody.document_ids = advancedFilters.documentIds;
    } else if (documentId) {
      requestBody.document_id = documentId;
    }

    // Handle date filters
    if (advancedFilters.dateFrom) {
      requestBody.date_from = advancedFilters.dateFrom;
    }
    if (advancedFilters.dateTo) {
      requestBody.date_to = advancedFilters.dateTo;
    }

    // Handle boolean operators
    if (advancedFilters.mustInclude && advancedFilters.mustInclude.length > 0) {
      requestBody.must_include = advancedFilters.mustInclude;
    }
    if (advancedFilters.mustExclude && advancedFilters.mustExclude.length > 0) {
      requestBody.must_exclude = advancedFilters.mustExclude;
    }
    if (advancedFilters.anyOf && advancedFilters.anyOf.length > 0) {
      requestBody.any_of = advancedFilters.anyOf;
    }

    const response = await api.post('/search/', requestBody);
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  // Send a chat message
  sendMessage: async (message, contextChunks = [], useSearchTool = false, conversationId = null, systemPrompt = null) => {
    const requestBody = {
      message,
      use_search_tool: useSearchTool,
    };

    if (conversationId) {
      requestBody.conversation_id = conversationId;
    }

    if (contextChunks && contextChunks.length > 0) {
      requestBody.context_chunks = contextChunks.map(chunk => ({
        chunk_id: chunk.chunk_id,
        content: chunk.content,
        metadata: chunk.metadata
      }));
    }

    if (systemPrompt) {
      requestBody.system_prompt = systemPrompt;
    }

    const response = await api.post('/chat/', requestBody);
    return response.data;
  },

  // Get conversation history
  getHistory: async (conversationId) => {
    const response = await api.get(`/chat/history/${conversationId}`);
    return response.data;
  },

  // Clear conversation history
  clearHistory: async (conversationId) => {
    const response = await api.delete(`/chat/history/${conversationId}`);
    return response.data;
  },

  // Check chat service health
  getHealth: async () => {
    const response = await api.get('/chat/health');
    return response.data;
  },
};

export default api;
