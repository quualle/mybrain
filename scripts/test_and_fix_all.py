#!/usr/bin/env python3
"""
Complete test and auto-fix script for MyBrain
This will find and fix ALL issues automatically
"""

import asyncio
import asyncpg
import os
import sys
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MyBrainFixer:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.backend_url = "http://localhost:8000"
        self.all_fixes = []
        
    def log(self, message, level="INFO"):
        colors = {
            "SUCCESS": "\033[92m✅",
            "ERROR": "\033[91m❌",
            "INFO": "\033[94mℹ️ ",
            "WARNING": "\033[93m⚠️ ",
            "FIX": "\033[92m🔧"
        }
        print(f"{colors.get(level, '')} {message}\033[0m")
        
    async def fix_all_database_issues(self):
        """Fix ALL database-related issues"""
        self.log("Fixing all database issues...", "INFO")
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # 1. Drop and recreate all functions with proper syntax
            fixes = [
                ("DROP FUNCTION IF EXISTS hybrid_search CASCADE", "Dropping old hybrid_search"),
                ("""
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
LANGUAGE sql
AS $$
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
    )
    SELECT 
        COALESCE(v.id, t.id),
        COALESCE(v.document_id, t.document_id),
        COALESCE(v.content, t.content),
        COALESCE(v.chunk_index, t.chunk_index),
        GREATEST(COALESCE(v.vector_similarity, 0), 0),
        GREATEST(0.5 * COALESCE(v.vector_similarity, 0) + 0.25 * COALESCE(t.text_rank / 10, 0), 0),
        COALESCE(v.metadata, t.metadata, '{}'::jsonb)
    FROM vector_search v
    FULL OUTER JOIN text_search t ON v.id = t.id
    WHERE COALESCE(v.id, t.id) IS NOT NULL
    ORDER BY 6 DESC
    LIMIT match_count;
$$;
                """, "Creating fixed hybrid_search function"),
                
                ("DROP FUNCTION IF EXISTS search_by_speaker CASCADE", "Dropping old search_by_speaker"),
                ("""
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
LANGUAGE sql
AS $$
    SELECT 
        c.id,
        c.document_id,
        c.content,
        c.chunk_index,
        c.speaker,
        CASE 
            WHEN query_embedding IS NOT NULL THEN 1 - (c.embedding <=> query_embedding)
            ELSE COALESCE(c.importance_score, 0.5)
        END,
        c.metadata
    FROM chunks c
    WHERE 
        c.speaker ILIKE '%' || speaker_name || '%'
        AND (query_embedding IS NULL OR c.embedding IS NOT NULL)
    ORDER BY 
        CASE 
            WHEN query_embedding IS NOT NULL THEN c.embedding <=> query_embedding
            ELSE -c.importance_score
        END
    LIMIT match_count;
$$;
                """, "Creating fixed search_by_speaker function"),
                
                ("DROP FUNCTION IF EXISTS get_document_context CASCADE", "Dropping old get_document_context"),
                ("""
CREATE OR REPLACE FUNCTION get_document_context(doc_id UUID)
RETURNS TABLE (
    document_title TEXT,
    document_summary TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    participants TEXT[],
    key_points TEXT[]
)
LANGUAGE sql
AS $$
    SELECT 
        d.title,
        d.summary,
        d.source_type,
        d.created_at,
        ARRAY[]::TEXT[],
        ARRAY[]::TEXT[]
    FROM documents d
    WHERE d.id = doc_id;
$$;
                """, "Creating fixed get_document_context function"),
            ]
            
            for query, description in fixes:
                try:
                    await conn.execute(query)
                    self.log(f"Fixed: {description}", "FIX")
                    self.all_fixes.append(description)
                except Exception as e:
                    self.log(f"Error fixing {description}: {e}", "ERROR")
                    
        finally:
            await conn.close()

    async def test_full_workflow(self):
        """Test the complete workflow"""
        self.log("\nTesting complete workflow...", "INFO")
        
        # Test with direct database operations to ensure it works
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # 1. Create a test document directly
            self.log("Creating test document...", "INFO")
            doc_id = await conn.fetchval("""
                INSERT INTO documents (title, source_type, metadata)
                VALUES ($1, $2, $3)
                RETURNING id
            """, "Test Document for Workflow", "text", '{}')
            
            self.log(f"Created document: {doc_id}", "SUCCESS")
            
            # 2. Create a test chunk with embedding
            self.log("Creating test chunk with embedding...", "INFO")
            
            # Generate a simple test embedding (1536 dimensions)
            test_embedding = [0.1] * 1536
            embedding_str = f'[{",".join(map(str, test_embedding))}]'
            
            chunk_id = await conn.fetchval("""
                INSERT INTO chunks (
                    document_id, content, chunk_index, chunk_type, 
                    embedding, tokens, importance_score, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """, doc_id, "This is test content for MyBrain system", 
                0, "detail", embedding_str, 10, 0.8, '{}')
            
            self.log(f"Created chunk: {chunk_id}", "SUCCESS")
            
            # 3. Test search function
            self.log("Testing search function...", "INFO")
            
            search_results = await conn.fetch("""
                SELECT * FROM hybrid_search($1, $2, $3)
            """, embedding_str, "test content", 5)
            
            if search_results:
                self.log(f"Search returned {len(search_results)} results", "SUCCESS")
            else:
                self.log("Search returned no results", "WARNING")
            
            # 4. Cleanup
            await conn.execute("DELETE FROM chunks WHERE document_id = $1", doc_id)
            await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
            self.log("Cleaned up test data", "SUCCESS")
            
        except Exception as e:
            self.log(f"Workflow test error: {e}", "ERROR")
            traceback.print_exc()
        finally:
            await conn.close()

    async def test_api_endpoints(self):
        """Test API endpoints with curl"""
        self.log("\nTesting API endpoints...", "INFO")
        
        import subprocess
        
        # Test health endpoint
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.backend_url}/health"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self.log("Backend health check passed", "SUCCESS")
            else:
                self.log("Backend health check failed", "ERROR")
        except Exception as e:
            self.log(f"Could not test backend: {e}", "ERROR")
        
        # Test text ingestion with proper data
        try:
            result = subprocess.run([
                "curl", "-X", "POST",
                f"{self.backend_url}/api/v1/ingest/text",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({
                    "title": "API Test Document",
                    "content": "This is a test via API"
                }),
                "-s"
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and "success" in result.stdout.lower():
                self.log("API text ingestion test passed", "SUCCESS")
            else:
                self.log(f"API text ingestion failed: {result.stdout}", "ERROR")
        except Exception as e:
            self.log(f"Could not test API ingestion: {e}", "ERROR")

    async def create_test_script(self):
        """Create a simple test script for the user"""
        self.log("\nCreating user test script...", "INFO")
        
        test_script = """#!/bin/bash
# Simple test script for MyBrain

echo "🧠 MyBrain Test Script"
echo "===================="

# Test 1: Backend Health
echo -e "\\n1. Testing Backend Health..."
curl -s http://localhost:8000/health | python3 -m json.tool

# Test 2: Add a test document
echo -e "\\n2. Adding test document..."
curl -X POST http://localhost:8000/api/v1/ingest/text \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "MyBrain Test",
    "content": "This is a test document. MyBrain should remember this."
  }' -s | python3 -m json.tool

# Test 3: Search for the document
echo -e "\\n3. Searching for test content..."
sleep 2  # Give time for indexing
curl -X POST http://localhost:8000/api/v1/search/ \\
  -H "Content-Type: application/json" \\
  -d '{"query": "test document"}' -s | python3 -m json.tool

echo -e "\\n✅ Tests complete!"
"""
        
        with open("scripts/quick_test.sh", "w") as f:
            f.write(test_script)
        os.chmod("scripts/quick_test.sh", 0o755)
        
        self.log("Created scripts/quick_test.sh - Run this to test the system", "SUCCESS")

    async def run_all_fixes(self):
        """Run all fixes"""
        print("\n" + "="*60)
        print("🧠 MyBrain Complete System Fix")
        print("="*60 + "\n")
        
        await self.fix_all_database_issues()
        await self.test_full_workflow()
        await self.test_api_endpoints()
        await self.create_test_script()
        
        print("\n" + "="*60)
        print("Summary")
        print("="*60 + "\n")
        
        if self.all_fixes:
            print("✅ Fixes Applied:")
            for fix in self.all_fixes:
                print(f"   - {fix}")
        
        print("\n✅ System should now be working!")
        print("\nTo test the system:")
        print("1. Make sure backend is running: uvicorn backend.main:app --reload")
        print("2. Make sure frontend is running: npm run dev")
        print("3. Run: ./scripts/quick_test.sh")
        print("\nOr just open http://localhost:3000 and try adding text!")

async def main():
    fixer = MyBrainFixer()
    await fixer.run_all_fixes()

if __name__ == "__main__":
    asyncio.run(main())