#!/usr/bin/env python3
"""
Analyze database content to understand what queries should work
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

async def analyze_database():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        print("=== MyBrain Database Content Analysis ===\n")
        
        # 1. Document Overview
        docs = await conn.fetch("""
            SELECT id, title, source_type, created_at, summary
            FROM documents
            ORDER BY created_at DESC
        """)
        
        print(f"📚 Total Documents: {len(docs)}\n")
        print("Documents by Type:")
        doc_types = defaultdict(int)
        for doc in docs:
            doc_types[doc['source_type']] += 1
        for dtype, count in doc_types.items():
            print(f"  - {dtype}: {count}")
        
        print("\n📄 All Documents:")
        for i, doc in enumerate(docs):
            print(f"\n{i+1}. {doc['title']}")
            print(f"   Type: {doc['source_type']}")
            print(f"   ID: {doc['id']}")
            if doc['summary']:
                print(f"   Summary: {doc['summary'][:100]}...")
        
        # 2. Speaker Analysis
        print("\n\n👥 Speakers Found:")
        speakers = await conn.fetch("""
            SELECT DISTINCT speaker, COUNT(*) as chunk_count
            FROM chunks
            WHERE speaker IS NOT NULL
            GROUP BY speaker
            ORDER BY chunk_count DESC
        """)
        
        for speaker in speakers:
            print(f"  - {speaker['speaker']}: {speaker['chunk_count']} chunks")
        
        # 3. Key Terms Analysis
        print("\n\n🔤 Key Terms in Content:")
        
        # Search for specific terms
        terms_to_check = [
            'Claude Code', 'Hooks', 'MCP', 'Careli', 'Sascha', 'Antonio',
            'Anwaltskanzlei', 'Pflegekräfte', 'Polen', 'Synclaro', 'IndyDevDan',
            'Cole Medlin'
        ]
        
        for term in terms_to_check:
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM chunks
                WHERE LOWER(content) LIKE $1
            """, f"%{term.lower()}%")
            
            if count > 0:
                # Find which documents contain this term
                doc_titles = await conn.fetch("""
                    SELECT DISTINCT d.title
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE LOWER(c.content) LIKE $1
                """, f"%{term.lower()}%")
                
                print(f"\n  '{term}': {count} chunks")
                for dt in doc_titles:
                    print(f"    - In: {dt['title']}")
        
        # 4. Sample Chunks
        print("\n\n📝 Sample Content from Each Document:")
        for doc in docs[:5]:  # First 5 documents
            chunks = await conn.fetch("""
                SELECT content, chunk_index
                FROM chunks
                WHERE document_id = $1
                ORDER BY chunk_index
                LIMIT 2
            """, doc['id'])
            
            if chunks:
                print(f"\n--- {doc['title']} ---")
                for chunk in chunks:
                    print(f"Chunk {chunk['chunk_index']}: {chunk['content'][:200]}...")
        
        # 5. Potential Query Tests
        print("\n\n🧪 Suggested Test Queries Based on Content:")
        
        test_queries = []
        
        # Based on document titles
        for doc in docs:
            if 'claude code hooks' in doc['title'].lower():
                test_queries.append(f"Was ist der Mehrwert von Claude Code Hooks?")
            elif 'mcp' in doc['title'].lower():
                test_queries.append(f"Erkläre mir MCP Server")
            
        # Based on speakers
        for speaker in speakers:
            if speaker['speaker']:
                test_queries.append(f"Was hat {speaker['speaker']} gesagt?")
        
        # Based on key terms
        if any('careli' in doc['title'].lower() for doc in docs):
            test_queries.append("Erzähl mir über die Firma Careli")
        
        print("\nBased on the database content, these queries should work:")
        for i, query in enumerate(test_queries[:10], 1):
            print(f"{i}. {query}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_database())