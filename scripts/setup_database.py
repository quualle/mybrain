#!/usr/bin/env python3
"""
Database setup script for MyBrain
Runs all migrations to set up Supabase with pgvector
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)


async def run_migrations():
    """Run all SQL migrations in order"""
    
    # Connect to database
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Get all migration files
        migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            print(f"\nRunning migration: {migration_file.name}")
            
            # Read and execute migration
            with open(migration_file, 'r') as f:
                sql = f.read()
                
            # Special handling for function definitions
            if '$$' in sql:
                # Execute the entire SQL file as one statement for files with functions
                try:
                    await conn.execute(sql)
                    print(f"  ✓ Executed entire migration file")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"  ⚠ Skipped (already exists)")
                    else:
                        print(f"  ✗ Error: {e}")
                        raise
            else:
                # Split by semicolons for regular statements
                statements = [s.strip() for s in sql.split(';') if s.strip()]
                
                for statement in statements:
                    try:
                        await conn.execute(statement)
                        print(f"  ✓ Executed: {statement[:50]}...")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"  ⚠ Skipped (already exists): {statement[:50]}...")
                        else:
                            print(f"  ✗ Error: {e}")
                            raise
        
        # Verify setup
        print("\nVerifying database setup...")
        
        # Check if vector extension is installed
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )
        if result > 0:
            print("  ✓ Vector extension installed")
        else:
            print("  ✗ Vector extension NOT installed")
            
        # Check tables
        tables = await conn.fetch(
            """
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('documents', 'chunks', 'colbert_tokens', 'conversations')
            ORDER BY tablename
            """
        )
        
        print(f"  ✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"    - {table['tablename']}")
            
        # Check functions
        functions = await conn.fetch(
            """
            SELECT routine_name FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            AND routine_name IN ('hybrid_search', 'get_document_context', 'search_by_speaker')
            """
        )
        
        print(f"  ✓ Created {len(functions)} search functions:")
        for func in functions:
            print(f"    - {func['routine_name']}")
        
        print("\n✅ Database setup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        raise
    finally:
        await conn.close()


async def test_connection():
    """Test basic database operations"""
    print("\nTesting database connection...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Test vector operations
        result = await conn.fetchval(
            "SELECT '[1,2,3]'::vector <=> '[3,2,1]'::vector as distance"
        )
        print(f"  ✓ Vector distance calculation works: {result}")
        
        # Test inserting a document
        doc_id = await conn.fetchval(
            """
            INSERT INTO documents (title, source_type, metadata) 
            VALUES ('Test Document', 'text', '{"test": true}'::jsonb)
            RETURNING id
            """
        )
        print(f"  ✓ Can insert documents: {doc_id}")
        
        # Clean up test data
        await conn.execute("DELETE FROM documents WHERE metadata->>'test' = 'true'")
        print("  ✓ Cleaned up test data")
        
    finally:
        await conn.close()


async def main():
    """Main setup function"""
    print("MyBrain Database Setup")
    print("=" * 50)
    
    await run_migrations()
    await test_connection()
    
    print("\n🎉 Database is ready for use!")
    print("\nNext steps:")
    print("1. Start the backend: uvicorn backend.main:app --reload")
    print("2. Start the frontend: npm run dev")


if __name__ == "__main__":
    asyncio.run(main())