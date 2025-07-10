"""
Chat API endpoints for MyBrain
Handles LLM integration with RAG
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, AsyncGenerator
import os
import json
from datetime import datetime
import asyncio
import asyncpg

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from core.retrieval import HybridRetriever
from core.smart_routing import SmartQueryRouter
from core.conversation_memory import ConversationMemory
from core.fuzzy_search import FuzzySearchEngine
from core.cross_context_reasoning import CrossContextReasoner
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
retriever = HybridRetriever(os.getenv("DATABASE_URL"))
smart_router = SmartQueryRouter(os.getenv("DATABASE_URL"))
conversation_memory = ConversationMemory()
fuzzy_search = FuzzySearchEngine(os.getenv("DATABASE_URL"))
cross_context = CrossContextReasoner(os.getenv("DATABASE_URL"))


# Pydantic models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[Dict]] = None
    search_strategy: Optional[str] = "hybrid_with_fallback"
    model: Optional[str] = "claude-sonnet-4-20250514"
    stream: bool = True
    debug: bool = False
    
class Message(BaseModel):
    role: str
    content: str
    
class ChatResponse(BaseModel):
    response: str
    sources: List[Dict] = []
    model_used: str
    tokens_used: Optional[int] = None
    debug_info: Optional[Dict] = None


@router.post("/")
async def chat(request: ChatRequest):
    """Main chat endpoint with intelligent hybrid search and quality checking"""
    try:
        # New intelligent pipeline with parallel search
        response = await intelligent_chat_pipeline(
            query=request.message,
            conversation_history=request.conversation_history or [],
            preferred_model=request.model,
            stream=request.stream,
            debug=request.debug
        )
        
        if request.stream:
            return StreamingResponse(
                response,
                media_type="text/event-stream"
            )
        else:
            return response
            
    except Exception as e:
        import traceback
        print(f"Chat error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


async def intelligent_chat_pipeline(
    query: str,
    conversation_history: List[Dict],
    preferred_model: str,
    stream: bool = True,
    debug: bool = False
) -> Dict:
    """Intelligent pipeline with parallel search and quality checking"""
    
    # 1. Extract conversation intent and build context
    conversation_memory.current_intent = conversation_memory.extract_intent(conversation_history)
    
    conv_context = ""
    if conversation_history:
        conv_context = "\n\nBisheriger Gesprächsverlauf:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages
            conv_context += f"{msg['role'].upper()}: {msg['content'][:200]}...\n"
    
    # 2. Try fuzzy search first if regular search might fail
    fuzzy_docs = await fuzzy_search.fuzzy_search_documents(query)
    
    # 3. Smart routing based on query type
    routing_result = await smart_router.route_query(query, conversation_history)
    
    # Track search attempt
    conversation_memory.track_search_attempt(
        query, 
        bool(routing_result.get('chunks') or fuzzy_docs),
        routing_result.get('strategy', 'unknown')
    )
    
    # Get chunks based on routing strategy
    if routing_result.get('strategy') == 'document_ref' and routing_result.get('chunks'):
        # Use document-focused chunks
        unique_chunks = routing_result['chunks']
        print(f"Smart routing: Found document '{routing_result['documents'][0]['title'] if routing_result['documents'] else 'Unknown'}'")
    elif fuzzy_docs:
        # Use fuzzy search results
        print(f"Fuzzy search found {len(fuzzy_docs)} documents")
        # Get chunks from fuzzy matched documents
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
        try:
            all_chunks = []
            for doc in fuzzy_docs[:3]:  # Top 3 fuzzy matches
                chunks = await conn.fetch("""
                    SELECT c.*, d.title as document_title
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE c.document_id = $1
                    ORDER BY c.chunk_index
                    LIMIT 20
                """, doc['id'])
                
                for chunk in chunks:
                    chunk_dict = dict(chunk)
                    chunk_dict['document'] = {
                        'document_title': chunk['document_title'],
                        'relevance_score': doc['relevance_score']
                    }
                    all_chunks.append(chunk_dict)
            
            unique_chunks = all_chunks
        finally:
            await conn.close()
    else:
        # Fallback to parallel search
        search_tasks = [
            retriever.search(query=query, top_k=10, use_colbert_rerank=False),
            retriever.search(query=query, top_k=5, use_colbert_rerank=True)
        ]
        
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Merge results
        all_chunks = []
        for result in search_results:
            if isinstance(result, list):
                all_chunks.extend(result)
        
        # Deduplicate by content hash
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            chunk_hash = hash(chunk.get('content', ''))
            if chunk_hash not in seen:
                seen.add(chunk_hash)
                unique_chunks.append(chunk)
    
    # 4. Check for cross-context insights
    cross_context_insight = None
    if unique_chunks:
        try:
            cross_context_insight = await cross_context.find_cross_context_insights(
                query=query,
                primary_results=unique_chunks[:10],
                conversation_history=conversation_history
            )
            
            # If we found meaningful cross-context insights, enrich the chunks
            if cross_context_insight and cross_context_insight.insights:
                # Add cross-context information to the context
                cross_context_info = {
                    'content': f"Cross-Context Insights:\n" + "\n".join(cross_context_insight.insights),
                    'chunk_type': 'cross_context',
                    'importance_score': 0.9
                }
                unique_chunks.insert(0, cross_context_info)
        except Exception as e:
            print(f"Cross-context reasoning failed: {e}")
    
    # 5. Generate initial response
    initial_response = await route_to_model(
        message=query,
        context_chunks=unique_chunks[:10],  # Top 10 unique chunks
        preferred_model=preferred_model,
        stream=False  # Need complete response for quality check
    )
    
    # 6. Quality check with GPT-4.1-mini
    quality_score = await check_answer_quality(
        query=query,
        context=unique_chunks,
        answer=initial_response['response'],
        conversation_history=conv_context
    )
    
    # 7. Check if we should remind about original question
    should_remind = conversation_memory.should_remind_original_question(initial_response['response'])
    
    # 8. Fallback if quality is low
    if quality_score < 0.7:
        print(f"Quality score {quality_score} too low, using fallback with model knowledge")
        
        # Include original question context in fallback
        original_context = ""
        if conversation_memory.current_intent:
            original_context = f"\n\nUrsprüngliche Frage des Nutzers: {conversation_memory.current_intent.original_question}\n"
        
        fallback_response = await generate_with_model_knowledge(
            query=query,
            failed_context=unique_chunks,
            previous_attempt=initial_response['response'],
            conversation_history=conv_context + original_context,
            model=preferred_model
        )
        
        # Add reminder if needed
        final_response = fallback_response['response']
        if should_remind:
            final_response += conversation_memory.format_reminder()
        
        if stream:
            return create_streaming_response(final_response, fallback_response['model_used'])
        else:
            return ChatResponse(
                response=final_response,
                sources=format_sources(unique_chunks),
                model_used=fallback_response['model_used'],
                tokens_used=fallback_response.get('tokens_used')
            )
    
    # Return original response if quality is good
    final_response = initial_response['response']
    if should_remind:
        final_response += conversation_memory.format_reminder()
    
    if stream:
        return create_streaming_response(final_response, initial_response['model_used'])
    else:
        debug_info = None
        if debug:
            debug_info = {
                'routing_strategy': routing_result.get('strategy', 'unknown'),
                'chunks_found': len(unique_chunks),
                'quality_score': quality_score,
                'used_fallback': False,
                'fuzzy_matches': len(fuzzy_docs) if fuzzy_docs else 0,
                'original_intent': conversation_memory.current_intent.original_question if conversation_memory.current_intent else None
            }
            if routing_result.get('strategy') == 'document_ref':
                debug_info['matched_documents'] = [d['title'] for d in routing_result.get('documents', [])]
            if fuzzy_docs:
                debug_info['fuzzy_matched_docs'] = [{'title': d['title'], 'score': d['relevance_score']} for d in fuzzy_docs[:3]]
            if cross_context_insight and cross_context_insight.insights:
                debug_info['cross_context_insights'] = cross_context_insight.insights
                debug_info['related_contexts'] = [{'title': ctx.get('title', 'Unknown')} for ctx in cross_context_insight.related_contexts]
        
        return ChatResponse(
            response=final_response,
            sources=format_sources(unique_chunks),
            model_used=initial_response['model_used'],
            tokens_used=initial_response.get('tokens_used'),
            debug_info=debug_info
        )


async def check_answer_quality(
    query: str,
    context: List[Dict],
    answer: str,
    conversation_history: str = ""
) -> float:
    """Check answer quality using GPT-4.1-mini"""
    
    # Prepare context summary
    context_summary = "\n".join([chunk['content'][:100] + "..." for chunk in context[:5]])
    
    prompt = f"""Bewerte ob diese Antwort die Frage angemessen beantwortet.

