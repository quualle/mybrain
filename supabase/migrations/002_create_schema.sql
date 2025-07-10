-- Documents table for storing metadata about ingested content
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('youtube', 'audio', 'text', 'pdf', 'web')),
    source_url TEXT,
    duration_seconds INTEGER,
    language TEXT DEFAULT 'de',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    summary TEXT,
    summary_embedding vector(1536)
);

-- Chunks table for storing document segments
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_type TEXT DEFAULT 'detail' CHECK (chunk_type IN ('summary', 'topic', 'detail')),
    start_time FLOAT,
    end_time FLOAT,
    speaker TEXT,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    tokens INTEGER,
    importance_score FLOAT DEFAULT 0.5
);

-- ColBERT token embeddings for fine-grained matching
CREATE TABLE colbert_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    token_embeddings JSONB NOT NULL,
    token_texts TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table for tracking dialogue sessions
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    participants TEXT[],
    topic_summary TEXT,
    key_points TEXT[],
    action_items TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Search history for analytics and caching
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    results JSONB NOT NULL,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create indices for performance
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX idx_documents_summary_embedding ON documents 
    USING ivfflat (summary_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX idx_chunks_content_trgm ON chunks USING GIN (content gin_trgm_ops);
CREATE INDEX idx_chunks_metadata ON chunks USING GIN (metadata);
CREATE INDEX idx_chunks_speaker ON chunks(speaker) WHERE speaker IS NOT NULL;
CREATE INDEX idx_chunks_importance ON chunks(importance_score DESC);

CREATE INDEX idx_colbert_chunk_id ON colbert_tokens(chunk_id);

-- Full text search indices
CREATE INDEX idx_chunks_content_fts_de ON chunks 
    USING GIN (to_tsvector('german_custom', content));
CREATE INDEX idx_chunks_content_fts_en ON chunks 
    USING GIN (to_tsvector('english_custom', content));

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();