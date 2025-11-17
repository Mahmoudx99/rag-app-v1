-- Migration: Add streaming progress tracking columns to documents table
-- This migration adds columns needed for tracking progressive/streaming document processing
-- Run this if you have an existing database. New databases will create these columns automatically.

-- Add chunks_processed column (tracks how many chunks have been embedded and stored)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunks_processed INTEGER DEFAULT 0;

-- Add chunks_estimated column (estimated total chunks based on page count)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunks_estimated INTEGER;

-- Add processing_started_at column (when processing began)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE;

-- Add last_chunk_at column (timestamp of last chunk processed)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_chunk_at TIMESTAMP WITH TIME ZONE;

-- Update any existing completed documents to have chunks_processed = num_chunks
UPDATE documents
SET chunks_processed = num_chunks
WHERE status = 'completed' AND chunks_processed = 0 AND num_chunks > 0;
