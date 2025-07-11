"""
Minimal Ingestion API for MyBrain - Text only
Optimized for performance and small footprint
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncpg
import os
from datetime import datetime
import json
import asyncio

# Import services
from core.chunking import smart_chunker
try:
    from core.embeddings import embedding_service
except ImportError:
    from core.embeddings_minimal import embedding_service


router = APIRouter()

# Pydantic models
class TextIngestRequest(BaseModel):
    title: str
    content: str
    source: str = "text"
    source_type: str = "text"
    speaker: Optional[str] = None
    metadata: Optional[Dict] = None


@router.post("/text")
async def ingest_text(request: TextIngestRequest):
    """Ingest text content with optimal chunking and embeddings"""
    try:
        # Create document with full content
        document_id = await create_document(
            title=request.title,
            source_type=request.source_type,
            metadata=request.metadata,
            full_content=request.content  # Store complete original
        )
        
        # Chunk the content intelligently
        chunks = smart_chunker.chunk_transcript(
            request.content,
            speakers=[(request.speaker, request.content)] if request.speaker else None
        )
        
        # Generate embeddings and save
        await process_chunks(document_id, chunks)
        
        # Generate summary if needed
        if len(request.content) > 1000:
            await generate_document_summary(document_id, request.content)
        
        return {
            "status": "success",
            "message": f"Text '{request.title}' ingested successfully",
            "document_id": str(document_id),
            "chunks_created": len(chunks)
        }
        
    except Exception as e:
        import traceback
        print(f"Error in text ingestion: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error ingesting text: {str(e)}")


# Helper functions
async def create_document(title: str, source_type: str, 
                         metadata: Dict = None,
                         full_content: str = None) -> str:
    """Create a document in the database"""
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        document_id = await conn.fetchval(
            """
            INSERT INTO documents (title, source_type, metadata, full_content, created_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            title,
            source_type,
            json.dumps(metadata) if metadata else '{}',
            full_content
        )
        
        return document_id
        
    finally:
        await conn.close()


async def process_chunks(document_id: str, chunks: List):
    """Process chunks: generate embeddings and save to database"""
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
        # Process chunks and ensure they're not too large
        processed_chunks = []
        chunk_texts = []
        
        for chunk in chunks:
            # Check token count
            tokens = len(encoding.encode(chunk.content))
            
            # If chunk is too large, split it
            if tokens > 8000:
                # Split into smaller pieces
                text = chunk.content
                words = text.split()
                current_chunk = []
                current_tokens = 0
                
                for word in words:
                    word_tokens = len(encoding.encode(word))
                    if current_tokens + word_tokens > 7000:  # Leave some buffer
                        # Save current chunk
                        sub_content = ' '.join(current_chunk)
                        processed_chunks.append(chunk)
                        chunk_texts.append(sub_content)
                        current_chunk = [word]
                        current_tokens = word_tokens
                    else:
                        current_chunk.append(word)
                        current_tokens += word_tokens
                
                # Don't forget the last piece
                if current_chunk:
                    sub_content = ' '.join(current_chunk)
                    processed_chunks.append(chunk)
                    chunk_texts.append(sub_content)
            else:
                processed_chunks.append(chunk)
                chunk_texts.append(chunk.content)
        
        # Generate embeddings using minimal service
        embeddings = await embedding_service.encode(chunk_texts)
        
        # Insert chunks
        for i, chunk in enumerate(processed_chunks if processed_chunks else chunks):
            # Format embedding for pgvector
            embedding_vector = None
            if i < len(embeddings):
                # Convert numpy array to pgvector format string: '[x,y,z]'
                embedding_list = embeddings[i].tolist()
                embedding_vector = f'[{",".join(map(str, embedding_list))}]'
            
            await conn.execute(
                """
                INSERT INTO chunks 
                (document_id, content, chunk_index, chunk_type, 
                 embedding, tokens, importance_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                document_id,
                chunk.content,
                chunk.chunk_index,
                chunk.chunk_type,
                embedding_vector,  # Now properly formatted as string
                chunk.tokens,
                chunk.importance_score,
                json.dumps(chunk.metadata) if chunk.metadata else '{}'
            )
            
    finally:
        await conn.close()


async def generate_document_summary(document_id: str, content: str):
    """Generate a summary for long documents"""
    try:
        from openai import AsyncOpenAI
        import tiktoken
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Limit content to safe token count
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(content)
        
        # Keep under 7500 tokens to leave room for system message
        if len(tokens) > 7500:
            content = encoding.decode(tokens[:7500])
        
        # Generate summary
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Create a concise summary of the following text. Focus on key points."},
                {"role": "user", "content": content}
            ],
            max_tokens=500
        )
        
        summary = response.choices[0].message.content
        
        # Update document with summary
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
        try:
            await conn.execute(
                "UPDATE documents SET summary = $1 WHERE id = $2",
                summary, document_id
            )
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Non-critical, continue without summary