#!/usr/bin/env python3
"""
Autonomous Test Suite for MyBrain
Tests various query types and edge cases
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import List, Dict
import asyncpg
from dotenv import load_dotenv

load_dotenv()

class MyBrainTester:
    def __init__(self):
        self.api_url = "http://localhost:8000/api/v1"
        self.results = []
        
    async def test_chat_query(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """Test a single chat query"""
        
        payload = {
            "message": message,
            "conversation_history": conversation_history or [],
            "stream": False,
            "debug": True,
            "model": "claude-sonnet-4-20250514"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/chat/",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "error": f"Status {response.status}",
                        "detail": await response.text()
                    }
    
    async def get_sample_documents(self) -> List[Dict]:
        """Get sample documents from database for testing"""
        
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
        try:
            docs = await conn.fetch("""
                SELECT id, title, source_type, created_at
                FROM documents
                ORDER BY created_at DESC
                LIMIT 10
            """)
            return [dict(doc) for doc in docs]
        finally:
            await conn.close()
    
    async def run_test_suite(self):
        """Run comprehensive test suite"""
        
        print("=== MyBrain Autonomous Test Suite ===\n")
        
        # Get sample documents for reference
        docs = await self.get_sample_documents()
        print(f"Found {len(docs)} documents in database:")
        for doc in docs:
            print(f"  - {doc['title']}")
        print("\n")
        
        # Test cases
        test_cases = [
            # 1. Exact document reference
            {
                "name": "Exact Video Reference",
                "query": "Claude Code Hooks - da gab es doch ein Video zu. Was war das nochmal?",
                "expected": "Should find IndyDevDan video about Claude Code Hooks"
            },
            
            # 2. Fuzzy matching
            {
                "name": "Fuzzy Company Search",
                "query": "Gibt es ein Gespräch über eine Firma die Pflegekräfte aus Polen vermittelt?",
                "expected": "Should find Careli/Sascha Zöller conversation"
            },
            
            # 3. Speaker reference
            {
                "name": "Speaker Search",
                "query": "Was hat Antonio über Anwaltskanzleien gesagt?",
                "expected": "Should find Antonio's comments about law firms"
            },
            
            # 4. Topic similarity
            {
                "name": "Similar Topic Search",
                "query": "Welche Videos gibt es über MCP Server oder Claude Tools?",
                "expected": "Should find both Cole Medlin MCP and IndyDevDan videos"
            },
            
            # 5. Conversation with context loss
            {
                "name": "Multi-turn with Original Question",
                "conversation": [
                    {"role": "user", "content": "Ich möchte mehr über das Careli Gespräch erfahren. Kannst du mir den Kontext nochmal aufbereiten?"},
                    {"role": "assistant", "content": "Ich kann kein Gespräch über Careli finden..."},
                    {"role": "user", "content": "Es ging um Sascha Zöller und Betreuungskräfte"}
                ],
                "query": "Ah ja, genau das meinte ich",
                "expected": "Should remember original question about context"
            },
            
            # 6. Temporal query
            {
                "name": "Recent Documents",
                "query": "Was wurde in den letzten Tagen hinzugefügt?",
                "expected": "Should list recent documents"
            },
            
            # 7. Entity extraction
            {
                "name": "Multiple Entity Search",
                "query": "Das Interview zwischen Marco und Antonio über Synclaro",
                "expected": "Should extract all three entities"
            },
            
            # 8. Typo tolerance
            {
                "name": "Typo Tolerance",
                "query": "Das Video von IndyDavDan über Claud Code Hoks",
                "expected": "Should find despite typos"
            }
        ]
        
        # Run tests
        for i, test in enumerate(test_cases):
            print(f"\n--- Test {i+1}: {test['name']} ---")
            
            if 'conversation' in test:
                # Multi-turn test
                conversation = test['conversation']
                response = await self.test_chat_query(test['query'], conversation)
            else:
                # Single query test
                response = await self.test_chat_query(test['query'])
            
            # Analyze result
            result = {
                "test_name": test['name'],
                "query": test.get('query', 'multi-turn'),
                "expected": test['expected'],
                "success": False,
                "response_preview": "",
                "debug_info": {}
            }
            
            if 'error' in response:
                result['error'] = response['error']
                print(f"❌ ERROR: {response['error']}")
            else:
                result['response_preview'] = response.get('response', '')[:200] + "..."
                result['debug_info'] = response.get('debug_info', {})
                
                # Simple success check
                if response.get('response'):
                    result['success'] = True
                    print(f"✅ SUCCESS")
                else:
                    print(f"❌ FAILED: No response")
                
                # Show debug info
                if result['debug_info']:
                    print(f"Debug Info:")
                    print(f"  - Strategy: {result['debug_info'].get('routing_strategy')}")
                    print(f"  - Chunks: {result['debug_info'].get('chunks_found')}")
                    print(f"  - Fuzzy Matches: {result['debug_info'].get('fuzzy_matches')}")
                    if result['debug_info'].get('fuzzy_matched_docs'):
                        print(f"  - Fuzzy Docs: {result['debug_info']['fuzzy_matched_docs']}")
                
                print(f"Response: {result['response_preview']}")
            
            self.results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Summary
        print("\n\n=== TEST SUMMARY ===")
        success_count = sum(1 for r in self.results if r['success'])
        print(f"Total Tests: {len(self.results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(self.results) - success_count}")
        print(f"Success Rate: {(success_count/len(self.results)*100):.1f}%")
        
        # Detailed failures
        print("\n=== FAILED TESTS ===")
        for result in self.results:
            if not result['success']:
                print(f"\n{result['test_name']}:")
                print(f"  Query: {result['query']}")
                print(f"  Expected: {result['expected']}")
                if 'error' in result:
                    print(f"  Error: {result['error']}")
        
        # Save results
        with open('test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n✅ Results saved to test_results.json")


async def main():
    tester = MyBrainTester()
    await tester.run_test_suite()


if __name__ == "__main__":
    asyncio.run(main())