{conversation_history}

Frage: {query}

Verfügbarer Kontext aus der Datenbank:
{context_summary}

Gegebene Antwort:
{answer}

Bewertungskriterien:
- Beantwortet die Antwort direkt die gestellte Frage?
- Nutzt die Antwort den verfügbaren Kontext sinnvoll?
- Ist die Antwort vollständig oder fehlen wichtige Informationen?

Bewertung:
- 0.9-1.0: Perfekt beantwortet mit relevantem Kontext
- 0.7-0.9: Gut beantwortet, kleinere Lücken
- 0.3-0.7: Teilweise beantwortet oder Kontext nicht optimal genutzt  
- 0.0-0.3: Verfehlt die Frage oder ignoriert wichtigen Kontext

Antworte NUR mit einer Zahl zwischen 0 und 1, z.B.: 0.85"""
    
    try:
        # Use GPT-4.1-mini for fast quality checking
        response = await openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Du bist ein Qualitätsprüfer für KI-Antworten. Antworte nur mit einer Dezimalzahl."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0
        )
        
        score_text = response.choices[0].message.content.strip()
        return float(score_text)
        
    except Exception as e:
        print(f"Quality check failed: {e}")
        return 0.8  # Default to assuming decent quality


async def generate_with_model_knowledge(
    query: str,
    failed_context: List[Dict],
    previous_attempt: str,
    conversation_history: str,
    model: str
) -> Dict:
    """Generate response using model knowledge when context is insufficient"""
    
    system_prompt = """Du bist ein intelligenter Assistent. 
