"""
Smart chunking algorithm for MyBrain
Optimized for 60-minute conversations and YouTube videos
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from datetime import timedelta


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    content: str
    chunk_type: str  # 'summary', 'topic', 'detail'
    chunk_index: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker: Optional[str] = None
    tokens: int = 0
    importance_score: float = 0.5
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "chunk_type": self.chunk_type,
            "chunk_index": self.chunk_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker": self.speaker,
            "tokens": self.tokens,
            "importance_score": self.importance_score,
            "metadata": self.metadata or {}
        }


class SmartChunker:
    """Hierarchical chunking system for long-form content"""
    
    def __init__(self, 
                 target_chunk_tokens: int = 750,
                 max_chunk_tokens: int = 1000,
                 overlap_tokens: int = 100):
        self.target_chunk_tokens = target_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        
    def chunk_transcript(self, 
                        transcript: str,
                        timestamps: Optional[List[Tuple[float, str]]] = None,
                        speakers: Optional[List[Tuple[str, str]]] = None) -> List[Chunk]:
        """
        Chunk a transcript with timestamps and speaker information
        
        Args:
            transcript: Full transcript text
            timestamps: List of (time_seconds, text) tuples
            speakers: List of (speaker_name, text) tuples
        """
        chunks = []
        
        # Create summary chunk
        summary = self._generate_summary_placeholder(transcript)
        chunks.append(Chunk(
            content=summary,
            chunk_type="summary",
            chunk_index=0,
            tokens=self._estimate_tokens(summary)
        ))
        
        # Split into topic chunks (10-minute segments for 60-min content)
        if timestamps:
            topic_chunks = self._create_topic_chunks_with_timestamps(timestamps)
        else:
            topic_chunks = self._create_topic_chunks_by_size(transcript)
        
        chunks.extend(topic_chunks)
        
        # Create detail chunks with overlap
        detail_chunks = self._create_detail_chunks(transcript, timestamps, speakers)
        chunks.extend(detail_chunks)
        
        # Assign importance scores
        chunks = self._calculate_importance_scores(chunks)
        
        return chunks
    
    def chunk_youtube_video(self,
                           transcript: str,
                           video_metadata: Dict) -> List[Chunk]:
        """Special handling for YouTube videos with auto-generated timestamps"""
        # Extract timestamps if available
        timestamps = self._extract_youtube_timestamps(transcript)
        
        # Use general transcript chunking
        chunks = self.chunk_transcript(transcript, timestamps)
        
        # Add video-specific metadata
        for chunk in chunks:
            chunk.metadata = chunk.metadata or {}
            chunk.metadata.update({
                "source": "youtube",
                "video_id": video_metadata.get("video_id"),
                "channel": video_metadata.get("channel"),
                "duration": video_metadata.get("duration")
            })
        
        return chunks
    
    def _create_topic_chunks_with_timestamps(self, 
                                           timestamps: List[Tuple[float, str]]) -> List[Chunk]:
        """Create topic-level chunks based on timestamps (10-min segments)"""
        chunks = []
        segment_duration = 600  # 10 minutes in seconds
        
        current_segment_start = 0
        current_segment_texts = []
        chunk_index = 1
        
        for time, text in timestamps:
            if time >= current_segment_start + segment_duration:
                # Create chunk for current segment
                if current_segment_texts:
                    content = " ".join(current_segment_texts)
                    chunks.append(Chunk(
                        content=content,
                        chunk_type="topic",
                        chunk_index=chunk_index,
                        start_time=current_segment_start,
                        end_time=time,
                        tokens=self._estimate_tokens(content)
                    ))
                    chunk_index += 1
                
                # Start new segment
                current_segment_start = time
                current_segment_texts = [text]
            else:
                current_segment_texts.append(text)
        
        # Don't forget the last segment
        if current_segment_texts:
            content = " ".join(current_segment_texts)
            chunks.append(Chunk(
                content=content,
                chunk_type="topic",
                chunk_index=chunk_index,
                start_time=current_segment_start,
                end_time=timestamps[-1][0] if timestamps else None,
                tokens=self._estimate_tokens(content)
            ))
        
        return chunks
    
    def _create_detail_chunks(self, 
                            transcript: str,
                            timestamps: Optional[List[Tuple[float, str]]] = None,
                            speakers: Optional[List[Tuple[str, str]]] = None) -> List[Chunk]:
        """Create detailed chunks with overlap, respecting speaker changes"""
        chunks = []
        
        if speakers:
            # Split by speaker changes
            return self._chunk_by_speakers(speakers, timestamps)
        
        # Fall back to size-based chunking
        sentences = self._split_into_sentences(transcript)
        
        current_chunk = []
        current_tokens = 0
        chunk_index = len(chunks) + 1
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.target_chunk_tokens:
                # Create chunk
                if current_chunk:
                    content = " ".join(current_chunk)
                    chunks.append(Chunk(
                        content=content,
                        chunk_type="detail",
                        chunk_index=chunk_index,
                        tokens=current_tokens
                    ))
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(self._estimate_tokens(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            content = " ".join(current_chunk)
            chunks.append(Chunk(
                content=content,
                chunk_type="detail",
                chunk_index=chunk_index,
                tokens=current_tokens
            ))
        
        return chunks
    
    def _chunk_by_speakers(self,
                          speakers: List[Tuple[str, str]],
                          timestamps: Optional[List[Tuple[float, str]]] = None) -> List[Chunk]:
        """Create chunks based on speaker changes"""
        chunks = []
        current_speaker = None
        current_texts = []
        current_tokens = 0
        chunk_index = 1
        
        for speaker, text in speakers:
            text_tokens = self._estimate_tokens(text)
            
            # Check if we need to create a new chunk
            if (speaker != current_speaker or 
                current_tokens + text_tokens > self.max_chunk_tokens):
                
                if current_texts:
                    content = " ".join(current_texts)
                    chunks.append(Chunk(
                        content=content,
                        chunk_type="detail",
                        chunk_index=chunk_index,
                        speaker=current_speaker,
                        tokens=current_tokens
                    ))
                    chunk_index += 1
                
                current_speaker = speaker
                current_texts = [text]
                current_tokens = text_tokens
            else:
                current_texts.append(text)
                current_tokens += text_tokens
        
        # Add final chunk
        if current_texts:
            content = " ".join(current_texts)
            chunks.append(Chunk(
                content=content,
                chunk_type="detail",
                chunk_index=chunk_index,
                speaker=current_speaker,
                tokens=current_tokens
            ))
        
        return chunks
    
    def _calculate_importance_scores(self, chunks: List[Chunk]) -> List[Chunk]:
        """Calculate importance scores based on position and content"""
        for i, chunk in enumerate(chunks):
            if chunk.chunk_type == "summary":
                chunk.importance_score = 1.0
            elif chunk.chunk_type == "topic":
                chunk.importance_score = 0.8
            else:
                # Detail chunks - higher importance at beginning and end
                position_score = 1.0 - abs(i - len(chunks) / 2) / (len(chunks) / 2)
                
                # Boost score if chunk contains questions or important keywords
                content_score = 0.5
                if any(word in chunk.content.lower() for word in 
                      ["wichtig", "important", "problem", "lösung", "solution", "frage", "question"]):
                    content_score = 0.8
                
                chunk.importance_score = (position_score + content_score) / 2
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter - can be improved with spaCy
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Roughly 1 token per 4 characters for German/English
        return len(text) // 4
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get sentences for overlap based on token count"""
        overlap_sentences = []
        overlap_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = self._estimate_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.overlap_tokens:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break
        
        return overlap_sentences
    
    def _extract_youtube_timestamps(self, transcript: str) -> Optional[List[Tuple[float, str]]]:
        """Extract timestamps from YouTube transcript format"""
        # Pattern for timestamps like [00:01:23] or (1:23)
        pattern = r'[\[\(](\d{1,2}):(\d{2})(?::(\d{2}))?[\]\)]'
        
        timestamps = []
        last_end = 0
        
        for match in re.finditer(pattern, transcript):
            # Extract time components
            hours = int(match.group(3) or 0)
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Extract text after timestamp
            start = match.end()
            next_match = re.search(pattern, transcript[start:])
            if next_match:
                end = start + next_match.start()
            else:
                end = len(transcript)
            
            text = transcript[start:end].strip()
            if text:
                timestamps.append((total_seconds, text))
        
        return timestamps if timestamps else None
    
    def _generate_summary_placeholder(self, text: str) -> str:
        """Generate a placeholder summary - will be replaced by LLM later"""
        # Take first 1000 characters as temporary summary
        return f"[Summary to be generated] {text[:1000]}..."
    
    def _create_topic_chunks_by_size(self, text: str) -> List[Chunk]:
        """Create topic chunks by size when no timestamps available"""
        # Roughly split into 6 parts for 60-min content
        text_length = len(text)
        chunk_size = text_length // 6
        
        chunks = []
        for i in range(6):
            start = i * chunk_size
            end = start + chunk_size if i < 5 else text_length
            
            content = text[start:end]
            chunks.append(Chunk(
                content=content,
                chunk_type="topic",
                chunk_index=i + 1,
                tokens=self._estimate_tokens(content)
            ))
        
        return chunks


# Global instance
smart_chunker = SmartChunker()