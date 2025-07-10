-- Add full_content column to documents table for storing complete original transcripts
-- This enables: a) future reprocessing b) full context loading for detailed questions

ALTER TABLE documents 
ADD COLUMN full_content TEXT;

-- Create index for full-text search on complete content
CREATE INDEX idx_documents_full_content_fts ON documents 
    USING GIN (to_tsvector('german_custom', full_content));

-- Add a flag to indicate if we should load full context for certain queries
ALTER TABLE documents
ADD COLUMN content_type TEXT DEFAULT 'chunked' CHECK (content_type IN ('chunked', 'full', 'hybrid'));

-- Create a function to decide when to use full content
CREATE OR REPLACE FUNCTION should_use_full_content(
    query TEXT,
    document_id UUID
) RETURNS BOOLEAN AS $$
DECLARE
    doc_size INTEGER;
    is_detail_query BOOLEAN;
BEGIN
    -- Get document size
    SELECT LENGTH(full_content) INTO doc_size
    FROM documents WHERE id = document_id;
    
    -- Check if query indicates need for full context
    is_detail_query := query ~* '(gesamt|vollständig|komplett|alles|detail|genau|exakt|wörtlich)';
    
    -- Use full content if:
    -- 1. Document is reasonably sized (< 50k chars)
    -- 2. Query asks for complete/detailed information
    -- 3. Query references "dieses Gespräch" or "dieses Transkript"
    RETURN doc_size < 50000 AND (
        is_detail_query OR 
        query ~* '(dieses|diesem|diese) (gespräch|transkript|video|interview)'
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get full document context when needed
CREATE OR REPLACE FUNCTION get_full_document_context(
    document_id UUID,
    query TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    title TEXT,
    full_content TEXT,
    summary TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    metadata JSONB,
    should_use_full BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.title,
        d.full_content,
        d.summary,
        d.source_type,
        d.created_at,
        d.metadata,
        CASE 
            WHEN query IS NULL THEN FALSE
            ELSE should_use_full_content(query, d.id)
        END as should_use_full
    FROM documents d
    WHERE d.id = document_id;
END;
$$ LANGUAGE plpgsql;