Die Datenbank-Suche war nicht erfolgreich genug, um die Frage vollständig zu beantworten.
Nutze dein allgemeines Wissen, um eine hilfreiche Antwort zu geben.
Erwähne am Ende kurz, dass die Antwort auf allgemeinem KI-Wissen basiert."""
    
    user_message = f"""{conversation_history}

Ursprüngliche Frage: {query}

Erster Antwortversuch (unzureichend):
{previous_attempt}

Bitte beantworte die Frage vollständig und präzise mit deinem Wissen."""
    
    # Use O3 for complex reasoning or the preferred model
    if "was ist" in query.lower() or "erkläre" in query.lower():
        selected_model = model
    else:
        selected_model = "o3"  # For complex reasoning
    
    if selected_model.startswith("claude"):
        return await generate_claude_response(
            system_prompt, user_message, selected_model, False
        )
    else:
        return await generate_openai_response(
            system_prompt, user_message, selected_model, False
        )


def create_streaming_response(content: str, model_used: str):
    """Create a streaming response from complete content"""
    async def stream():
        # Split content into chunks for streaming effect
        words = content.split()
        chunk_size = 5
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i+chunk_size]) + ' '
            yield f"data: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.05)  # Small delay for streaming effect
            
        yield f"data: {json.dumps({'done': True, 'model_used': model_used})}\n\n"
    
    return stream()  # Return the generator directly, not call it


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    request.stream = True
    return await chat(request)


async def route_to_model(
    message: str,
    context_chunks: List[Dict],
    preferred_model: str,
    stream: bool = True
) -> Dict:
    """Route query to appropriate LLM based on complexity and context size"""
    
    # Calculate context size
    context_text = "\n\n".join([chunk['content'] for chunk in context_chunks])
    context_tokens = len(context_text) // 4  # Rough estimate
    
    # Determine best model
    selected_model = select_optimal_model(message, context_tokens, preferred_model)
    
    # Prepare system prompt
    system_prompt = create_system_prompt()
    
    # Prepare user message with context
    user_message = create_rag_prompt(message, context_chunks)
    
    # Generate response
    if selected_model.startswith("claude"):
        return await generate_claude_response(
            system_prompt, user_message, selected_model, stream
        )
    elif selected_model.startswith("gpt") or selected_model.startswith("o"):
        # Handle all OpenAI models (gpt-*, o1-*, o3-*, etc.)
        return await generate_openai_response(
            system_prompt, user_message, selected_model, stream
        )
    else:
        raise ValueError(f"Unknown model: {selected_model}")


def select_optimal_model(query: str, context_tokens: int, preferred_model: str) -> str:
    """Select the best model based on query characteristics"""
    
    # Check for reasoning indicators
    reasoning_keywords = [
        "analysiere", "analyze", "erkläre", "explain", 
        "warum", "why", "strategie", "strategy",
        "vergleiche", "compare", "bewerte", "evaluate"
    ]
    
    needs_reasoning = any(keyword in query.lower() for keyword in reasoning_keywords)
    
    # Model selection logic - July 2025
    if needs_reasoning:
        return "o3"  # Use O3 for complex reasoning
    elif context_tokens > 50000:
        return "gpt-4o"  # GPT-4o handles large contexts well
    elif preferred_model:
        return preferred_model
    else:
        return "claude-sonnet-4-20250514"  # Default to Claude 4 Sonnet


def create_system_prompt() -> str:
    """Create system prompt for the LLM"""
    return """Du bist ein intelligenter Assistent mit Zugriff auf das persönliche Wissensmanagement-System.
    
