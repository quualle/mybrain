# MyBrain 🧠

Personal AI-powered long-term memory system that intelligently stores and retrieves information from hour-long conversations, YouTube videos, and personal notes.

## Features

- **Intelligent Storage**: Processes 60-minute conversations and YouTube videos with smart chunking
- **Hybrid Search**: Combines keyword search (BM25), semantic search, and ColBERT token-level matching
- **Multi-Platform Access**: Web interface, Siri shortcuts, and Alexa integration ready
- **Rich Responses**: Beautiful markdown rendering with tables, charts, and code highlighting
- **Fast Retrieval**: Sub-second response times with Redis caching
- **Multi-LLM Support**: Claude Sonnet 4.0, GPT-O3 (reasoning), and GPT-4.1 (large context)

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Next.js 14 with TypeScript
- **Database**: Supabase (PostgreSQL + pgvector)
- **Embeddings**: OpenAI text-embedding-3-small + ColBERT
- **Cache**: Upstash Redis
- **Deployment**: Vercel

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and add your credentials
3. Install dependencies:
   ```bash
   # Backend
   pip install -r requirements.txt
   
   # Frontend
   npm install
   ```
4. Run database migrations:
   ```bash
   python scripts/setup_database.py
   ```
5. Start the development servers:
   ```bash
   # Backend
   uvicorn backend.main:app --reload
   
   # Frontend (new terminal)
   npm run dev
   ```

## API Endpoints

- `POST /api/v1/ingest/youtube` - Ingest YouTube video
- `POST /api/v1/ingest/audio` - Ingest audio file
- `POST /api/v1/ingest/text` - Ingest text/markdown
- `GET /api/v1/search` - Search knowledge base
- `POST /api/v1/chat` - Chat with AI
- `GET /api/v1/quick/{query}` - Quick access for Siri/Alexa

## Architecture

- **Hierarchical Chunking**: Summary → Topic blocks (10min) → Detail chunks (1min)
- **3-Stage Retrieval**: Broad search → ColBERT re-ranking → Context assembly
- **Smart LLM Routing**: Routes to appropriate model based on query complexity

## License

Private use only.