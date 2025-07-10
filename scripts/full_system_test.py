#!/usr/bin/env python3
"""
Comprehensive test and fix script for MyBrain
This will test all components and automatically fix any issues found
"""

import asyncio
import asyncpg
import os
import sys
import json
import httpx
from datetime import datetime
from colorama import init, Fore, Style
from dotenv import load_dotenv

# Initialize colorama for colored output
init()

# Load environment variables
load_dotenv()

class MyBrainTester:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.issues_found = []
        self.fixes_applied = []
        
    def log_success(self, message):
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
        
    def log_error(self, message):
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
        self.issues_found.append(message)
        
    def log_info(self, message):
        print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")
        
    def log_warning(self, message):
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
        
    def log_fix(self, message):
        print(f"{Fore.GREEN}🔧 FIXED: {message}{Style.RESET_ALL}")
        self.fixes_applied.append(message)

    async def test_database_connection(self):
        """Test database connectivity"""
        self.log_info("Testing database connection...")
        try:
            conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
            await conn.fetchval("SELECT 1")
            await conn.close()
            self.log_success("Database connection successful")
            return True
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return False

    async def fix_database_functions(self):
        """Fix all database functions"""
        self.log_info("Fixing database functions...")
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # Fix hybrid_search function
            await conn.execute("DROP FUNCTION IF EXISTS hybrid_search CASCADE")
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
            c.id AS chunk_id_v,
            c.document_id AS document_id_v,
            c.content AS content_v,
            c.chunk_index AS chunk_index_v,
            c.metadata AS metadata_v,
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
            c.id AS chunk_id_t,
            c.document_id AS document_id_t,
            c.content AS content_t,
            c.chunk_index AS chunk_index_t,
            c.metadata AS metadata_t,
            ts_rank_cd(
                to_tsvector('simple', c.content),
                plainto_tsquery('simple', query_text)
            ) AS text_rank
        FROM chunks c
        WHERE 
            query_text IS NOT NULL 
            AND query_text != ''
            AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', query_text)
            AND (filter_metadata IS NULL OR c.metadata @> filter_metadata)
        ORDER BY text_rank DESC
        LIMIT match_count * 2
    ),
    combined_results AS (
        SELECT 
            COALESCE(v.chunk_id_v, t.chunk_id_t) AS combined_chunk_id,
            COALESCE(v.document_id_v, t.document_id_t) AS combined_document_id,
            COALESCE(v.content_v, t.content_t) AS combined_content,
            COALESCE(v.chunk_index_v, t.chunk_index_t) AS combined_chunk_index,
            COALESCE(v.metadata_v, t.metadata_t) AS combined_metadata,
            COALESCE(v.vector_similarity, 0) AS vec_sim,
            COALESCE(t.text_rank, 0) AS txt_rank
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.chunk_id_v = t.chunk_id_t
    )
    SELECT 
        combined_chunk_id,
        combined_document_id,
        combined_content,
        combined_chunk_index,
        vec_sim,
        (0.5 * vec_sim + 0.25 * LEAST(txt_rank / 10, 1)) AS combined_rank,
        combined_metadata
    FROM combined_results
    WHERE combined_chunk_id IS NOT NULL
    ORDER BY combined_rank DESC
    LIMIT match_count;
END;
$$;
            """)
            self.log_fix("Fixed hybrid_search function (column ambiguity)")
            
            # Fix search_by_speaker function
            await conn.execute("DROP FUNCTION IF EXISTS search_by_speaker CASCADE")
            await conn.execute("""
