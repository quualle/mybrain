#!/usr/bin/env python3
"""
Check if MyBrain is properly set up
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

def check_env():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        "DATABASE_URL",
        "SUPABASE_URL", 
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HUGGINGFACE_TOKEN",
        "UPSTASH_REDIS_URL",
        "UPSTASH_REDIS_TOKEN"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            print(f"  ❌ {var} is missing")
        else:
            print(f"  ✅ {var} is set")
    
    return len(missing) == 0


def check_imports():
    """Check if all required packages can be imported"""
    print("\n🔍 Checking Python packages...")
    
    packages = [
        ("fastapi", "FastAPI"),
        ("openai", "OpenAI Client"),
        ("anthropic", "Anthropic Client"),
        ("asyncpg", "PostgreSQL Async"),
        ("transformers", "HuggingFace Transformers"),
        ("yt_dlp", "YouTube Downloader"),
        ("redis", "Redis Client")
    ]
    
    all_good = True
    for package, name in packages:
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - run: pip install -r requirements.txt")
            all_good = False
    
    return all_good


def check_files():
    """Check if all important files exist"""
    print("\n🔍 Checking project files...")
    
    files = [
        ".env",
        "requirements.txt",
        "package.json",
        "backend/main.py",
        "app/page.tsx",
        "scripts/setup_database.py"
    ]
    
    all_exist = True
    for file in files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} is missing")
            all_exist = False
    
    return all_exist


def main():
    print("🧠 MyBrain Setup Checker")
    print("=" * 40)
    
    # Load .env if exists
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    env_ok = check_env()
    imports_ok = check_imports()
    files_ok = check_files()
    
    print("\n" + "=" * 40)
    
    if env_ok and imports_ok and files_ok:
        print("✅ Everything looks good! You're ready to start MyBrain.")
        print("\nNext step: Run ./scripts/setup_database.py")
    else:
        print("❌ Some issues found. Please fix them before starting.")
        if not env_ok:
            print("\n1. Make sure .env file exists with all credentials")
        if not imports_ok:
            print("\n2. Run: pip install -r requirements.txt")
        if not files_ok:
            print("\n3. Make sure you're in the project root directory")


if __name__ == "__main__":
    main()