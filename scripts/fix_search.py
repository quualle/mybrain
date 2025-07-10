#!/usr/bin/env python3
"""Fix the hybrid search function in the database"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def fix_search_function():
    """Update the hybrid_search function to use standard configs"""
    
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        # Drop the old function
        await conn.execute("DROP FUNCTION IF EXISTS hybrid_search CASCADE")
        
        # Create the fixed function
        await conn.execute("""
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
BEGIN
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
                to_tsvector('english', c.content),
                plainto_tsquery('english', query_text)
            ) AS text_rank
        FROM chunks c
        WHERE 
            to_tsvector('english', c.content) @@ plainto_tsquery('english', query_text)
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
        doc_id AS document_id,
        content_text AS content,
        idx AS chunk_index,
        vec_sim AS similarity,
        (0.5 * vec_sim + 0.25 * LEAST(txt_rank / 10, 1)) AS rank,
        meta AS metadata
    FROM combined_results
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$
        """)
        
        print("✅ Successfully fixed hybrid_search function")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_search_function())