CREATE OR REPLACE FUNCTION search_by_speaker(
    speaker_name TEXT,
    query_embedding vector(1536) DEFAULT NULL,
    match_count INT DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    chunk_index INT,
    speaker TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.speaker,
            1 - (c.embedding <=> query_embedding) AS sim,
            c.metadata
        FROM chunks c
        WHERE 
            c.speaker ILIKE '%' || speaker_name || '%'
            AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;
    ELSE
        RETURN QUERY
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.speaker,
            c.importance_score AS sim,
            c.metadata
        FROM chunks c
        WHERE 
            c.speaker ILIKE '%' || speaker_name || '%'
        ORDER BY c.created_at DESC
        LIMIT match_count;
    END IF;
END;
$$;
            """)
            self.log_fix("Fixed search_by_speaker function")
            
            # Fix search_by_timerange function
            await conn.execute("DROP FUNCTION IF EXISTS search_by_timerange CASCADE")
            await conn.execute("""
CREATE OR REPLACE FUNCTION search_by_timerange(
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    query_embedding vector(1536) DEFAULT NULL,
    match_count INT DEFAULT 20
)
RETURNS TABLE (
    document_id UUID,
    title TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    summary_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            d.id,
            d.title,
            d.source_type,
            d.created_at,
            1 - (d.summary_embedding <=> query_embedding) AS score
        FROM documents d
        WHERE 
            d.created_at BETWEEN start_time AND end_time
            AND d.summary_embedding IS NOT NULL
        ORDER BY d.summary_embedding <=> query_embedding
        LIMIT match_count;
    ELSE
        RETURN QUERY
        SELECT 
            d.id,
            d.title,
            d.source_type,
            d.created_at,
            1.0 AS score
        FROM documents d
        WHERE 
            d.created_at BETWEEN start_time AND end_time
        ORDER BY d.created_at DESC
        LIMIT match_count;
    END IF;
END;
$$;
            """)
            self.log_fix("Fixed search_by_timerange function")
            
        finally:
            await conn.close()

    async def test_backend_health(self):
        """Test backend API health"""
        self.log_info("Testing backend health...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.backend_url}/health")
                if response.status_code == 200:
                    self.log_success(f"Backend is healthy: {response.json()}")
                    return True
                else:
                    self.log_error(f"Backend health check failed: {response.status_code}")
                    return False
            except Exception as e:
                self.log_error(f"Backend not accessible: {e}")
                return False

    async def test_text_ingestion(self):
        """Test text ingestion"""
        self.log_info("Testing text ingestion...")
        
        test_content = {
            "title": "Test Document",
            "content": "This is a test document for MyBrain system testing. It contains some sample content."
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.backend_url}/api/v1/ingest/text",
                    json=test_content
                )
                if response.status_code == 200:
                    result = response.json()
                    self.log_success(f"Text ingestion successful: {result}")
                    return result.get("document_id")
                else:
                    self.log_error(f"Text ingestion failed: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                self.log_error(f"Text ingestion error: {e}")
                return None

    async def test_search(self, query="test document"):
        """Test search functionality"""
        self.log_info(f"Testing search with query: '{query}'...")
        
        async with httpx.AsyncClient() as client:
            try:
                # Test direct search endpoint
                response = await client.post(
                    f"{self.backend_url}/api/v1/search/",
                    json={"query": query, "top_k": 5}
                )
                if response.status_code == 200:
                    results = response.json()
                    self.log_success(f"Search successful: Found {len(results.get('results', []))} results")
                    return True
                else:
                    self.log_error(f"Search failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                self.log_error(f"Search error: {e}")
                return False

    async def test_chat(self):
        """Test chat functionality"""
        self.log_info("Testing chat functionality...")
        
        test_message = {
            "message": "What is the test document about?",
            "use_rag": True,
            "stream": False,
            "model": "claude-sonnet-4.0"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.backend_url}/api/v1/chat/",
                    json=test_message
                )
                if response.status_code == 200:
                    result = response.json()
                    self.log_success(f"Chat successful: {result.get('response', '')[:100]}...")
                    return True
                else:
                    self.log_error(f"Chat failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                self.log_error(f"Chat error: {e}")
                return False

    async def cleanup_test_data(self):
        """Clean up test data"""
        self.log_info("Cleaning up test data...")
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            # Delete test documents
            await conn.execute("""
                DELETE FROM chunks WHERE document_id IN (
                    SELECT id FROM documents WHERE title = 'Test Document'
                )
            """)
            await conn.execute("DELETE FROM documents WHERE title = 'Test Document'")
            self.log_success("Test data cleaned up")
        finally:
            await conn.close()

    async def run_all_tests(self):
        """Run all tests and fixes"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"MyBrain Comprehensive System Test & Fix")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        # 1. Test database
        if not await self.test_database_connection():
            self.log_error("Cannot proceed without database connection")
            return
        
        # 2. Fix database functions
        await self.fix_database_functions()
        
        # 3. Test backend
        if not await self.test_backend_health():
            self.log_warning("Backend not running. Please ensure backend is started.")
            return
        
        # 4. Test ingestion
        doc_id = await self.test_text_ingestion()
        if not doc_id:
            self.log_warning("Text ingestion failed - skipping search/chat tests")
        else:
            # 5. Test search
            await asyncio.sleep(2)  # Give time for indexing
            await self.test_search()
            
            # 6. Test chat
            await self.test_chat()
        
        # 7. Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print("Test Summary")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        if self.issues_found:
            print(f"{Fore.YELLOW}Issues Found:{Style.RESET_ALL}")
            for issue in self.issues_found:
                print(f"  - {issue}")
            print()
        
        if self.fixes_applied:
            print(f"{Fore.GREEN}Fixes Applied:{Style.RESET_ALL}")
            for fix in self.fixes_applied:
                print(f"  - {fix}")
            print()
        
        if not self.issues_found or all(fix in str(self.fixes_applied) for fix in self.issues_found):
            print(f"{Fore.GREEN}✅ All tests passed! System is ready to use.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}⚠️  Some issues remain. Please check the logs above.{Style.RESET_ALL}")

async def main():
    tester = MyBrainTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    # Install colorama if not installed
    try:
        import colorama
    except ImportError:
        print("Installing colorama for colored output...")
        os.system(f"{sys.executable} -m pip install colorama")
        import colorama
    
    asyncio.run(main())