Deine Aufgaben:
1. Beantworte Fragen präzise basierend auf dem gegebenen Kontext
2. Zitiere relevante Quellen wenn möglich
3. Gib an, wenn Information nicht im Kontext verfügbar ist
4. Strukturiere deine Antworten klar (Listen, Tabellen wenn sinnvoll)
5. Sei hilfsbereit aber präzise

Antworte auf Deutsch, außer der Nutzer fragt auf Englisch."""


def create_rag_prompt(query: str, context_chunks: List[Dict]) -> str:
    """Create RAG-enhanced prompt with context"""
    if not context_chunks:
        return query
    
    prompt = "Kontext aus deiner Wissensdatenbank:\n\n"
    
    for i, chunk in enumerate(context_chunks):
        source_info = ""
        if chunk.get('document'):
            doc = chunk['document']
            source_info = f" (Quelle: {doc.get('document_title', 'Unbekannt')}, {doc.get('created_at', '')})"
        
        if chunk.get('speaker'):
            source_info += f" [Speaker: {chunk['speaker']}]"
            
        prompt += f"[{i+1}] {chunk['content']}{source_info}\n\n"
    
    prompt += f"\nBasierend auf diesem Kontext, beantworte folgende Frage:\n{query}"
    
    return prompt


async def generate_claude_response(
    system_prompt: str,
    user_message: str,
    model: str,
    stream: bool
) -> Dict:
    """Generate response using Claude"""
    
    # Map model names - Updated July 2025
    model_map = {
        "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
        "claude-opus-4-20250514": "claude-opus-4-20250514",
        "claude-3-sonnet-20240229": "claude-3-sonnet-20240229"  # Fallback
    }
    
    actual_model = model_map.get(model, "claude-sonnet-4-20250514")
    
    if stream:
        async def stream_response():
            async with anthropic_client.messages.stream(
                model=actual_model,
                messages=[{"role": "user", "content": user_message}],
                system=system_prompt,
                max_tokens=4000
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
        
        return stream_response()
    else:
        response = await anthropic_client.messages.create(
            model=actual_model,
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
            max_tokens=4000
        )
        
        return {
            "response": response.content[0].text,
            "model_used": actual_model,
            "tokens_used": response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else None
        }


async def generate_openai_response(
    system_prompt: str,
    user_message: str,
    model: str,
    stream: bool
) -> Dict:
    """Generate response using OpenAI"""
    
    # Map model names - Updated July 2025
    model_map = {
        "gpt-4o": "gpt-4o",  # Omni model
        "gpt-4.1": "gpt-4.1",  # Latest GPT-4.1
        "gpt-4.1-mini": "gpt-4.1-mini",  # Fast & cheap quality checker
        "gpt-4.1-nano": "gpt-4.1-nano",  # Cheapest model
        "o3": "o3-2025-04-16",  # O3 reasoning model with specific version
        "o3-pro": "o3-pro",  # Extended reasoning (if available)
        "o3-mini": "o3-mini",  # Lightweight O3
        "o1-preview": "o1-preview",  # O1 preview model
        "o1-mini": "o1-mini",  # Lightweight O1
        "gpt-4-turbo": "gpt-4-turbo",  # Fallback
        "gpt-4": "gpt-4"  # Legacy
    }
    
    actual_model = model_map.get(model, "gpt-4o")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    if stream:
        async def stream_response():
            try:
                stream = await openai_client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    stream=True,
                    max_tokens=4000
                )
            except Exception as e:
                # Fallback to gpt-4o if O3 models are not available
                if "o3" in actual_model.lower():
                    print(f"O3 model {actual_model} not available, falling back to gpt-4o")
                    stream = await openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        stream=True,
                        max_tokens=4000
                    )
                else:
                    raise e
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        return stream_response()
    else:
        try:
            response = await openai_client.chat.completions.create(
                model=actual_model,
                messages=messages,
                max_tokens=4000
            )
        except Exception as e:
            # Fallback to gpt-4o if O3 models are not available
            if "o3" in actual_model.lower():
                print(f"O3 model {actual_model} not available, falling back to gpt-4o")
                response = await openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=4000
                )
            else:
                raise e
        
        return {
            "response": response.choices[0].message.content,
            "model_used": actual_model,
            "tokens_used": response.usage.total_tokens if response.usage else None
        }


def format_sources(context_chunks: List[Dict]) -> List[Dict]:
    """Format source citations for response"""
    sources = []
    
    for chunk in context_chunks:
        source = {
            "content": chunk['content'][:200] + "...",
            "score": chunk.get('similarity', chunk.get('rank', 0))
        }
        
        if chunk.get('document'):
            doc = chunk['document']
            source.update({
                "title": doc.get('document_title'),
                "type": doc.get('source_type'),
                "date": doc.get('created_at')
            })
            
        if chunk.get('speaker'):
            source['speaker'] = chunk['speaker']
            
        sources.append(source)
    
    return sources


@router.get("/models")
async def list_available_models():
    """List available LLM models"""
    return {
        "models": [
            {
                "id": "claude-sonnet-4-20250514",
                "name": "Claude 4 Sonnet",
                "provider": "Anthropic",
                "description": "Latest Claude model - balanced for general queries",
                "context_window": 200000
            },
            {
                "id": "o3",
                "name": "OpenAI O3",
                "provider": "OpenAI",
                "description": "Advanced reasoning model with simulated reasoning",
                "context_window": 200000
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o (Omni)",
                "provider": "OpenAI",
                "description": "Multimodal model - text, vision, and audio",
                "context_window": 128000
            },
            {
                "id": "o3-pro",
                "name": "OpenAI O3 Pro",
                "provider": "OpenAI",
                "description": "Extended reasoning - thinks longer for complex tasks",
                "context_window": 200000
            },
            {
                "id": "gpt-4.1-mini",
                "name": "GPT-4.1 Mini",
                "provider": "OpenAI",
                "description": "Fast and cheap model for quality checking - 1M token context",
                "context_window": 1000000
            }
        ],
        "default": "claude-sonnet-4-20250514"
    }