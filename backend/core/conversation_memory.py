"""
Conversation Memory System for MyBrain
Tracks conversation context and original user intent
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime


@dataclass
class ConversationIntent:
    """Represents the original user intent throughout a conversation"""
    original_question: str
    clarified_question: Optional[str] = None
    entities_mentioned: List[str] = None
    search_attempts: List[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.entities_mentioned is None:
            self.entities_mentioned = []
        if self.search_attempts is None:
            self.search_attempts = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConversationMemory:
    """Manages conversation context and tracks user intent"""
    
    def __init__(self):
        self.current_intent: Optional[ConversationIntent] = None
        self.entity_aliases: Dict[str, List[str]] = {}
        self.conversation_entities: List[str] = []
        
    def extract_intent(self, messages: List[Dict]) -> ConversationIntent:
        """Extract the original intent from conversation history"""
        
        if not messages:
            return None
            
        # Find the first substantive user question
        original_question = None
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Skip greetings and very short messages
                if len(content) > 20 and not self._is_greeting(content):
                    original_question = content
                    break
        
        if not original_question:
            original_question = messages[-1].get('content', '') if messages else ""
            
        # Extract entities from all messages
        all_entities = []
        for msg in messages:
            entities = self._extract_entities(msg.get('content', ''))
            all_entities.extend(entities)
            
        intent = ConversationIntent(
            original_question=original_question,
            entities_mentioned=list(set(all_entities))
        )
        
        return intent
    
    def track_search_attempt(self, query: str, results_found: bool, strategy: str):
        """Track each search attempt in the conversation"""
        if self.current_intent:
            self.current_intent.search_attempts.append({
                'query': query,
                'strategy': strategy,
                'found_results': results_found,
                'timestamp': datetime.now()
            })
    
    def should_remind_original_question(self, current_response: str) -> bool:
        """Determine if we should remind about the original question"""
        if not self.current_intent:
            return False
            
        # If we've done multiple searches
        if len(self.current_intent.search_attempts) >= 2:
            # And the current response doesn't address the original question
            original_keywords = self._extract_keywords(self.current_intent.original_question)
            response_keywords = self._extract_keywords(current_response)
            
            overlap = len(set(original_keywords) & set(response_keywords))
            if overlap < len(original_keywords) * 0.3:  # Less than 30% overlap
                return True
                
        return False
    
    def format_reminder(self) -> str:
        """Format a reminder about the original question"""
        if not self.current_intent:
            return ""
            
        return f"\n\n---\nZur Erinnerung an deine ursprüngliche Frage: {self.current_intent.original_question}"
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract potential entities from text"""
        entities = []
        
        # Names (capitalized words)
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        names = re.findall(name_pattern, text)
        entities.extend(names)
        
        # Companies/Products in quotes
        quote_pattern = r'["\'](.*?)["\']'
        quoted = re.findall(quote_pattern, text)
        entities.extend(quoted)
        
        # Technical terms (CamelCase, kebab-case, etc.)
        tech_pattern = r'\b[A-Za-z]+(?:[A-Z][a-z]+)+\b|\b[a-z]+(?:-[a-z]+)+\b'
        tech_terms = re.findall(tech_pattern, text)
        entities.extend(tech_terms)
        
        return entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Remove common words
        stopwords = {'der', 'die', 'das', 'und', 'oder', 'aber', 'mit', 'von', 'zu', 
                    'in', 'auf', 'an', 'für', 'bei', 'ist', 'sind', 'war', 'waren',
                    'the', 'a', 'an', 'and', 'or', 'but', 'with', 'from', 'to', 'in'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        return keywords
    
    def _is_greeting(self, text: str) -> bool:
        """Check if text is just a greeting"""
        greetings = ['hallo', 'hi', 'hey', 'guten tag', 'servus', 'moin']
        text_lower = text.lower().strip()
        return any(text_lower.startswith(g) for g in greetings) and len(text_lower) < 20
    
    def add_entity_alias(self, entity: str, aliases: List[str]):
        """Add aliases for an entity for better matching"""
        self.entity_aliases[entity.lower()] = [a.lower() for a in aliases]
        
    def resolve_entity(self, mention: str) -> str:
        """Resolve an entity mention to its canonical form"""
        mention_lower = mention.lower()
        
        # Direct match
        if mention_lower in self.entity_aliases:
            return mention
            
        # Check if mention is an alias
        for entity, aliases in self.entity_aliases.items():
            if mention_lower in aliases:
                return entity
                
        # Fuzzy match
        for entity, aliases in self.entity_aliases.items():
            all_terms = [entity] + aliases
            for term in all_terms:
                if mention_lower in term or term in mention_lower:
                    return entity
                    
        return mention