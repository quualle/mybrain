"""
Ingestion API endpoints for MyBrain
Handles YouTube videos, audio files, and text input
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
import asyncpg
import os
from datetime import datetime
import json
import asyncio

# Import services
from services.youtube import YouTubeService
from services.whisper import WhisperService
from core.chunking import smart_chunker
from core.embeddings import embedding_service


router = APIRouter()

# Pydantic models
class YouTubeIngestRequest(BaseModel):
    url: HttpUrl
    language: Optional[str] = "auto"
    generate_summary: bool = True
    
class TextIngestRequest(BaseModel):
    title: str
    content: str
    source_type: str = "text"
    metadata: Optional[Dict] = None
    speaker: Optional[str] = None

class AudioIngestRequest(BaseModel):
    title: str
    language: Optional[str] = "auto"
    speakers: Optional[List[str]] = None


# Initialize services
youtube_service = YouTubeService()
whisper_service = WhisperService()


@router.post("/youtube")
async def ingest_youtube(request: YouTubeIngestRequest, background_tasks: BackgroundTasks):
    """Ingest a YouTube video with transcript"""
    try:
        # Extract video ID and metadata
        video_data = await youtube_service.extract_video_data(str(request.url))
        
        if not video_data['transcript']:
            raise HTTPException(status_code=400, detail="No transcript available for this video")
        
        # Add to background processing
        background_tasks.add_task(
            process_youtube_video,
            video_data,
            request.language,
            request.generate_summary
        )
        
        return {
            "status": "processing",
            "message": f"YouTube video '{video_data['title']}' queued for processing",
            "video_id": video_data['video_id'],
            "duration": video_data['duration']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing YouTube URL: {str(e)}")


@router.post("/audio")
async def ingest_audio(
    file: UploadFile = File(...),
    title: str = None,
    language: str = "auto",
    speakers: Optional[str] = None
):
    """Ingest an audio file and transcribe it"""
    try:
        # Validate file type
        if not file.filename.endswith(('.mp3', '.wav', '.m4a', '.ogg', '.webm')):
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        
        # Read file content
        audio_content = await file.read()
        
        # Transcribe using Whisper
        transcript_data = await whisper_service.transcribe(
            audio_content,
            filename=file.filename,
            language=language
        )
        
        # Process the transcript
        document_id = await process_audio_transcript(
            transcript_data,
            title or file.filename,
            speakers.split(',') if speakers else None
        )
        
        return {
            "status": "success",
            "message": f"Audio file '{file.filename}' processed successfully",
            "document_id": str(document_id),
            "duration": transcript_data.get('duration'),
            "language": transcript_data.get('language')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@router.post("/text")
async def ingest_text(request: TextIngestRequest):
    """Ingest text or markdown content"""
    try:
        # Create document with full content
        document_id = await create_document(
            title=request.title,
            source_type=request.source_type,
            metadata=request.metadata,
            full_content=request.content  # Store complete original
        )
        
        # Chunk the content
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


@router.post("/quick")
async def quick_capture(content: str, source: str = "voice"):
    """Quick capture endpoint for Siri/Alexa"""
    try:
        # Create a quick note
        title = f"Quick note - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        request = TextIngestRequest(
            title=title,
            content=content,
            source_type=source,
            metadata={"quick_capture": True}
        )
        
        return await ingest_text(request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in quick capture: {str(e)}")


# Helper functions
async def create_document(title: str, source_type: str, 
                         source_url: str = None, 
                         duration_seconds: int = None,
                         metadata: Dict = None,
                         full_content: str = None) -> str:
    """Create a document in the database"""
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        document_id = await conn.fetchval(
            """
            INSERT INTO documents (title, source_type, source_url, duration_seconds, metadata, full_content)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            title,
            source_type,
            source_url,
            duration_seconds,
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
        # Generate embeddings for all chunks
        chunk_dicts = [chunk.to_dict() for chunk in chunks]
        embeddings_result = await embedding_service.embed_document_hierarchical(
            "", chunk_dicts
        )
        
        # Prepare batch insert data
        chunk_records = []
        colbert_records = []
        
        for i, chunk in enumerate(chunks):
            # Get embedding for this chunk
            embedding = None
            for emb in embeddings_result['chunk_embeddings']:
                if emb['chunk_id'] == i:
                    embedding = emb['embedding']
                    break
            
            chunk_records.append((
                document_id,
                chunk.content,
                chunk.chunk_index,
                chunk.chunk_type,
                chunk.start_time,
                chunk.end_time,
                chunk.speaker,
                f'[{",".join(map(str, embedding))}]' if embedding else None,  # Convert to vector format
                chunk.tokens,
                chunk.importance_score,
                json.dumps(chunk.metadata) if chunk.metadata else '{}'
            ))
        
        # Insert chunks one by one (batch insert with executemany has issues with UUIDs)
        chunk_ids = []
        for record in chunk_records:
            chunk_id = await conn.fetchval(
                """
                INSERT INTO chunks 
                (document_id, content, chunk_index, chunk_type, start_time, end_time, 
                 speaker, embedding, tokens, importance_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
                """,
                *record
            )
            chunk_ids.append({'id': chunk_id})
        
        # Insert ColBERT embeddings if available
        for colbert_data in embeddings_result.get('colbert_embeddings', []):
            chunk_idx = colbert_data.get('chunk_id')
            if chunk_idx is not None and chunk_idx < len(chunk_ids):
                chunk_id = chunk_ids[chunk_idx]['id']
                await conn.execute(
                    """
                    INSERT INTO colbert_tokens (chunk_id, token_embeddings, token_texts)
                    VALUES ($1, $2, $3)
                    """,
                    chunk_id,
                    json.dumps(colbert_data['token_embeddings']),
                    colbert_data['tokens']
                )
        
    finally:
        await conn.close()


