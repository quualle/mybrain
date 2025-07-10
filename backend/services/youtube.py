"""
YouTube service for extracting video data and transcripts
"""

import re
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Optional, List
import asyncio


class YouTubeService:
    """Service for handling YouTube video extraction"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    async def extract_video_data(self, url: str) -> Dict:
        """Extract video metadata and transcript from YouTube URL"""
        # Extract video ID
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Get video metadata
        metadata = await self._get_video_metadata(url)
        
        # Get transcript
        transcript_data = await self._get_transcript(video_id)
        
        return {
            'video_id': video_id,
            'url': url,
            'title': metadata.get('title', 'Unknown Title'),
            'channel': metadata.get('uploader', 'Unknown Channel'),
            'duration': metadata.get('duration', 0),
            'thumbnail': metadata.get('thumbnail'),
            'transcript': transcript_data['text'] if transcript_data else None,
            'transcript_segments': transcript_data['segments'] if transcript_data else [],
            'language': transcript_data['language'] if transcript_data else None
        }
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*&v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _get_video_metadata(self, url: str) -> Dict:
        """Get video metadata using yt-dlp"""
        loop = asyncio.get_event_loop()
        
        def extract_info():
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        # Run in executor to avoid blocking
        info = await loop.run_in_executor(None, extract_info)
        
        return {
            'title': info.get('title'),
            'uploader': info.get('uploader'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'description': info.get('description'),
            'upload_date': info.get('upload_date'),
            'view_count': info.get('view_count')
        }
    
    async def _get_transcript(self, video_id: str) -> Optional[Dict]:
        """Get video transcript with timestamps"""
        loop = asyncio.get_event_loop()
        
        def fetch_transcript():
            try:
                # Try to get transcript in different languages
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Prefer manually created transcripts
                try:
                    # Try German first
                    transcript = transcript_list.find_transcript(['de'])
                except:
                    try:
                        # Then English
                        transcript = transcript_list.find_transcript(['en'])
                    except:
                        # Fall back to auto-generated
                        transcript = transcript_list.find_generated_transcript(['de', 'en'])
                
                # Fetch the transcript
                transcript_data = transcript.fetch()
                
                # Combine all text
                full_text = ' '.join([segment['text'] for segment in transcript_data])
                
                # Format segments with timestamps
                segments = []
                for segment in transcript_data:
                    segments.append({
                        'start': segment['start'],
                        'duration': segment['duration'],
                        'text': segment['text'].strip()
                    })
                
                return {
                    'text': full_text,
                    'segments': segments,
                    'language': transcript.language_code
                }
                
            except Exception as e:
                print(f"Error fetching transcript: {e}")
                return None
        
        # Run in executor
        return await loop.run_in_executor(None, fetch_transcript)
    
    def format_transcript_with_timestamps(self, segments: List[Dict]) -> str:
        """Format transcript segments with timestamps"""
        formatted_lines = []
        
        for segment in segments:
            # Convert seconds to MM:SS format
            minutes = int(segment['start'] // 60)
            seconds = int(segment['start'] % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            # Add formatted line
            formatted_lines.append(f"{timestamp} {segment['text']}")
        
        return '\n'.join(formatted_lines)