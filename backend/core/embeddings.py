"""
Embedding service for MyBrain
Handles OpenAI text-embedding-3-small and ColBERT token embeddings
"""

import os
import numpy as np
from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
import torch
from transformers import AutoTokenizer, AutoModel
import asyncio
from functools import lru_cache
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EmbeddingService:
    """Multi-modal embedding service"""
    
    def __init__(self):
        self.openai_client = openai_client
        self.colbert_model = None
        self.colbert_tokenizer = None
        self.tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        
    async def initialize_colbert(self):
        """Lazy load ColBERT model"""
        if self.colbert_model is None:
            print("Loading ColBERT model...")
            self.colbert_tokenizer = AutoTokenizer.from_pretrained(
                "colbert-ir/colbertv2.0",
                token=os.getenv("HUGGINGFACE_TOKEN")
            )
            self.colbert_model = AutoModel.from_pretrained(
                "colbert-ir/colbertv2.0",
                token=os.getenv("HUGGINGFACE_TOKEN")
            )
            self.colbert_model.eval()
            print("ColBERT model loaded successfully")
    
    async def get_dense_embedding(self, text: str) -> List[float]:
        """Get dense embedding using OpenAI text-embedding-3-small"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting dense embedding: {e}")
            raise
    
    async def get_dense_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get dense embeddings for multiple texts efficiently"""
        try:
            # OpenAI supports batch embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            raise
    
    def get_colbert_embeddings(self, text: str) -> Tuple[List[List[float]], List[str]]:
        """Get token-level ColBERT embeddings"""
        if self.colbert_model is None:
            raise RuntimeError("ColBERT model not initialized. Call initialize_colbert() first.")
        
        # Tokenize
        inputs = self.colbert_tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        
        # Get embeddings
        with torch.no_grad():
            outputs = self.colbert_model(**inputs)
            token_embeddings = outputs.last_hidden_state
        
        # Convert tokens back to text
        token_ids = inputs['input_ids'][0].tolist()
        tokens = self.colbert_tokenizer.convert_ids_to_tokens(token_ids)
        
        # Remove padding tokens
        mask = inputs['attention_mask'][0].bool()
        token_embeddings = token_embeddings[0][mask]
        tokens = [t for t, m in zip(tokens, mask) if m]
        
        # Convert to list format
        embeddings_list = token_embeddings.tolist()
        
        return embeddings_list, tokens
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        return len(self.tiktoken_encoder.encode(text))
    
    def truncate_to_token_limit(self, text: str, max_tokens: int = 8000) -> str:
        """Truncate text to fit within token limit"""
        tokens = self.tiktoken_encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return self.tiktoken_encoder.decode(truncated_tokens)
    
    async def embed_document_hierarchical(self, 
                                        document_text: str,
                                        chunks: List[Dict]) -> Dict:
        """
        Create hierarchical embeddings for a document
        Returns embeddings for summary, topics, and detail chunks
        """
        result = {
            "summary_embedding": None,
            "chunk_embeddings": [],
            "colbert_embeddings": []
        }
        
        # Get summary embedding if available
        if "summary" in chunks[0]:
            result["summary_embedding"] = await self.get_dense_embedding(
                chunks[0]["summary"]
            )
        
        # Batch process chunk embeddings
        chunk_texts = [chunk["content"] for chunk in chunks]
        chunk_embeddings = await self.get_dense_embeddings_batch(chunk_texts)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = chunk_embeddings[i]
            result["chunk_embeddings"].append({
                "chunk_id": chunk.get("id", i),
                "embedding": chunk_embeddings[i],
                "tokens": self.count_tokens(chunk["content"])
            })
        
        # Get ColBERT embeddings for detail chunks (optional, for precision queries)
        # We'll only do this for important chunks to save resources
        if len(chunks) <= 10:  # Only for short documents
            await self.initialize_colbert()
            for chunk in chunks[:5]:  # Top 5 chunks only
                token_embeddings, tokens = self.get_colbert_embeddings(chunk["content"])
                result["colbert_embeddings"].append({
                    "chunk_id": chunk.get("id"),
                    "token_embeddings": token_embeddings,
                    "tokens": tokens
                })
        
        return result


# Global instance
embedding_service = EmbeddingService()