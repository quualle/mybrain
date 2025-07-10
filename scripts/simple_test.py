#!/usr/bin/env python3
"""
Simple synchronous test for cross-context reasoning
"""

import requests
import json

def test_query(query, conversation_history=None):
    """Test a query against the API"""
    
    payload = {
        "message": query,
        "conversation_history": conversation_history or [],
        "stream": False,
        "debug": True,
        "model": "gpt-4.1-mini"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/chat/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== Simple Cross-Context Test ===\n")
    
    # Test 1: The exact query from the user's test
    print("Test 1: Cross-Context Query")
    print("Query: 'Könnte man die Erkenntnisse aus dem Cole Medlin MCP Server irgendwie in Saschas Bedürfnislandschaft einbringen?'")
    
    result = test_query(
        "Könnte man die Erkenntnisse aus dem Cole Medlin MCP Server irgendwie in Saschas Bedürfnislandschaft einbringen?"
    )
    
    if 'error' not in result:
        print(f"\n✅ Response received")
        print(f"Response Preview: {result.get('response', '')[:500]}...")
        
        if result.get('debug_info'):
            debug = result['debug_info']
            print(f"\nDebug Info:")
            print(f"  Strategy: {debug.get('routing_strategy')}")
            print(f"  Chunks Found: {debug.get('chunks_found')}")
            print(f"  Quality Score: {debug.get('quality_score')}")
            
            if debug.get('cross_context_insights'):
                print(f"\n🔗 Cross-Context Insights:")
                for insight in debug['cross_context_insights']:
                    print(f"  - {insight}")
            
            if debug.get('related_contexts'):
                print(f"\n📄 Related Documents:")
                for ctx in debug['related_contexts']:
                    print(f"  - {ctx.get('title')}")
    else:
        print(f"❌ Error: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Multi-turn conversation
    print("Test 2: Multi-turn Conversation Test")
    
    conversation = [
        {"role": "user", "content": "Was waren die Hauptpunkte im letzten Gespräch mit Sascha?"},
        {"role": "assistant", "content": "Die Hauptpunkte waren: Gewerbeanmeldung automatisieren, Guided Browser-Ansatz, rechtliche Sicherheit, etc."},
        {"role": "user", "content": "Und was war das Hauptthema im Cole Medlin Video?"}
    ]
    
    result = test_query(
        "Wie könnten diese beiden Themen zusammenhängen?",
        conversation_history=conversation
    )
    
    if 'error' not in result:
        print(f"\n✅ Response received") 
        print(f"Response Preview: {result.get('response', '')[:500]}...")
        
        if result.get('debug_info', {}).get('cross_context_insights'):
            print(f"\n🔗 Found cross-context connections!")
    else:
        print(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    main()