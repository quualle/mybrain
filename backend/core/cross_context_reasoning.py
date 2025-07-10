"""
Cross-Context Reasoning Engine for MyBrain
Enables understanding relationships between different documents and contexts
"""

from typing import List, Dict, Optional, Tuple, Set
import asyncpg
import asyncio
from dataclasses import dataclass
from datetime import datetime
import re
import json


@dataclass
class DocumentRelationship:
    """Represents a relationship between documents"""
    doc1_id: str
    doc1_title: str
    doc2_id: str  
    doc2_title: str
    relationship_type: str  # 'people', 'topic', 'temporal', 'solution_match'
    confidence: float
    evidence: List[str]


@dataclass 
class CrossContextInsight:
    """Represents an insight across multiple contexts"""
    query: str
    primary_context: Dict
    related_contexts: List[Dict]
    insights: List[str]
    confidence: float


class CrossContextReasoner:
    """Handles reasoning across multiple documents and contexts"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._relationship_cache = {}
        
    async def find_cross_context_insights(
        self, 
        query: str, 
        primary_results: List[Dict],
        conversation_history: List[Dict] = None
    ) -> CrossContextInsight:
        """Find insights that span multiple documents/contexts"""
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            # Extract entities and concepts from query
            entities = self._extract_entities(query)
            concepts = self._extract_concepts(query)
            
            # Identify primary document context
            primary_docs = self._get_unique_documents(primary_results)
            
            # Find related documents
            related_docs = await self._find_related_documents(
                conn, primary_docs, entities, concepts
            )
            
            # Extract cross-context patterns
            insights = await self._extract_insights(
                conn, query, primary_docs, related_docs, conversation_history
            )
            
            # Build comprehensive response
            return CrossContextInsight(
                query=query,
                primary_context=primary_docs[0] if primary_docs else {},
                related_contexts=related_docs,
                insights=insights,
                confidence=self._calculate_confidence(insights, related_docs)
            )
            
        finally:
            await conn.close()
    
    async def find_document_relationships(
        self, 
        document_ids: List[str]
    ) -> List[DocumentRelationship]:
        """Find relationships between documents"""
        
        if len(document_ids) < 2:
            return []
            
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            relationships = []
            
            # Get document details
            docs = await conn.fetch("""
                SELECT id, title, summary, created_at
                FROM documents 
                WHERE id = ANY($1)
            """, document_ids)
            
            doc_map = {doc['id']: doc for doc in docs}
            
            # Check each pair
            for i in range(len(document_ids)):
                for j in range(i + 1, len(document_ids)):
                    doc1_id = document_ids[i]
                    doc2_id = document_ids[j]
                    
                    if doc1_id not in doc_map or doc2_id not in doc_map:
                        continue
                    
                    # Find relationships
                    rels = await self._analyze_document_pair(
                        conn, doc_map[doc1_id], doc_map[doc2_id]
                    )
                    relationships.extend(rels)
            
            return relationships
            
        finally:
            await conn.close()
    
    async def suggest_connections(
        self,
        query: str,
        document_context: Dict
    ) -> List[Dict]:
        """Suggest how insights from one document could apply to another context"""
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            suggestions = []
            
            # Extract key concepts from the document
            doc_concepts = await self._extract_document_concepts(conn, document_context['id'])
            
            # Find documents with complementary concepts
            complementary = await conn.fetch("""
                SELECT DISTINCT d.id, d.title, d.summary
                FROM documents d
                JOIN chunks c ON c.document_id = d.id
                WHERE d.id != $1
                AND (
                    -- Look for problem-solution patterns
                    (c.content ILIKE '%problem%' AND $2 ILIKE '%solution%') OR
                    (c.content ILIKE '%solution%' AND $2 ILIKE '%problem%') OR
                    (c.content ILIKE '%need%' AND $2 ILIKE '%tool%') OR
                    (c.content ILIKE '%challenge%' AND $2 ILIKE '%approach%')
                )
                LIMIT 5
            """, document_context['id'], ' '.join(doc_concepts))
            
            for comp_doc in complementary:
                # Analyze how they might connect
                connection = await self._analyze_connection_potential(
                    conn, document_context, dict(comp_doc), query
                )
                if connection:
                    suggestions.append(connection)
            
            return suggestions
            
        finally:
            await conn.close()
    
    async def _find_related_documents(
        self,
        conn: asyncpg.Connection,
        primary_docs: List[Dict],
        entities: List[str],
        concepts: List[str]
    ) -> List[Dict]:
        """Find documents related by entities or concepts"""
        
        if not primary_docs:
            return []
        
        primary_ids = [doc['id'] for doc in primary_docs]
        
        # Search for documents with shared entities or concepts
        related = await conn.fetch("""
            SELECT DISTINCT d.id, d.title, d.summary, d.source_type,
                   COUNT(DISTINCT c.id) as relevance_count
            FROM documents d
            JOIN chunks c ON c.document_id = d.id
            WHERE d.id != ALL($1)
            AND (
                -- Entity matches
                c.speaker = ANY($2) OR
                -- Concept matches
                c.content ILIKE ANY($3) OR
                -- Cross-references
                c.content ILIKE ANY($4)
            )
            GROUP BY d.id, d.title, d.summary, d.source_type
            ORDER BY relevance_count DESC
            LIMIT 5
        """, 
        primary_ids,
        entities,
        [f'%{concept}%' for concept in concepts],
        [f'%{doc["title"]}%' for doc in primary_docs if doc.get("title")]
        )
        
        return [dict(doc) for doc in related]
    
    async def _extract_insights(
        self,
        conn: asyncpg.Connection,
        query: str,
        primary_docs: List[Dict],
        related_docs: List[Dict],
        conversation_history: List[Dict] = None
    ) -> List[str]:
        """Extract cross-context insights"""
        
        insights = []
        
        # Pattern 1: People connections
        people_insights = await self._find_people_connections(
            conn, primary_docs, related_docs
        )
        insights.extend(people_insights)
        
        # Pattern 2: Solution-Problem matching
        solution_insights = await self._find_solution_matches(
            conn, query, primary_docs, related_docs
        )
        insights.extend(solution_insights)
        
        # Pattern 3: Temporal progression
        temporal_insights = await self._find_temporal_patterns(
            conn, primary_docs, related_docs
        )
        insights.extend(temporal_insights)
        
        # Pattern 4: Technology complementarity
        tech_insights = await self._find_technology_synergies(
            conn, primary_docs, related_docs
        )
        insights.extend(tech_insights)
        
        return insights
    
    async def _analyze_document_pair(
        self,
        conn: asyncpg.Connection,
        doc1: Dict,
        doc2: Dict
    ) -> List[DocumentRelationship]:
        """Analyze relationship between two documents"""
        
        relationships = []
        
        # Check for shared people
        people1 = await conn.fetch("""
            SELECT DISTINCT speaker FROM chunks 
            WHERE document_id = $1 AND speaker IS NOT NULL
        """, doc1['id'])
        
        people2 = await conn.fetch("""
            SELECT DISTINCT speaker FROM chunks 
            WHERE document_id = $1 AND speaker IS NOT NULL
        """, doc2['id'])
        
        people1_set = {p['speaker'] for p in people1}
        people2_set = {p['speaker'] for p in people2}
        shared_people = people1_set & people2_set
        
        if shared_people:
            relationships.append(DocumentRelationship(
                doc1_id=doc1['id'],
                doc1_title=doc1['title'],
                doc2_id=doc2['id'],
                doc2_title=doc2['title'],
                relationship_type='people',
                confidence=0.9,
                evidence=[f"Both involve: {', '.join(shared_people)}"]
            ))
        
        # Check for topic overlap
        topics1 = await self._extract_document_concepts(conn, doc1['id'])
        topics2 = await self._extract_document_concepts(conn, doc2['id'])
        
        topic_overlap = set(topics1) & set(topics2)
        if len(topic_overlap) >= 2:
            relationships.append(DocumentRelationship(
                doc1_id=doc1['id'],
                doc1_title=doc1['title'],
                doc2_id=doc2['id'],
                doc2_title=doc2['title'],
                relationship_type='topic',
                confidence=0.7 + (0.1 * min(len(topic_overlap), 3)),
                evidence=[f"Shared topics: {', '.join(list(topic_overlap)[:3])}"]
            ))
        
        return relationships
    
    async def _find_people_connections(
        self,
        conn: asyncpg.Connection,
        primary_docs: List[Dict],
        related_docs: List[Dict]
    ) -> List[str]:
        """Find insights about people across documents"""
        
        insights = []
        
        # Get all people mentioned
        all_doc_ids = [d['id'] for d in primary_docs + related_docs]
        people_mentions = await conn.fetch("""
            SELECT speaker, document_id, COUNT(*) as mention_count
            FROM chunks
            WHERE document_id = ANY($1) AND speaker IS NOT NULL
            GROUP BY speaker, document_id
        """, all_doc_ids)
        
        # Group by person
        person_docs = {}
        for mention in people_mentions:
            person = mention['speaker']
            if person not in person_docs:
                person_docs[person] = []
            person_docs[person].append(mention['document_id'])
        
        # Find people in multiple contexts
        for person, doc_ids in person_docs.items():
            if len(doc_ids) > 1:
                doc_titles = []
                for doc_id in doc_ids:
                    for doc in primary_docs + related_docs:
                        if doc['id'] == doc_id:
                            doc_titles.append(doc['title'])
                            break
                
                if len(doc_titles) > 1:
                    insights.append(
                        f"{person} appears in multiple contexts: {', '.join(doc_titles[:3])}"
                    )
        
        return insights
    
    async def _find_solution_matches(
        self,
        conn: asyncpg.Connection,
        query: str,
        primary_docs: List[Dict],
        related_docs: List[Dict]
    ) -> List[str]:
        """Match solutions to problems across documents"""
        
        insights = []
        
        # Identify if query is about finding solutions
        solution_keywords = ['how', 'kann', 'könnte', 'solve', 'help', 'nutzen', 'einsetzen']
        is_solution_query = any(kw in query.lower() for kw in solution_keywords)
        
        if not is_solution_query:
            return insights
        
        # Extract problems/needs from primary context
        for primary in primary_docs:
            problems = await conn.fetch("""
                SELECT content FROM chunks
                WHERE document_id = $1
                AND (content ILIKE '%problem%' OR content ILIKE '%need%' OR 
                     content ILIKE '%challenge%' OR content ILIKE '%anforderung%')
                LIMIT 5
            """, primary['id'])
            
            # Find potential solutions in related docs
            for related in related_docs:
                solutions = await conn.fetch("""
                    SELECT content FROM chunks
                    WHERE document_id = $1
                    AND (content ILIKE '%solution%' OR content ILIKE '%lösung%' OR
                         content ILIKE '%approach%' OR content ILIKE '%tool%')
                    LIMIT 5
                """, related['id'])
                
                if problems and solutions:
                    insights.append(
                        f"Potential connection: {related['title']} might address needs from {primary['title']}"
                    )
        
        return insights
    
    async def _find_temporal_patterns(
        self,
        conn: asyncpg.Connection,
        primary_docs: List[Dict],
        related_docs: List[Dict]
    ) -> List[str]:
        """Find temporal relationships between documents"""
        
        insights = []
        all_docs = primary_docs + related_docs
        
        # Sort by creation date if available
        dated_docs = [d for d in all_docs if d.get('created_at')]
        dated_docs.sort(key=lambda x: x['created_at'])
        
        if len(dated_docs) >= 2:
            # Check for evolution of topics
            for i in range(len(dated_docs) - 1):
                doc1 = dated_docs[i]
                doc2 = dated_docs[i + 1]
                
                # Check if topics evolved
                topics1 = await self._extract_document_concepts(conn, doc1['id'])
                topics2 = await self._extract_document_concepts(conn, doc2['id'])
                
                common = set(topics1) & set(topics2)
                if common:
                    insights.append(
                        f"Topic evolution: '{', '.join(list(common)[:2])}' discussed in both {doc1['title']} and later in {doc2['title']}"
                    )
        
        return insights
    
    async def _find_technology_synergies(
        self,
        conn: asyncpg.Connection,
        primary_docs: List[Dict],
        related_docs: List[Dict]
    ) -> List[str]:
        """Find technology synergies across documents"""
        
        insights = []
        
        # Technology keywords
        tech_keywords = [
            'api', 'integration', 'automation', 'tool', 'server', 'system',
            'platform', 'framework', 'service', 'protocol', 'workflow'
        ]
        
        # Extract technologies from all documents
        doc_technologies = {}
        
        for doc in primary_docs + related_docs:
            techs = await conn.fetch("""
                SELECT DISTINCT 
                    regexp_matches(LOWER(content), '\\b(' || $2 || ')\\w*\\b', 'g') as tech
                FROM chunks
                WHERE document_id = $1
            """, doc['id'], '|'.join(tech_keywords))
            
            doc_technologies[doc['id']] = {
                'title': doc['title'],
                'techs': [t['tech'][0] for t in techs if t['tech']]
            }
        
        # Find complementary technologies
        for doc1_id, doc1_info in doc_technologies.items():
            for doc2_id, doc2_info in doc_technologies.items():
                if doc1_id >= doc2_id:  # Avoid duplicates
                    continue
                
                # Check for integration potential
                doc1_techs = set(doc1_info['techs'])
                doc2_techs = set(doc2_info['techs'])
                
                if ('api' in doc1_techs and 'integration' in doc2_techs) or \
                   ('server' in doc1_techs and 'automation' in doc2_techs):
                    insights.append(
                        f"Integration opportunity: {doc1_info['title']} and {doc2_info['title']} could work together"
                    )
        
        return insights
    
    async def _extract_document_concepts(
        self,
        conn: asyncpg.Connection,
        document_id: str
    ) -> List[str]:
        """Extract key concepts from a document"""
        
        # Get document chunks
        chunks = await conn.fetch("""
            SELECT content FROM chunks
            WHERE document_id = $1
            AND chunk_type = 'topic'
            LIMIT 10
        """, document_id)
        
        concepts = []
        concept_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Proper nouns
            r'\b(\w+(?:automation|system|service|platform|tool))\b',  # Tech terms
            r'\b(\w+(?:kräfte|agentur|vermittlung|dienst))\b'  # German business terms
        ]
        
        for chunk in chunks:
            content = chunk['content']
            for pattern in concept_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                concepts.extend(matches)
        
        # Deduplicate and return top concepts
        concept_counts = {}
        for concept in concepts:
            concept_lower = concept.lower()
            if len(concept_lower) > 3:  # Skip short words
                concept_counts[concept_lower] = concept_counts.get(concept_lower, 0) + 1
        
        # Sort by frequency
        sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
        return [concept for concept, _ in sorted_concepts[:10]]
    
    async def _analyze_connection_potential(
        self,
        conn: asyncpg.Connection,
        doc1: Dict,
        doc2: Dict,
        query: str
    ) -> Optional[Dict]:
        """Analyze how two documents might connect based on query"""
        
        # Extract key information from both documents
        doc1_chunks = await conn.fetch("""
            SELECT content, speaker FROM chunks
            WHERE document_id = $1
            ORDER BY importance_score DESC NULLS LAST
            LIMIT 5
        """, doc1['id'])
        
        doc2_chunks = await conn.fetch("""
            SELECT content, speaker FROM chunks
            WHERE document_id = $1
            ORDER BY importance_score DESC NULLS LAST
            LIMIT 5
        """, doc2['id'])
        
        # Look for complementary patterns
        doc1_content = ' '.join([c['content'] for c in doc1_chunks])
        doc2_content = ' '.join([c['content'] for c in doc2_chunks])
        
        connection_score = 0
        reasons = []
        
        # Check for problem-solution match
        if ('problem' in doc1_content.lower() and 'solution' in doc2_content.lower()) or \
           ('need' in doc1_content.lower() and 'provide' in doc2_content.lower()):
            connection_score += 0.4
            reasons.append("Potential problem-solution match")
        
        # Check for technology overlap
        tech_terms = ['api', 'integration', 'automation', 'server', 'system']
        doc1_techs = [t for t in tech_terms if t in doc1_content.lower()]
        doc2_techs = [t for t in tech_terms if t in doc2_content.lower()]
        
        if doc1_techs and doc2_techs:
            overlap = set(doc1_techs) & set(doc2_techs)
            if overlap:
                connection_score += 0.3
                reasons.append(f"Shared technology focus: {', '.join(overlap)}")
        
        # Check query relevance
        query_terms = self._extract_entities(query) + self._extract_concepts(query)
        if any(term.lower() in doc1_content.lower() and term.lower() in doc2_content.lower() 
               for term in query_terms):
            connection_score += 0.3
            reasons.append("Both relevant to query terms")
        
        if connection_score > 0.5:
            return {
                'source_doc': doc1['title'],
                'target_doc': doc2['title'],
                'connection_score': connection_score,
                'reasons': reasons,
                'suggestion': f"{doc2['title']} might provide insights applicable to {doc1['title']}"
            }
        
        return None
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text"""
        # Simple pattern-based extraction
        entities = []
        
        # Capitalized words (likely names/companies)
        cap_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        entities.extend(re.findall(cap_pattern, text))
        
        # Known entities from context
        known_entities = ['Sascha', 'Marco', 'Antonio', 'Careli', 'Claude', 'MCP']
        for entity in known_entities:
            if entity.lower() in text.lower():
                entities.append(entity)
        
        return list(set(entities))
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        concepts = []
        
        # Technology concepts
        tech_patterns = [
            r'\b(\w*(?:server|tool|system|platform|automation|integration))\b',
            r'\b(\w*(?:lösung|problem|anforderung|bedarf))\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            concepts.extend(matches)
        
        return list(set(concepts))
    
    def _get_unique_documents(self, search_results: List[Dict]) -> List[Dict]:
        """Extract unique documents from search results"""
        seen = set()
        docs = []
        
        for result in search_results:
            if 'document' in result and result['document']:
                doc_id = result['document'].get('id') or result.get('document_id')
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    docs.append({
                        'id': doc_id,
                        'title': result['document'].get('document_title', 'Unknown'),
                        'source_type': result['document'].get('source_type'),
                        'created_at': result['document'].get('created_at')
                    })
        
        return docs
    
    def _calculate_confidence(self, insights: List[str], related_docs: List[Dict]) -> float:
        """Calculate confidence score for cross-context insights"""
        base_score = 0.5
        
        # More insights = higher confidence
        if insights:
            base_score += min(len(insights) * 0.1, 0.3)
        
        # More related documents = higher confidence  
        if related_docs:
            base_score += min(len(related_docs) * 0.05, 0.2)
        
        return min(base_score, 1.0)