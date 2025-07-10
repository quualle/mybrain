#!/usr/bin/env python3
"""
Quick API test for specific queries
"""

import asyncio
import aiohttp
import json
from typing import List, Dict

async def test_query(query: str, conversation_history: List[Dict] = None):
    """Test a single query against the API"""
    
    payload = {
        "message": query,
        "conversation_history": conversation_history or [],
        "stream": False,
        "debug": True,
        "model": "claude-sonnet-4-20250514"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "http://localhost:8000/api/v1/chat/",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                return result
        except Exception as e:
            return {"error": str(e)}

async def main():
    print("=== Quick MyBrain API Test ===\n")
    
    # Test 1: Claude Code Hooks
    print("Test 1: Claude Code Hooks Query")
    print("Query: 'Claude Code Hooks - da gab es doch ein Video zu. Was war das nochmal?'")
    
    result = await test_query("Claude Code Hooks - da gab es doch ein Video zu. Was war das nochmal?")
    
    if 'error' not in result:
        print(f"\nResponse Preview: {result.get('response', '')[:300]}...")
        if result.get('debug_info'):
            print(f"\nDebug Info:")
            print(f"  Strategy: {result['debug_info'].get('routing_strategy')}")
            print(f"  Chunks Found: {result['debug_info'].get('chunks_found')}")
            print(f"  Fuzzy Matches: {result['debug_info'].get('fuzzy_matches')}")
            if result['debug_info'].get('fuzzy_matched_docs'):
                print(f"  Fuzzy Docs: {result['debug_info']['fuzzy_matched_docs']}")
    else:
        print(f"Error: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Careli without name
    print("Test 2: Careli Search without Name")
    print("Query: 'Gibt es ein Gespräch über eine Firma die Pflegekräfte aus Polen vermittelt?'")
    
    result = await test_query("Gibt es ein Gespräch über eine Firma die Pflegekräfte aus Polen vermittelt?")
    
    if 'error' not in result:
        print(f"\nResponse Preview: {result.get('response', '')[:300]}...")
        if result.get('debug_info'):
            print(f"\nDebug Info:")
            print(f"  Strategy: {result['debug_info'].get('routing_strategy')}")
            print(f"  Chunks Found: {result['debug_info'].get('chunks_found')}")
            print(f"  Fuzzy Matches: {result['debug_info'].get('fuzzy_matches')}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())