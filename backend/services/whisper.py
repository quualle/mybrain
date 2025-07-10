"""
Whisper service for audio transcription
Uses OpenAI's Whisper API
"""

import os
import io
import tempfile
from typing import Dict, Optional, BinaryIO
from openai import AsyncOpenAI
import asyncio


class WhisperService:
    """Service for transcribing audio using OpenAI Whisper"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.supported_formats = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
        self.max_file_size = 25 * 1024 * 1024  # 25MB limit
    
    async def transcribe(self, 
                        audio_content: bytes,
                        filename: str,
                        language: Optional[str] = None,
                        prompt: Optional[str] = None) -> Dict:
        """
        Transcribe audio content using Whisper API
        
        Args:
            audio_content: Audio file content as bytes
            filename: Original filename (for format detection)
            language: Optional language code (e.g., 'de', 'en')
            prompt: Optional prompt to guide transcription
        
        Returns:
            Dict with transcript text, segments, duration, and detected language
        """
        # Validate file size
        if len(audio_content) > self.max_file_size:
            raise ValueError(f"Audio file too large. Maximum size is 25MB.")
        
        # Validate file format
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_ext}")
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            tmp_file.write(audio_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Transcribe with detailed response
            with open(tmp_file_path, 'rb') as audio_file:
                # Get detailed transcription with timestamps
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language != 'auto' else None,
                    prompt=prompt,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Process response
            result = {
                'text': response.text,
                'language': response.language,
                'duration': response.duration if hasattr(response, 'duration') else None,
                'segments': []
            }
            
            # Extract segments with timestamps if available
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    result['segments'].append({
                        'id': segment.id,
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip()
                    })
            
            return result
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
    
    async def transcribe_with_speakers(self,
                                     audio_content: bytes,
                                     filename: str,
                                     speakers: Optional[list] = None) -> Dict:
        """
        Transcribe audio with speaker diarization hints
        Note: Whisper doesn't directly support speaker diarization,
        but we can use prompts to help identify speakers
        """
        # Create a prompt with speaker names if provided
        prompt = None
        if speakers:
            speaker_names = ', '.join(speakers)
            prompt = f"This is a conversation between {speaker_names}. "
        
        # Get base transcription
        result = await self.transcribe(audio_content, filename, prompt=prompt)
        
        # Post-process to identify speakers (basic heuristic)
        if speakers and len(speakers) > 1:
            result['segments'] = self._identify_speakers(result['segments'], speakers)
        
        return result
    
    def _identify_speakers(self, segments: list, speakers: list) -> list:
        """
        Basic speaker identification using turn-taking heuristics
        This is a simplified approach - for better results, use dedicated
        speaker diarization services
        """
        current_speaker_idx = 0
        
        for i, segment in enumerate(segments):
            # Simple heuristic: alternate speakers on significant pauses
            if i > 0:
                time_gap = segment['start'] - segments[i-1]['end']
                if time_gap > 2.0:  # 2 second pause might indicate speaker change
                    current_speaker_idx = (current_speaker_idx + 1) % len(speakers)
            
            segment['speaker'] = speakers[current_speaker_idx]
        
        return segments
    
    async def get_supported_languages(self) -> list:
        """Get list of supported languages for transcription"""
        return [
            {'code': 'en', 'name': 'English'},
            {'code': 'de', 'name': 'German'},
            {'code': 'es', 'name': 'Spanish'},
            {'code': 'fr', 'name': 'French'},
            {'code': 'it', 'name': 'Italian'},
            {'code': 'pt', 'name': 'Portuguese'},
            {'code': 'nl', 'name': 'Dutch'},
            {'code': 'pl', 'name': 'Polish'},
            {'code': 'ru', 'name': 'Russian'},
            {'code': 'ja', 'name': 'Japanese'},
            {'code': 'ko', 'name': 'Korean'},
            {'code': 'zh', 'name': 'Chinese'}
        ]
    
    def estimate_transcription_time(self, file_size: int) -> float:
        """Estimate transcription time based on file size"""
        # Rough estimate: 1MB takes about 2-3 seconds
        return (file_size / (1024 * 1024)) * 2.5