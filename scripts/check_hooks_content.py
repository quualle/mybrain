#!/usr/bin/env python3
"""Check full content about Claude Code Hooks"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def get_hooks_content():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        # Get all chunks about hooks
        chunks = await conn.fetch("""
            SELECT c.content, c.chunk_index, d.title
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.id = 'ad71dcb2-7dfa-4cf5-8ab6-cccb2e3ce0cf'
              AND (LOWER(c.content) LIKE '%hook%' 
                   OR LOWER(c.content) LIKE '%security%'
                   OR LOWER(c.content) LIKE '%permission%'
                   OR LOWER(c.content) LIKE '%observability%'
                   OR LOWER(c.content) LIKE '%audio%feedback%'
                   OR LOWER(c.content) LIKE '%parallel%sub%agent%')
            ORDER BY c.chunk_index
        """)
        
        print(f"=== Found {len(chunks)} relevant chunks about Claude Code Hooks ===\n")
        
        for chunk in chunks:
            print(f"=== Chunk {chunk['chunk_index']} ===")
            print(chunk['content'])
            print("\n" + "="*80 + "\n")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(get_hooks_content())