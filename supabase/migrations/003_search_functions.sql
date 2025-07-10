-- Hybrid search function combining vector similarity and full-text search
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    match_count INT DEFAULT 20,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    chunk_index INT,
    similarity FLOAT,
    rank FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    query_language TEXT;
BEGIN
    -- Detect query language (simplified - in production use proper detection)
    IF query_text ~ '[äöüßÄÖÜ]' THEN
        query_language := 'german_custom';
    ELSE
        query_language := 'english_custom';
    END IF;

    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.metadata,
            1 - (c.embedding <=> query_embedding) AS vector_similarity
        FROM chunks c
        WHERE 
            c.embedding IS NOT NULL
            AND (filter_metadata IS NULL OR c.metadata @> filter_metadata)
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    text_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.metadata,
            ts_rank_cd(
                to_tsvector(query_language, c.content),
                plainto_tsquery(query_language, query_text)
            ) AS text_rank
        FROM chunks c
        WHERE 
            to_tsvector(query_language, c.content) @@ plainto_tsquery(query_language, query_text)
            AND (filter_metadata IS NULL OR c.metadata @> filter_metadata)
        ORDER BY text_rank DESC
        LIMIT match_count * 2
    ),
    combined_results AS (
        SELECT 
            COALESCE(v.id, t.id) AS chunk_id,
            COALESCE(v.document_id, t.document_id) AS doc_id,
            COALESCE(v.content, t.content) AS content_text,
            COALESCE(v.chunk_index, t.chunk_index) AS idx,
            COALESCE(v.metadata, t.metadata) AS meta,
            COALESCE(v.vector_similarity, 0) AS vec_sim,
            COALESCE(t.text_rank, 0) AS txt_rank
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT 
        chunk_id,
        doc_id,
        content_text,
        idx,
        vec_sim AS similarity,
        -- Weighted combination: 50% vector, 25% text, 25% recency boost
        (0.5 * vec_sim + 0.25 * LEAST(txt_rank / 10, 1)) AS rank,
        meta
    FROM combined_results
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;

-- Function to get document summary with context
CREATE OR REPLACE FUNCTION get_document_context(doc_id UUID)
RETURNS TABLE (
    document_title TEXT,
    document_summary TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    participants TEXT[],
    key_points TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.title,
        d.summary,
        d.source_type,
        d.created_at,
        c.participants,
        c.key_points
    FROM documents d
    LEFT JOIN conversations c ON c.document_id = d.id
    WHERE d.id = doc_id;
END;
$$;

-- Function to search by speaker
CREATE OR REPLACE FUNCTION search_by_speaker(
    speaker_name TEXT,
    query_embedding vector(1536) DEFAULT NULL,
    match_count INT DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    speaker TEXT,
    start_time FLOAT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.document_id,
        c.content,
        c.speaker,
        c.start_time,
        CASE 
            WHEN query_embedding IS NOT NULL THEN 1 - (c.embedding <=> query_embedding)
            ELSE 1.0
        END AS similarity
    FROM chunks c
    WHERE 
        c.speaker ILIKE '%' || speaker_name || '%'
        AND c.chunk_type = 'detail'
    ORDER BY 
        CASE 
            WHEN query_embedding IS NOT NULL THEN c.embedding <=> query_embedding
            ELSE 0
        END,
        c.created_at DESC
    LIMIT match_count;
END;
$$;

-- Function for time-based retrieval
CREATE OR REPLACE FUNCTION search_by_timerange(
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    query_embedding vector(1536) DEFAULT NULL,
    match_count INT DEFAULT 20
)
RETURNS TABLE (
    document_id UUID,
    title TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    summary TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.title,
        d.source_type,
        d.created_at,
        d.summary,
        CASE 
            WHEN query_embedding IS NOT NULL AND d.summary_embedding IS NOT NULL 
            THEN 1 - (d.summary_embedding <=> query_embedding)
            ELSE 1.0
        END AS similarity
    FROM documents d
    WHERE 
        d.created_at BETWEEN start_date AND end_date
    ORDER BY 
        CASE 
            WHEN query_embedding IS NOT NULL AND d.summary_embedding IS NOT NULL 
            THEN d.summary_embedding <=> query_embedding
            ELSE 0
        END,
        d.created_at DESC
    LIMIT match_count;
END;
$$;