async def process_youtube_video(video_data: Dict, language: str, generate_summary: bool):
    """Background task to process YouTube video"""
    try:
        # Create document with full transcript
        document_id = await create_document(
            title=video_data['title'],
            source_type='youtube',
            source_url=video_data['url'],
            duration_seconds=video_data['duration'],
            metadata={
                'video_id': video_data['video_id'],
                'channel': video_data['channel'],
                'thumbnail': video_data['thumbnail']
            },
            full_content=video_data['transcript']  # Store complete transcript
        )
        
        # Chunk the transcript
        chunks = smart_chunker.chunk_youtube_video(
            video_data['transcript'],
            video_data
        )
        
        # Process chunks
        await process_chunks(document_id, chunks)
        
        # Generate summary if requested
        if generate_summary:
            await generate_document_summary(document_id, video_data['transcript'])
        
        print(f"Successfully processed YouTube video: {video_data['title']}")
        
    except Exception as e:
        print(f"Error processing YouTube video: {e}")


async def process_audio_transcript(transcript_data: Dict, title: str, speakers: List[str]) -> str:
    """Process transcribed audio"""
    # Create document with full transcript
    document_id = await create_document(
        title=title,
        source_type='audio',
        duration_seconds=transcript_data.get('duration'),
        metadata={
            'language': transcript_data.get('language'),
            'speakers': speakers
        },
        full_content=transcript_data['text']  # Store complete transcript
    )
    
    # Process segments if available
    if 'segments' in transcript_data:
        # Convert segments to timestamp format
        timestamps = [
            (seg['start'], seg['text']) 
            for seg in transcript_data['segments']
        ]
    else:
        timestamps = None
    
    # Chunk the transcript
    chunks = smart_chunker.chunk_transcript(
        transcript_data['text'],
        timestamps=timestamps,
        speakers=[(speakers[0], transcript_data['text'])] if speakers else None
    )
    
    # Process chunks
    await process_chunks(document_id, chunks)
    
    return document_id


async def generate_document_summary(document_id: str, full_text: str):
    """Generate and save document summary using LLM with full context"""
    from openai import AsyncOpenAI
    
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # Use GPT-4 to generate comprehensive summary from full text
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """Du bist ein Experte für präzise Zusammenfassungen.
                    Erstelle eine strukturierte Zusammenfassung, die:
                    1. Die Hauptthemen und Kernaussagen erfasst
                    2. Wichtige Personen und ihre Beiträge nennt
                    3. Konkrete Ergebnisse oder Entscheidungen hervorhebt
                    4. Zeitliche Aspekte und nächste Schritte aufführt
                    
                    Format:
                    ## Hauptthemen
                    - Thema 1: Kurze Beschreibung
                    - Thema 2: Kurze Beschreibung
                    
                    ## Kernaussagen
                    - Person X: Wichtigste Aussage
                    - Person Y: Wichtigste Aussage
                    
                    ## Ergebnisse/Entscheidungen
                    - Konkrete Outcomes
                    
                    ## Nächste Schritte (falls erwähnt)
                    - Action Items
                    """
                },
                {
                    "role": "user",
                    "content": f"Erstelle eine strukturierte Zusammenfassung des folgenden Transkripts:\n\n{full_text}"
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        
    except Exception as e:
        print(f"Error generating summary with LLM: {e}")
        # Fallback to simple summary
        summary = f"[Summary generation failed] {full_text[:1000]}..."
    
    # Generate embedding for summary
    summary_embedding = await embedding_service.get_dense_embedding(summary)
    
    # Update document
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    try:
        # Convert embedding to vector format
        embedding_str = f'[{",".join(map(str, summary_embedding))}]'
        
        await conn.execute(
            """
            UPDATE documents 
            SET summary = $1, summary_embedding = $2
            WHERE id = $3
            """,
            summary,
            embedding_str,
            document_id
        )
        
        print(f"Generated comprehensive summary for document {document_id}")
        
    finally:
        await conn.close()