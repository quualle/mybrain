import asyncio
import asyncpg
import os
import re
from dotenv import load_dotenv

load_dotenv()

async def simple_search():
    # Erstelle neue Verbindung mit statement_cache_size=0
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        # Suche nach dem Netflix CEO Video
        print("Searching for Netflix CEO video chunks...")
        results = await conn.fetch("""
            SELECT content
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.title ILIKE '%Netflix CEO%'
            AND c.content ILIKE '%maybe we could%'
            LIMIT 20
        """)
        
        if results:
            print(f"Found {len(results)} chunks")
            
            # Durchsuche jeden Chunk nach dem Pattern
            pattern = r'maybe we could use this\s+(\w+)\s+thing'
            
            for i, r in enumerate(results):
                content = r['content']
                match = re.search(pattern, content, re.IGNORECASE)
                
                if match:
                    print(f"\n✅ GEFUNDEN! Das fehlende Wort ist: '{match.group(1).upper()}'")
                    
                    # Zeige den Kontext
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 200)
                    context = content[start:end]
                    
                    # Highlight das gefundene Wort
                    highlighted = context.replace(match.group(0), f">>> {match.group(0)} <<<")
                    print(f"\nKontext:\n{highlighted}")
                    
                    return match.group(1)
        
        print("\n❌ Kein exakter Treffer gefunden")
        
        # Zeige was in der DB ist
        print("\nZeige Netflix-bezogene Chunks:")
        netflix_chunks = await conn.fetch("""
            SELECT SUBSTRING(content, 1, 200) as snippet
            FROM chunks
            WHERE content ILIKE '%Netflix%'
            LIMIT 5
        """)
        
        for chunk in netflix_chunks:
            print(f"\n{chunk['snippet']}...")
            
    finally:
        await conn.close()

asyncio.run(simple_search())