#!/usr/bin/env python3
"""Check for IndyDevDan video content in database"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def search_for_video():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        # Search in documents
        print("=== Searching for IndyDevDan content ===\n")
        
        docs = await conn.fetch("""
            SELECT id, title, source_type, created_at 
            FROM documents 
            WHERE LOWER(title) LIKE '%indy%' 
               OR LOWER(title) LIKE '%claude%hook%'
               OR LOWER(title) LIKE '%code%hook%'
            ORDER BY created_at DESC
        """)
        
        print(f"Found {len(docs)} documents:\n")
        for doc in docs:
            print(f"Title: {doc['title']}")
            print(f"Type: {doc['source_type']}")
            print(f"ID: {doc['id']}")
            print(f"Created: {doc['created_at']}")
            print("-" * 50)
        
        # If we found documents, check their chunks
        if docs:
            doc_id = docs[0]['id']
            print(f"\n=== Checking chunks for document {doc_id} ===\n")
            
            chunks = await conn.fetch("""
                SELECT content, chunk_index 
                FROM chunks 
                WHERE document_id = $1 
                  AND (LOWER(content) LIKE '%hook%' 
                       OR LOWER(content) LIKE '%indy%'
                       OR chunk_index < 3)
                ORDER BY chunk_index
                LIMIT 5
            """, doc_id)
            
            for chunk in chunks:
                print(f"Chunk {chunk['chunk_index']}:")
                print(chunk['content'][:500] + "...\n")
                
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(search_for_video())