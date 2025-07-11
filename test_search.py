import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def search_for_text():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        # Suche nach dem spezifischen Text
        results = await conn.fetch("""
            SELECT 
                c.content, 
                c.document_id,
                d.title,
                d.source_type
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE 
                c.content ILIKE '%Netflix%' 
                AND c.content ILIKE '%hindsight%' 
                AND c.content ILIKE '%wonderful thing%'
            LIMIT 5
        """)
        
        if results:
            print(f"Found {len(results)} matching chunks:\n")
            for r in results:
                print(f"Document: {r['title']} ({r['source_type']})")
                print(f"Content: {r['content'][:500]}...")
                print("-" * 80)
        else:
            print("No matching text found in database")
            
        # Suche nach dem exakten Textmuster
        print("\nSearching for exact pattern...")
        exact = await conn.fetch("""
            SELECT 
                c.content,
                d.title,
                c.chunk_index
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE 
                c.content ILIKE '%aybe we could use this%' 
                AND c.content ILIKE '%thing for Netflix%'
                AND c.content ILIKE '%hindsight%'
            ORDER BY c.chunk_index
            LIMIT 5
        """)
        
        if exact:
            print(f"\nFound exact match!")
            for e in exact:
                print(f"\nDocument: {e['title']}")
                print(f"Chunk index: {e['chunk_index']}")
                # Find the exact phrase
                content = e['content']
                start = content.lower().find('aybe we could use this')
                if start != -1:
                    print(f"Context: ...{content[max(0, start-50):min(len(content), start+300)]}...")
                else:
                    print(f"Full content: {content}")
                    
        # Auch nach dem vollständigen Dokument suchen
        print("\nSearching for full document content...")
        full_doc = await conn.fetch("""
            SELECT 
                d.full_content,
                d.title
            FROM documents d
            WHERE 
                d.title ILIKE '%Netflix CEO%'
            LIMIT 1
        """)
        
        if partial:
            print(f"\nFound {len(partial)} partial matches:")
            for p in partial:
                print(f"\nDocument: {p['title']}")
                print(f"Content: {p['content'][:300]}...")
                
    finally:
        await conn.close()

asyncio.run(search_for_text())