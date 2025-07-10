"""
Search API endpoints for MyBrain
Handles hybrid search, speaker search, and date-based queries
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import os

from ..core.retrieval import HybridRetriever


router = APIRouter()

# Initialize retriever
retriever = HybridRetriever(os.getenv("DATABASE_URL"))


# Pydantic models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 20
    use_colbert_rerank: bool = True
    filters: Optional[Dict] = None

class SearchResponse(BaseModel):
    results: List[Dict]
    query: str
    total_results: int
    search_time_ms: float


@router.get("/")
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    speaker: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source_type: Optional[str] = None,
    use_colbert: bool = True
):
    """
    Perform hybrid search across all documents
    
    Parameters:
    - q: Search query
    - limit: Maximum number of results
    - speaker: Filter by speaker name
    - start_date: Filter by start date
    - end_date: Filter by end date
    - source_type: Filter by source type (youtube, audio, text)
    - use_colbert: Whether to use ColBERT re-ranking
    """
    start_time = datetime.now()
    
    try:
        # Build filters
        filters = {}
        if source_type:
            filters['source_type'] = source_type
        
        # Perform search
        results = await retriever.search(
            query=q,
            top_k=limit,
            use_colbert_rerank=use_colbert,
            filters=filters if filters else None
        )
        
        # Apply additional filters if needed
        if speaker:
            results = [r for r in results if r.get('speaker', '').lower() == speaker.lower()]
        
        if start_date or end_date:
            results = await filter_by_date_range(results, start_date, end_date)
        
        # Calculate search time
        search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=results,
            query=q,
            total_results=len(results),
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/speaker/{speaker_name}")
async def search_by_speaker(
    speaker_name: str,
    q: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Search for content by a specific speaker"""
    try:
        results = await retriever.search_by_speaker(
            speaker_name=speaker_name,
            query=q,
            top_k=limit
        )
        
        return {
            "speaker": speaker_name,
            "query": q,
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speaker search error: {str(e)}")


@router.get("/date-range")
async def search_by_date(
    start_date: datetime,
    end_date: datetime,
    q: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Search within a specific date range"""
    try:
        results = await retriever.search_by_date_range(
            start_date=start_date,
            end_date=end_date,
            query=q,
            top_k=limit
        )
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "query": q,
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Date range search error: {str(e)}")


@router.get("/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """Find documents similar to a given document"""
    try:
        results = await retriever.get_similar_documents(
            document_id=document_id,
            top_k=limit
        )
        
        return {
            "source_document_id": document_id,
            "similar_documents": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search error: {str(e)}")


@router.get("/quick/{query}")
async def quick_search(query: str):
    """
    Quick search endpoint optimized for voice assistants
    Returns concise results suitable for audio playback
    """
    try:
        # Perform search with limited results
        results = await retriever.search(
            query=query,
            top_k=3,
            use_colbert_rerank=False  # Skip for speed
        )
        
        if not results:
            return {
                "query": query,
                "answer": "Ich habe keine relevanten Informationen zu Ihrer Anfrage gefunden.",
                "sources": []
            }
        
        # Format for voice response
        top_result = results[0]
        answer = format_for_voice(top_result['content'])
        
        return {
            "query": query,
            "answer": answer,
            "confidence": top_result.get('similarity', 0),
            "source": {
                "title": top_result.get('document', {}).get('document_title'),
                "type": top_result.get('document', {}).get('source_type'),
                "date": top_result.get('document', {}).get('created_at')
            },
            "additional_results": len(results) - 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search error: {str(e)}")


@router.get("/today")
async def search_today(q: Optional[str] = None):
    """Search for content from today"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now()
    
    return await search_by_date(
        start_date=today_start,
        end_date=today_end,
        q=q
    )


@router.get("/recent")
async def search_recent(
    days: int = Query(7, ge=1, le=30),
    q: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Search recent content from the last N days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = await retriever.search_by_date_range(
        start_date=start_date,
        end_date=end_date,
        query=q,
        top_k=limit
    )
    
    return {
        "period": f"Last {days} days",
        "query": q,
        "results": results,
        "total_results": len(results)
    }


# Helper functions
async def filter_by_date_range(results: List[Dict], 
                             start_date: Optional[datetime],
                             end_date: Optional[datetime]) -> List[Dict]:
    """Filter results by date range"""
    filtered = []
    
    for result in results:
        doc_date = result.get('document', {}).get('created_at')
        if doc_date:
            doc_datetime = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
            
            if start_date and doc_datetime < start_date:
                continue
            if end_date and doc_datetime > end_date:
                continue
                
            filtered.append(result)
    
    return filtered


def format_for_voice(text: str, max_length: int = 200) -> str:
    """Format text for voice output"""
    # Remove special characters and URLs
    import re
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'[*_#`]', '', text)
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()