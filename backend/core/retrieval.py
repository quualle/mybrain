"""
Hybrid retrieval system for MyBrain
Combines BM25, dense embeddings, and ColBERT re-ranking
"""

import asyncio
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import asyncpg
try:
    from core.embeddings import embedding_service
except ImportError:
    from core.embeddings_minimal import embedding_service


class HybridRetriever:
    """Multi-stage retrieval system"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.embedding_service = embedding_service
        
    async def search(self,
                    query: str,
                    top_k: int = 20,
                    use_colbert_rerank: bool = True,
                    filters: Optional[Dict] = None) -> List[Dict]:
        """
        Perform hybrid search with optional ColBERT re-ranking
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_colbert_rerank: Whether to use ColBERT for re-ranking
            filters: Optional filters (speaker, date range, etc.)
        """
        # Get query embedding
        query_embedding = await self.embedding_service.get_dense_embedding(query)
        
        # Connect to database
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # Stage 1: Hybrid search (BM25 + Dense)
            initial_results = await self._hybrid_search(
                conn, query, query_embedding, top_k * 2, filters
            )
            
            if not initial_results:
                return []
            
            # Stage 2: ColBERT re-ranking (if enabled and available)
            if use_colbert_rerank and len(initial_results) > 5:
                results = await self._colbert_rerank(query, initial_results, top_k)
            else:
                results = initial_results[:top_k]
            
            # Stage 3: Enrich with context
            results = await self._enrich_results(conn, results)
            
            return results
            
        finally:
            await conn.close()
    
    async def search_by_speaker(self,
                               speaker_name: str,
                               query: Optional[str] = None,
                               top_k: int = 20) -> List[Dict]:
        """Search for content by a specific speaker"""
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # Get query embedding if query provided
            query_embedding = None
            if query:
                query_embedding = await self.embedding_service.get_dense_embedding(query)
            
            # Use specialized speaker search function
            embedding_str = f'[{",".join(map(str, query_embedding))}]' if query_embedding else None
            results = await conn.fetch(
                """
                SELECT * FROM search_by_speaker($1, $2, $3)
                """,
                speaker_name,
                embedding_str,
                top_k
            )
            
            # Convert to dict and enrich
            results = [dict(r) for r in results]
            results = await self._enrich_results(conn, results)
            
            return results
            
        finally:
            await conn.close()
    
    async def search_by_date_range(self,
                                  start_date: datetime,
                                  end_date: datetime,
                                  query: Optional[str] = None,
                                  top_k: int = 20) -> List[Dict]:
        """Search for content within a date range"""
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # Get query embedding if query provided
            query_embedding = None
            if query:
                query_embedding = await self.embedding_service.get_dense_embedding(query)
            
            # Search by time range
            embedding_str = f'[{",".join(map(str, query_embedding))}]' if query_embedding else None
            results = await conn.fetch(
                """
                SELECT * FROM search_by_timerange($1, $2, $3, $4)
                """,
                start_date,
                end_date,
                embedding_str,
                top_k
            )
            
            # Convert and enrich
            results = [dict(r) for r in results]
            
            # If we have document-level results, get their chunks
            if results and 'document_id' in results[0]:
                chunk_results = []
                for doc in results:
                    chunks = await self._get_document_chunks(
                        conn, doc['document_id'], query_embedding, 5
                    )
                    chunk_results.extend(chunks)
                results = chunk_results
            
            return results
            
        finally:
            await conn.close()
    
    async def _hybrid_search(self,
                           conn: asyncpg.Connection,
                           query: str,
                           query_embedding: List[float],
                           top_k: int,
                           filters: Optional[Dict]) -> List[Dict]:
        """Perform hybrid search using database function"""
        # Convert filters to JSONB if provided
        filter_jsonb = None
        if filters:
            import json
            filter_jsonb = json.dumps(filters)
        
        # Convert embedding to vector format
        embedding_str = f'[{",".join(map(str, query_embedding))}]'
        
        # Call hybrid search function
        results = await conn.fetch(
            """
            SELECT * FROM hybrid_search($1, $2, $3, $4)
            """,
            embedding_str,
            query,
            top_k,
            filter_jsonb
        )
        
        # Convert to dictionaries
        return [dict(r) for r in results]
    
    async def _colbert_rerank(self,
                            query: str,
                            initial_results: List[Dict],
                            top_k: int) -> List[Dict]:
        """Re-rank results using ColBERT token-level matching"""
        # Initialize ColBERT if needed
        await self.embedding_service.initialize_colbert()
        
        # Get query token embeddings
        query_tokens, query_token_texts = self.embedding_service.get_colbert_embeddings(query)
        query_tokens = np.array(query_tokens)
        
        # Score each result
        scored_results = []
        
        for result in initial_results:
            # Check if we have ColBERT embeddings for this chunk
            if 'colbert_tokens' in result and result['colbert_tokens']:
                # Calculate MaxSim score
                doc_tokens = np.array(result['colbert_tokens']['token_embeddings'])
                
                # Compute similarity matrix
                sim_matrix = np.dot(query_tokens, doc_tokens.T)
                
                # MaxSim: max similarity for each query token
                max_sims = np.max(sim_matrix, axis=1)
                colbert_score = np.mean(max_sims)
                
                # Combine with original score
                combined_score = 0.6 * result['rank'] + 0.4 * colbert_score
            else:
                # No ColBERT embeddings, use original score
                combined_score = result['rank']
            
            result['colbert_score'] = combined_score
            scored_results.append(result)
        
        # Sort by combined score
        scored_results.sort(key=lambda x: x['colbert_score'], reverse=True)
        
        return scored_results[:top_k]
    
    async def _enrich_results(self,
                            conn: asyncpg.Connection,
                            results: List[Dict]) -> List[Dict]:
        """Enrich results with document context and metadata"""
        enriched = []
        
        for result in results:
            # Get document context
            doc_id = result.get('document_id')
            if doc_id:
                doc_context = await conn.fetchrow(
                    """
                    SELECT * FROM get_document_context($1)
                    """,
                    doc_id
                )
                
                if doc_context:
                    result['document'] = dict(doc_context)
            
            # Add surrounding chunks if detail chunk
            if result.get('chunk_index'):
                # Get previous and next chunks for context
                surrounding = await conn.fetch(
                    """
                    SELECT id, content, chunk_index, speaker
                    FROM chunks
                    WHERE document_id = $1 
                    AND chunk_index IN ($2, $3)
                    AND chunk_type = 'detail'
                    ORDER BY chunk_index
                    """,
                    doc_id,
                    result['chunk_index'] - 1,
                    result['chunk_index'] + 1
                )
                
                result['context'] = {
                    'previous': dict(surrounding[0]) if len(surrounding) > 0 else None,
                    'next': dict(surrounding[1]) if len(surrounding) > 1 else None
                }
            
            enriched.append(result)
        
        return enriched
    
    async def _get_document_chunks(self,
                                 conn: asyncpg.Connection,
                                 document_id: str,
                                 query_embedding: Optional[List[float]],
                                 limit: int) -> List[Dict]:
        """Get relevant chunks from a document"""
        if query_embedding:
            # Get chunks sorted by relevance
            chunks = await conn.fetch(
                """
                SELECT 
                    id as chunk_id,
                    document_id,
                    content,
                    chunk_index,
                    1 - (embedding <=> $2) as similarity,
                    metadata
                FROM chunks
                WHERE document_id = $1
                AND chunk_type = 'detail'
                ORDER BY embedding <=> $2
                LIMIT $3
                """,
                document_id,
                query_embedding,
                limit
            )
        else:
            # Get chunks by importance
            chunks = await conn.fetch(
                """
                SELECT 
                    id as chunk_id,
                    document_id,
                    content,
                    chunk_index,
                    importance_score as similarity,
                    metadata
                FROM chunks
                WHERE document_id = $1
                AND chunk_type = 'detail'
                ORDER BY importance_score DESC, chunk_index
                LIMIT $2
                """,
                document_id,
                limit
            )
        
        return [dict(chunk) for chunk in chunks]
    
    async def get_similar_documents(self,
                                   document_id: str,
                                   top_k: int = 5) -> List[Dict]:
        """Find similar documents based on summary embeddings"""
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        
        try:
            # Get document's summary embedding
            doc_embedding = await conn.fetchval(
                """
                SELECT summary_embedding
                FROM documents
                WHERE id = $1
                """,
                document_id
            )
            
            if not doc_embedding:
                return []
            
            # Find similar documents
            similar = await conn.fetch(
                """
                SELECT 
                    id,
                    title,
                    source_type,
                    created_at,
                    1 - (summary_embedding <=> $1) as similarity
                FROM documents
                WHERE id != $2
                AND summary_embedding IS NOT NULL
                ORDER BY summary_embedding <=> $1
                LIMIT $3
                """,
                doc_embedding,
                document_id,
                top_k
            )
            
            return [dict(doc) for doc in similar]
            
        finally:
            await conn.close()