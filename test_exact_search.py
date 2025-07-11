import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def find_missing_word():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        # Der Text aus dem Test
        test_phrase = "aybe we could use this {...…} thing for Netflix"
        
        # Suche nach dem exakten Textmuster
        print("Searching for the exact pattern in chunks...")
        results = await conn.fetch("""
            SELECT 
                c.content,
                d.title,
                c.chunk_index,
                c.document_id
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE 
                c.content ILIKE '%maybe we could use this%thing for Netflix%'
            ORDER BY c.chunk_index
            LIMIT 10
        """)
        
        if results:
            print(f"\nFound {len(results)} matching chunks!")
            for r in results:
                content = r['content']
                # Suche die exakte Stelle
                import re
                pattern = r'maybe we could use this\s+(\w+)\s+thing for Netflix'
                match = re.search(pattern, content, re.IGNORECASE)
                
                if match:
                    missing_word = match.group(1)
                    print(f"\n✅ FOUND THE MISSING WORD: '{missing_word}'")
                    print(f"Document: {r['title']}")
                    print(f"Context: ...{match.group(0)}...")
                    
                    # Zeige mehr Kontext
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    print(f"\nFull context:\n{content[start:end]}")
        else:
            print("❌ No exact match found in chunks")
            
        # Versuche es mit dem full_content
        print("\n\nSearching in full document content...")
        full_results = await conn.fetch("""
            SELECT 
                d.full_content,
                d.title
            FROM documents d
            WHERE 
                d.full_content ILIKE '%maybe we could use this%thing for Netflix%'
                OR d.title ILIKE '%Netflix CEO%'
            LIMIT 3
        """)
        
        if full_results:
            print(f"\nFound {len(full_results)} documents")
            for doc in full_results:
                if doc['full_content']:
                    content = doc['full_content']
                    pattern = r'maybe we could use this\s+(\w+)\s+thing for Netflix'
                    match = re.search(pattern, content, re.IGNORECASE)
                    
                    if match:
                        missing_word = match.group(1)
                        print(f"\n✅ FOUND IN FULL CONTENT: '{missing_word}'")
                        print(f"Document: {doc['title']}")
                        
                        # Zeige Kontext
                        start = max(0, match.start() - 200)
                        end = min(len(content), match.end() + 200)
                        print(f"\nContext:\n{content[start:end]}")
                    else:
                        # Suche nach ähnlichem Text
                        if 'Netflix' in content and 'hindsight' in content:
                            print(f"\nDocument '{doc['title']}' contains Netflix and hindsight")
                            # Finde alle Vorkommen von "Netflix"
                            netflix_pos = content.lower().find('netflix')
                            if netflix_pos != -1:
                                print(f"Netflix context: ...{content[max(0, netflix_pos-200):min(len(content), netflix_pos+200)]}...")
                
    finally:
        await conn.close()

asyncio.run(find_missing_word())