#!/usr/bin/env python3
"""Fix model names to use actual available models"""

import os
import re

def fix_chat_models():
    """Replace non-existent model names with actual ones"""
    
    chat_file = "backend/api/chat.py"
    
    # Read the file
    with open(chat_file, 'r') as f:
        content = f.read()
    
    # Model replacements
    replacements = {
        '"claude-sonnet-4.0"': '"claude-3-sonnet-20240229"',
        "'claude-sonnet-4.0'": "'claude-3-sonnet-20240229'",
        '"gpt-o3"': '"gpt-4"',
        "'gpt-o3'": "'gpt-4'",
        '"gpt-4.1-turbo"': '"gpt-4-turbo-preview"',
        "'gpt-4.1-turbo'": "'gpt-4-turbo-preview'",
        '"gpt-4.1"': '"gpt-4-turbo-preview"',
        "'gpt-4.1'": "'gpt-4-turbo-preview'"
    }
    
    # Apply replacements
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write back
    with open(chat_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed model names in chat.py")
    
    # Also fix the frontend
    frontend_files = [
        "frontend/lib/hooks/useChat.ts",
        "frontend/components/Chat.tsx"
    ]
    
    for file in frontend_files:
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read()
            
            content = content.replace("claude-sonnet-4.0", "claude-3-sonnet-20240229")
            
            with open(file, 'w') as f:
                f.write(content)
            
            print(f"✅ Fixed model names in {file}")

if __name__ == "__main__":
    fix_chat_models()
    print("\n✅ All model names fixed! The chat should work now.")