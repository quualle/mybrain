from fastapi import APIRouter, HTTPException
from typing import List, Optional
import asyncpg
from datetime import datetime
import os

router = APIRouter()

async def get_db_connection():
    """Create a database connection"""
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

@router.get("/")
async def get_documents():
    """Get all documents with metadata"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Fetch all documents
        query = """
            SELECT 
                id,
                title,
                source_type,
                source_url,
                created_at,
                metadata,
                CASE 
                    WHEN full_content IS NOT NULL 
                    THEN LENGTH(full_content)
                    ELSE 0
                END as content_length
            FROM documents
            ORDER BY created_at DESC
        """
        
        rows = await conn.fetch(query)
        
        # Convert to list of dicts
        documents = []
        for row in rows:
            doc = dict(row)
            # Convert datetime to ISO format string
            if doc.get('created_at'):
                doc['created_at'] = doc['created_at'].isoformat()
            documents.append(doc)
        
        return documents
        
    except Exception as e:
        print(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Start a transaction
        async with conn.transaction():
            # Delete chunks first (in case no cascade)
            await conn.execute(
                "DELETE FROM chunks WHERE document_id = $1",
                document_id
            )
            
            # Delete the document
            result = await conn.execute(
                "DELETE FROM documents WHERE id = $1",
                document_id
            )
            
            # Check if document was found and deleted
            if result.split()[-1] == '0':
                raise HTTPException(status_code=404, detail="Document not found")
        
        return {"success": True, "message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()

@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get a single document with its content"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Fetch document with full content
        query = """
            SELECT 
                id,
                title,
                source_type,
                source_url,
                created_at,
                metadata,
                full_content,
                summary
            FROM documents
            WHERE id = $1
        """
        
        row = await conn.fetchrow(query, document_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = dict(row)
        if doc.get('created_at'):
            doc['created_at'] = doc['created_at'].isoformat()
            
        return doc
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()