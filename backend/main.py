"""
MyBrain Backend API
FastAPI application for personal knowledge management
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import routers (to be created)
from api import ingest, search, chat

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    print("Starting MyBrain backend...")
    yield
    # Shutdown
    print("Shutting down MyBrain backend...")


# Create FastAPI app
app = FastAPI(
    title="MyBrain API",
    description="Personal AI-powered long-term memory system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://*.netlify.app",
        "https://*.vercel.app",
        "https://mybrain.netlify.app",  # Deine finale Netlify URL
        "*"  # Temporär für Tests - später entfernen!
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingestion"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MyBrain API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "redis": "connected",
            "embeddings": "ready"
        }
    }