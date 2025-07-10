"""
Fuzzy Search and Entity Matching for MyBrain
Improves search by finding similar terms and concepts
"""

from typing import List, Dict, Optional, Tuple
import asyncpg
from difflib import SequenceMatcher
import re
from dataclasses import dataclass


@dataclass
class EntityMatch:
    """Represents a matched entity with confidence"""
    original: str
    matched: str
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'semantic', 'alias'


class FuzzySearchEngine:
    """Handles fuzzy matching and semantic search improvements"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        # Common aliases and related terms
        self.domain_knowledge = {
            'pflegekräfte': ['betreuungskräfte', 'pfleger', 'betreuer', 'caregiver'],
            'polen': ['polnisch', 'poland', 'osteuropäisch'],
            'vermittlung': ['vermitteln', 'agentur', 'service', 'placement'],
            'claude code': ['claude-code', 'claudecode', 'anthropic code'],
            'hooks': ['hook', 'webhook', 'callback', 'integration'],
            'mcp': ['model context protocol', 'mcp server', 'mcp-server'],
            'video': ['youtube', 'tutorial', 'recording', 'screencast'],
            'gespräch': ['interview', 'unterhaltung', 'meeting', 'call'],
        }
        
    async def fuzzy_search_documents(self, query: str, threshold: float = 0.6) -> List[Dict]:
        """Search documents with fuzzy matching"""
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            # Extract key terms from query
            key_terms = self._extract_search_terms(query)
            expanded_terms = self._expand_terms(key_terms)
            
            # Build search conditions
            conditions = []
            params = []
            param_count = 0
            
            for term in expanded_terms:
                param_count += 1
                conditions.append(f"""
                    (LOWER(d.title) LIKE ${param_count} OR 
                     LOWER(d.summary) LIKE ${param_count} OR
                     EXISTS (
                         SELECT 1 FROM chunks c 
                         WHERE c.document_id = d.id 
                         AND LOWER(c.content) LIKE ${param_count}
                         LIMIT 1
                     ))
                """)
                params.append(f"%{term.lower()}%")
            
            if not conditions:
                return []
            
            # Search with expanded terms
            where_clause = " OR ".join(conditions)
            docs = await conn.fetch(f"""
                SELECT DISTINCT
                    d.id, 
                    d.title, 
                    d.source_type,
                    d.created_at,
                    d.summary
                FROM documents d
                WHERE {where_clause}
                ORDER BY d.created_at DESC
                LIMIT 10
            """, *params)
            
            # Score results by relevance
            scored_docs = []
            for doc in docs:
                score = self._calculate_relevance_score(
                    query, 
                    doc['title'] or '', 
                    doc['summary'] or ''
                )
                if score >= threshold:
                    doc_dict = dict(doc)
                    doc_dict['relevance_score'] = score
                    scored_docs.append(doc_dict)
            
            # Sort by relevance
            scored_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_docs
            
        finally:
            await conn.close()
    
    async def find_similar_entities(self, entity: str, search_in: str = 'all') -> List[EntityMatch]:
        """Find similar entities in the database"""
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            matches = []
            
            # Search in document titles
            if search_in in ['all', 'documents']:
                docs = await conn.fetch("""
                    SELECT DISTINCT title 
                    FROM documents 
                    WHERE title IS NOT NULL
                """)
                
                for doc in docs:
                    title = doc['title']
                    similarity = self._calculate_similarity(entity, title)
                    if similarity > 0.5:
                        matches.append(EntityMatch(
                            original=entity,
                            matched=title,
                            confidence=similarity,
                            match_type='fuzzy'
                        ))
            
            # Search in speaker names
            if search_in in ['all', 'speakers']:
                speakers = await conn.fetch("""
                    SELECT DISTINCT speaker 
                    FROM chunks 
                    WHERE speaker IS NOT NULL
                """)
                
                for record in speakers:
                    speaker = record['speaker']
                    similarity = self._calculate_similarity(entity, speaker)
                    if similarity > 0.6:
                        matches.append(EntityMatch(
                            original=entity,
                            matched=speaker,
                            confidence=similarity,
                            match_type='fuzzy'
                        ))
            
            # Check domain knowledge
            entity_lower = entity.lower()
            for key, aliases in self.domain_knowledge.items():
                if entity_lower == key or entity_lower in aliases:
                    matches.append(EntityMatch(
                        original=entity,
                        matched=key,
                        confidence=1.0,
                        match_type='alias'
                    ))
                elif any(alias in entity_lower or entity_lower in alias for alias in aliases):
                    matches.append(EntityMatch(
                        original=entity,
                        matched=key,
                        confidence=0.8,
                        match_type='semantic'
                    ))
            
            # Sort by confidence
            matches.sort(key=lambda x: x.confidence, reverse=True)
            return matches[:5]  # Top 5 matches
            
        finally:
            await conn.close()
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from query"""
        # Remove common words
        stopwords = {'das', 'der', 'die', 'ein', 'eine', 'gibt', 'es', 'doch', 
                    'was', 'war', 'nochmal', 'mal', 'mit', 'über', 'zu', 'von'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', query.lower())
        terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Also extract phrases in quotes
        quoted = re.findall(r'["\'](.*?)["\']', query)
        terms.extend(quoted)
        
        # Extract capitalized words (likely entities)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        terms.extend([e.lower() for e in entities])
        
        return list(set(terms))
    
    def _expand_terms(self, terms: List[str]) -> List[str]:
        """Expand terms with aliases and related words"""
        expanded = set(terms)
        
        for term in terms:
            term_lower = term.lower()
            
            # Add from domain knowledge
            if term_lower in self.domain_knowledge:
                expanded.update(self.domain_knowledge[term_lower])
            
            # Check if term is an alias
            for key, aliases in self.domain_knowledge.items():
                if term_lower in aliases:
                    expanded.add(key)
                    expanded.update(aliases)
        
        return list(expanded)
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        # Exact match
        if str1_lower == str2_lower:
            return 1.0
        
        # Substring match
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8
        
        # Token overlap
        tokens1 = set(re.findall(r'\b\w+\b', str1_lower))
        tokens2 = set(re.findall(r'\b\w+\b', str2_lower))
        
        if tokens1 and tokens2:
            overlap = len(tokens1 & tokens2)
            total = len(tokens1 | tokens2)
            token_similarity = overlap / total if total > 0 else 0
            
            if token_similarity > 0.5:
                return token_similarity
        
        # Character-level similarity
        return SequenceMatcher(None, str1_lower, str2_lower).ratio()
    
    def _calculate_relevance_score(self, query: str, title: str, summary: str) -> float:
        """Calculate relevance score for a document"""
        query_lower = query.lower()
        title_lower = title.lower()
        summary_lower = summary.lower()
        
        score = 0.0
        
        # Title match is most important
        title_similarity = self._calculate_similarity(query, title)
        score += title_similarity * 0.6
        
        # Check query terms in title
        query_terms = self._extract_search_terms(query)
        for term in query_terms:
            if term in title_lower:
                score += 0.1
        
        # Summary match
        if summary:
            summary_similarity = self._calculate_similarity(query, summary[:200])
            score += summary_similarity * 0.3
        
        return min(score, 1.0)