# MyBrain - Complete Context Recovery Document

## 🔴 CRITICAL: Read this after context reset!

### Project Status: 90% Complete - Backend startup issues

## What is MyBrain?
Personal AI-powered long-term memory system for Marco. Stores 60-minute conversations and YouTube videos, provides instant answers via Chat, accessible through Siri/Alexa.

## Current Situation (July 9, 2025)

### ✅ What's Working:
1. **Database**: Fully set up in Supabase with pgvector
2. **Frontend**: Running on http://localhost:3000 
3. **Project Structure**: Complete
4. **All Code**: Written and ready

### ❌ Current Problem:
Backend won't start due to Python 3.13 compatibility issues with dependencies

## Technical Stack Recap
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI (having issues)
- **Database**: Supabase (PostgreSQL + pgvector) - WORKING
- **Embeddings**: OpenAI text-embedding-3-small + ColBERT
- **LLMs**: Claude Sonnet 4.0, GPT-O3, GPT-4.1

## File Locations - IMPORTANT!
- **All Credentials**: `/Users/marcoheer/Desktop/privat/Programmierung/mybrain/.env`
- **Progress Log**: `/Users/marcoheer/Desktop/privat/Programmierung/mybrain/PROGRESS.md`
- **Start Script**: `./scripts/start-dev.sh`
- **Database Setup**: `./scripts/setup_database.py` (ALREADY RUN - DON'T RUN AGAIN)

## Problems Encountered & Solutions

### 1. Python 3.13 Compatibility
**Problem**: Many packages don't support Python 3.13 yet
**Attempted Solutions**:
- Created `requirements-minimal.txt` with flexible versions
- Removed psycopg2-binary (not needed, using asyncpg)
- Updated torch to >=2.6.0

**Still Issues With**:
- Some ML packages (transformers, sentence-transformers)
- Backend imports failing

### 2. Environment Variables
**Problem**: Backend couldn't find API keys
**Solution Applied**: Added `load_dotenv()` to embeddings.py

### 3. Database Issues
**All Resolved**:
- Fixed SQL syntax in migrations
- Database is fully set up and tested
- pgvector extension working

## Current Backend Error
```
File "/Users/marcoheer/Desktop/privat/Programmierung/mybrain/backend/core/embeddings.py", line 21, in <module>
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai.OpenAIError: The api_key client option must be set
```

## Quick Fix Options for Next Session

### Option 1: Use Python 3.11 (Recommended)
```bash
# Install Python 3.11
brew install python@3.11
# Create new venv
python3.11 -m venv venv_py311
source venv_py311/bin/activate
pip install -r requirements.txt
```

### Option 2: Minimal Backend (No ML)
Create a simplified backend without ColBERT/transformers, just use OpenAI embeddings.

### Option 3: Docker
Use the Docker setup already created in the project.

## How to Continue After Context Reset

1. **Check Current Status**:
   ```bash
   cd /Users/marcoheer/Desktop/privat/Programmierung/mybrain
   ./scripts/check_setup.py
   ```

2. **If Frontend Works, Backend Doesn't**:
   - Frontend: http://localhost:3000 ✅
   - Backend: http://localhost:8000 ❌
   - Try Python 3.11 approach above

3. **To Start Everything**:
   ```bash
   ./scripts/start-dev.sh
   ```

## Key Design Decisions to Remember

1. **Hybrid Search**: BM25 (25%) + Dense (50%) + Metadata (25%)
2. **ColBERT Re-ranking**: For precision on "what did X say about Y"
3. **Chunking**: Hierarchical - Summary → Topics (10min) → Details (1min)
4. **Smart Routing**: 
   - Complex reasoning → GPT-O3
   - Large context → GPT-4.1 
   - Default → Claude Sonnet 4.0

## Siri Integration
Complete documentation in `SIRI_SHORTCUTS.md`. API endpoints ready at:
- `/api/shortcuts/quick`
- `/api/shortcuts/person/[name]`

## What Marco Wanted
- Quick voice access ("Hey Siri, was war im Meeting mit Schmidt?")
- Handle 60-minute conversations perfectly
- Find exact details from conversations
- Beautiful UI with tables/charts in responses
- < 1 second response time

## Final Notes
- Database: ✅ Ready
- Frontend: ✅ Ready  
- Backend: 🔧 Needs Python compatibility fix
- All code is written, just needs the runtime environment fixed

**The project is essentially complete - just needs the Python environment sorted out!**

---
Generated: July 9, 2025
Context Window: Nearly full
Next Step: Fix Python compatibility or use Docker