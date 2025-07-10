"""
Minimal embeddings service using only OpenAI
For production deployment without heavy ML dependencies
"""

from typing import List, Dict, Optional
import os
from openai import AsyncOpenAI
import asyncio
import numpy as np

class MinimalEmbeddingService:
    """Lightweight embedding service using OpenAI embeddings"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
        
    async def encode(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        """Encode texts using OpenAI embeddings"""
        if not texts:
            return np.array([])
            
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.openai_client.embeddings.create(
                input=batch,
                model=self.model
            )
            batch_embeddings = [e.embedding for e in response.data]
            embeddings.extend(batch_embeddings)
            
        return np.array(embeddings)
    
    async def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query"""
        response = await self.openai_client.embeddings.create(
            input=[query],
            model=self.model
        )
        return np.array(response.data[0].embedding)

# Global instance
embedding_service = MinimalEmbeddingService()