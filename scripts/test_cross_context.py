#!/usr/bin/env python3
"""
Test Cross-Context Reasoning Capabilities
Tests MyBrain's ability to find connections between different documents
"""

import asyncio
import aiohttp
import json
from typing import List, Dict
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()


class CrossContextTester:
    def __init__(self):
        self.api_url = "http://localhost:8000/api/v1"
        self.database_url = os.getenv("DATABASE_URL")
        self.results = []
        
    async def test_query(self, query: str, conversation_history: List[Dict] = None):
        """Test a single query"""
        
        payload = {
            "message": query,
            "conversation_history": conversation_history or [],
            "stream": False,
            "debug": True,
            "model": "gpt-4.1-mini"  # Fast for testing
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/chat/",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return await response.json()
            except Exception as e:
                return {"error": str(e)}
    
    async def analyze_database_for_relationships(self):
        """Analyze database to find potential relationships"""
        
        conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
        try:
            # Get all documents
            docs = await conn.fetch("""
                SELECT id, title, summary, source_type, created_at
                FROM documents
                ORDER BY created_at DESC
            """)
            
            print(f"\n📚 Found {len(docs)} documents in database:")
            for doc in docs:
                print(f"  - {doc['title']} ({doc['source_type']})")
            
            # Find documents with shared people
            shared_people = await conn.fetch("""
                SELECT 
                    c1.speaker,
                    d1.title as doc1_title,
                    d2.title as doc2_title
                FROM chunks c1
                JOIN documents d1 ON d1.id = c1.document_id
                JOIN chunks c2 ON c2.speaker = c1.speaker
                JOIN documents d2 ON d2.id = c2.document_id
                WHERE c1.speaker IS NOT NULL
                AND c1.document_id != c2.document_id
                GROUP BY c1.speaker, d1.title, d2.title
                ORDER BY c1.speaker
            """)
            
            if shared_people:
                print(f"\n👥 Documents with shared people:")
                current_person = None
                for record in shared_people:
                    if record['speaker'] != current_person:
                        current_person = record['speaker']
                        print(f"\n  {current_person} appears in:")
                    print(f"    - {record['doc1_title']} ↔ {record['doc2_title']}")
            
            # Find technology overlaps
            tech_terms = ['api', 'server', 'automation', 'integration', 'tool', 'system']
            print(f"\n🔧 Technology term overlaps:")
            
            for term in tech_terms:
                docs_with_term = await conn.fetch("""
                    SELECT DISTINCT d.title
                    FROM documents d
                    JOIN chunks c ON c.document_id = d.id
                    WHERE LOWER(c.content) LIKE $1
                """, f'%{term}%')
                
                if len(docs_with_term) > 1:
                    print(f"  '{term}' found in: {', '.join([d['title'] for d in docs_with_term])}")
            
            return [dict(doc) for doc in docs]
            
        finally:
            await conn.close()
    
    async def run_cross_context_tests(self):
        """Run comprehensive cross-context tests"""
        
        print("=== Cross-Context Reasoning Tests ===\n")
        
        # First analyze what's in the database
        docs = await self.analyze_database_for_relationships()
        
        print("\n\n=== Running Test Queries ===")
        
        test_cases = [
            # Test 1: Direct cross-context question
            {
                "name": "Direct Cross-Context Connection",
                "query": "Könnte man die Erkenntnisse aus dem Cole Medlin MCP Server Video irgendwie in Saschas Bedürfnislandschaft einbringen?",
                "expected": "Should connect MCP server capabilities to Sascha's automation needs"
            },
            
            # Test 2: Implicit relationship search
            {
                "name": "Implicit Technology Match",
                "query": "Welche der besprochenen Technologien könnten bei der Gewerbeanmeldungs-Automatisierung helfen?",
                "expected": "Should connect various tech discussions to automation needs"
            },
            
            # Test 3: Person-based connections
            {
                "name": "Person-Based Cross-Reference", 
                "query": "Was waren die wichtigsten Themen in allen Gesprächen mit Sascha?",
                "expected": "Should aggregate all Sascha-related content"
            },
            
            # Test 4: Solution mapping
            {
                "name": "Problem-Solution Mapping",
                "query": "Für welche der in den Gesprächen erwähnten Probleme gibt es bereits Lösungsansätze in anderen Videos?",
                "expected": "Should map problems to solutions across documents"
            },
            
            # Test 5: Multi-step reasoning
            {
                "name": "Multi-Step Cross-Context",
                "conversation": [
                    {"role": "user", "content": "Was waren die Hauptpunkte im letzten Gespräch mit Sascha?"},
                    {"role": "assistant", "content": "Die Hauptpunkte waren: Gewerbeanmeldung automatisieren, Guided Browser-Ansatz, etc."},
                    {"role": "user", "content": "Und was war nochmal das Hauptthema im Cole Medlin Video?"}
                ],
                "query": "Wie könnten diese beiden Themen zusammenhängen?",
                "expected": "Should connect insights from both contexts"
            },
            
            # Test 6: Temporal evolution
            {
                "name": "Topic Evolution Tracking",
                "query": "Wie hat sich das Thema Automatisierung über die verschiedenen Gespräche entwickelt?",
                "expected": "Should track automation topic across time"
            },
            
            # Test 7: Entity network
            {
                "name": "Entity Relationship Network",
                "query": "Welche Verbindungen gibt es zwischen den verschiedenen Personen und Firmen in den Dokumenten?",
                "expected": "Should map relationships between people and companies"
            },
            
            # Test 8: Comprehensive integration
            {
                "name": "Full Integration Question",
                "query": "Basierend auf allen verfügbaren Informationen: Welche konkreten technischen Lösungen würden Saschas Anforderungen am besten erfüllen?",
                "expected": "Should synthesize across all relevant documents"
            }
        ]
        
        # Run tests
        for i, test in enumerate(test_cases):
            print(f"\n\n--- Test {i+1}: {test['name']} ---")
            print(f"Query: {test['query']}")
            print(f"Expected: {test['expected']}")
            
            if 'conversation' in test:
                response = await self.test_query(test['query'], test['conversation'])
            else:
                response = await self.test_query(test['query'])
            
            # Analyze results
            if 'error' in response:
                print(f"\n❌ ERROR: {response['error']}")
                self.results.append({
                    "test": test['name'],
                    "success": False,
                    "error": response['error']
                })
            else:
                print(f"\n✅ Response received")
                
                # Check debug info
                debug = response.get('debug_info', {})
                if debug:
                    print(f"\n📊 Debug Info:")
                    print(f"  - Strategy: {debug.get('routing_strategy')}")
                    print(f"  - Chunks: {debug.get('chunks_found')}")
                    print(f"  - Quality Score: {debug.get('quality_score')}")
                    
                    if debug.get('cross_context_insights'):
                        print(f"\n🔗 Cross-Context Insights Found:")
                        for insight in debug['cross_context_insights']:
                            print(f"    - {insight}")
                    
                    if debug.get('related_contexts'):
                        print(f"\n📄 Related Documents:")
                        for ctx in debug['related_contexts']:
                            print(f"    - {ctx.get('title')}")
                
                # Show response preview
                response_text = response.get('response', '')
                print(f"\n💬 Response Preview:")
                print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
                
                # Simple success check
                success = bool(response_text) and (
                    'cross_context_insights' in debug or
                    any(keyword in response_text.lower() for keyword in ['verbindung', 'zusammenhang', 'beide', 'könnten'])
                )
                
                self.results.append({
                    "test": test['name'],
                    "success": success,
                    "has_cross_context": 'cross_context_insights' in debug,
                    "quality_score": debug.get('quality_score', 0)
                })
            
            await asyncio.sleep(1)  # Rate limiting
        
        # Summary
        print("\n\n=== TEST SUMMARY ===")
        successful = sum(1 for r in self.results if r['success'])
        cross_context_found = sum(1 for r in self.results if r.get('has_cross_context'))
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Successful: {successful} ({successful/len(self.results)*100:.1f}%)")
        print(f"With Cross-Context Insights: {cross_context_found}")
        
        print("\n📈 Quality Scores:")
        for result in self.results:
            if 'quality_score' in result:
                print(f"  - {result['test']}: {result.get('quality_score', 0):.2f}")
        
        # Save results
        with open('cross_context_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print("\n✅ Results saved to cross_context_test_results.json")


async def main():
    tester = CrossContextTester()
    await tester.run_cross_context_tests()


if __name__ == "__main__":
    asyncio.run(main())