"""
Smart query routing for MyBrain
Intelligently routes queries based on their type and intent
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import asyncpg
from datetime import datetime, timedelta


@dataclass
class QueryIntent:
    """Represents the detected intent of a query"""
    query_type: str  # 'document_ref', 'speaker_ref', 'temporal', 'general'
    entities: Dict[str, str]
    confidence: float


class SmartQueryRouter:
    """Routes queries to appropriate search strategies"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        
    async def analyze_query(self, query: str, history: List[Dict] = None) -> QueryIntent:
        """Analyze query to determine intent and extract entities"""
        
        query_lower = query.lower()
        
        # Simplified patterns for better matching
        # Check for video references first
        if 'video' in query_lower:
            # Extract author/channel and topic
            author = None
            topic = None
            
            # Try to find author (von X)
            author_match = re.search(r'von\s+([\w]+)', query_lower)
            if author_match:
                author = author_match.group(1)
            
            # Try to find topic (über/zu X)
            topic_match = re.search(r'(?:über|zu|zum thema)\s+(.+?)(?:\.|$)', query_lower)
            if topic_match:
                topic = topic_match.group(1).strip()
            
            return QueryIntent(
                query_type='document_ref',
                entities={'doc_type': 'video', 'author': author, 'topic': topic},
                confidence=0.9
            )
        
        # Document reference patterns
        doc_patterns = {
            'video': r'video.*?(?:von\s+([\w]+))?.*?(?:über|zu|zum thema)\s+(.+)',
            'artikel': r'artikel.*?(?:von\s+([\w]+))?.*?(?:über|zu)?\s*(.+)',
            'gespräch': r'gespräch.*?(?:mit|von)\s+([\w]+)',
            'transkript': r'transkript.*?(?:von|über)\s+(.+)'
        }
        
        for doc_type, pattern in doc_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                # Safely extract groups
                groups = match.groups()
                entities = {
                    'doc_type': doc_type,
                    'author': groups[0] if len(groups) > 0 and groups[0] else None,
                    'topic': groups[1] if len(groups) > 1 and groups[1] else None
                }
                # Clean up entities
                for k, v in entities.items():
                    if v:
                        entities[k] = v.strip(' .?,')
                
                return QueryIntent(
                    query_type='document_ref',
                    entities=entities,
                    confidence=0.9
                )
        
        # Speaker reference patterns
        if any(phrase in query_lower for phrase in ['hat gesagt', 'meinte', 'erwähnte', 'sagte']):
            # Extract speaker name (usually before "hat gesagt")
            speaker_match = re.search(r'(\w+)\s+(?:hat|meinte|erwähnte|sagte)', query_lower)
            speaker = speaker_match.group(1) if speaker_match else None
            
            return QueryIntent(
                query_type='speaker_ref',
                entities={'speaker': speaker},
                confidence=0.85
            )
        
        # Temporal patterns
        temporal_patterns = {
            'heute': 0,
            'gestern': 1,
            'vorgestern': 2,
            'letzte woche': 7,
            'letzten monat': 30,
            'neulich': 14  # Default to 2 weeks
        }
        
        for pattern, days_ago in temporal_patterns.items():
            if pattern in query_lower:
                return QueryIntent(
                    query_type='temporal',
                    entities={'days_ago': str(days_ago)},
                    confidence=0.8
                )
        
        # Default to general search
        return QueryIntent(
            query_type='general',
            entities={},
            confidence=0.5
        )
    
    async def route_query(self, query: str, history: List[Dict] = None) -> Dict:
        """Route query to appropriate search strategy"""
        
        intent = await self.analyze_query(query, history)
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            if intent.query_type == 'document_ref':
                return await self._document_reference_search(conn, query, intent.entities)
            elif intent.query_type == 'speaker_ref':
                return await self._speaker_reference_search(conn, query, intent.entities)
            elif intent.query_type == 'temporal':
                return await self._temporal_search(conn, query, intent.entities)
            else:
                return {'strategy': 'general', 'intent': intent}
        finally:
            await conn.close()
    
    async def _document_reference_search(self, conn: asyncpg.Connection, 
                                       query: str, entities: Dict) -> Dict:
        """Search for specific documents first, then get all their chunks"""
        
        # Build search conditions
        conditions = []
        params = []
        param_count = 0
        
        if entities.get('author'):
            param_count += 1
            conditions.append(f"LOWER(title) LIKE ${param_count}")
            params.append(f"%{entities['author'].lower()}%")
        
        if entities.get('topic'):
            param_count += 1
            conditions.append(f"LOWER(title) LIKE ${param_count}")
            params.append(f"%{entities['topic'].lower()}%")
        
        if entities.get('doc_type') == 'video':
            param_count += 1
            conditions.append(f"(source_type = 'youtube' OR LOWER(title) LIKE ${param_count})")
            params.append("%video%")
        
        if not conditions:
            return {'strategy': 'document_ref', 'documents': [], 'chunks': []}
        
        # Search documents
        where_clause = " OR ".join(conditions)
        docs = await conn.fetch(f"""
            SELECT id, title, source_type, created_at, full_content
            FROM documents
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 5
        """, *params)
        
        if not docs:
            return {'strategy': 'document_ref', 'documents': [], 'chunks': []}
        
        doc_id = docs[0]['id']
        doc_dict = dict(docs[0])
        
        # Check if query needs full context
        needs_full_context = self._needs_full_context(query)
        
        if needs_full_context and doc_dict.get('full_content'):
            # Return full content as a single chunk for detail questions
            full_chunk = {
                'content': doc_dict['full_content'],
                'chunk_type': 'full_document',
                'chunk_index': 0,
                'document': {
                    'document_title': doc_dict['title'],
                    'document_id': str(doc_id)
                },
                'importance_score': 1.0
            }
            
            return {
                'strategy': 'document_ref',
                'documents': [dict(doc) for doc in docs],
                'chunks': [full_chunk],
                'focused_doc_id': str(doc_id),
                'used_full_content': True
            }
        else:
            # Get ALL chunks from the most relevant document
            chunks = await conn.fetch("""
                SELECT c.*, d.title as document_title
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = $1
                ORDER BY c.chunk_index
            """, doc_id)
            
            # Convert to dict format
            chunk_dicts = []
            for chunk in chunks:
                chunk_dict = dict(chunk)
                chunk_dict['document'] = {
                    'document_title': chunk['document_title'],
                    'document_id': str(doc_id)
                }
                chunk_dicts.append(chunk_dict)
            
            return {
                'strategy': 'document_ref',
                'documents': [dict(doc) for doc in docs],
                'chunks': chunk_dicts,
                'focused_doc_id': str(doc_id),
                'used_full_content': False
            }
    
    async def _speaker_reference_search(self, conn: asyncpg.Connection,
                                      query: str, entities: Dict) -> Dict:
        """Search for chunks where a specific speaker said something"""
        
        speaker = entities.get('speaker', '')
        
        chunks = await conn.fetch("""
            SELECT c.*, d.title as document_title
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE LOWER(c.speaker) LIKE $1
               OR LOWER(c.content) LIKE $2
            ORDER BY c.created_at DESC
            LIMIT 20
        """, f"%{speaker.lower()}%", f"%{speaker}%")
        
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = dict(chunk)
            chunk_dict['document'] = {'document_title': chunk['document_title']}
            chunk_dicts.append(chunk_dict)
        
        return {
            'strategy': 'speaker_ref',
            'speaker': speaker,
            'chunks': chunk_dicts
        }
    
    async def _temporal_search(self, conn: asyncpg.Connection,
                             query: str, entities: Dict) -> Dict:
        """Search based on time references"""
        
        days_ago = int(entities.get('days_ago', 7))
        since_date = datetime.now() - timedelta(days=days_ago)
        
        chunks = await conn.fetch("""
            SELECT c.*, d.title as document_title
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.created_at >= $1
            ORDER BY d.created_at DESC
        """, since_date)
        
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = dict(chunk)
            chunk_dict['document'] = {'document_title': chunk['document_title']}
            chunk_dicts.append(chunk_dict)
        
        return {
            'strategy': 'temporal',
            'since_date': since_date.isoformat(),
            'chunks': chunk_dicts
        }
    
    def _needs_full_context(self, query: str) -> bool:
        """Check if query requires full document context"""
        query_lower = query.lower()
        
        # Indicators that full context is needed
        full_context_indicators = [
            'gesamt', 'vollständig', 'komplett', 'alles', 
            'detail', 'genau', 'exakt', 'wörtlich',
            'komplette transkript', 'ganze gespräch',
            'was wurde alles', 'alle themen',
            'zusammenfassung des gesamten'
        ]
        
        # Check for indicators
        for indicator in full_context_indicators:
            if indicator in query_lower:
                return True
        
        # Check for "dieses/diesem Gespräch/Transkript" pattern
        if re.search(r'(dieses|diesem|diese)\s+(gespräch|transkript|video|interview)', query_lower):
            if any(word in query_lower for word in ['alles', 'gesamt', 'komplett', 'detail']):
                return True
        
        return False