"""
Knowledge Base API Routes

Knowledge articles with semantic search capabilities.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from asyncpg import Connection

from src.database import get_db_connection
from src.api.dependencies import get_pagination, PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
async def search_knowledge_base(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
    db: Connection = Depends(get_db_connection),
):
    """
    Search knowledge base using full-text search.
    
    For semantic search with embeddings, use the /semantic-search endpoint.
    """
    results = await db.fetch(
        """
        SELECT id, title, content, category, tags, status,
               ts_rank_cd(search_vector, to_tsquery('english', $1)) AS rank
        FROM knowledge_base
        WHERE status = 'published'
          AND search_vector @@ to_tsquery('english', $1)
          AND ($2::text IS NULL OR category = $2)
        ORDER BY rank DESC
        LIMIT $3
        """,
        query,
        category,
        limit,
    )
    
    return {
        "query": query,
        "results": [dict(r) for r in results],
        "count": len(results),
    }


@router.get("/semantic-search")
async def semantic_search(
    query: str = Query(..., description="Search query for semantic matching"),
    limit: int = Query(10, ge=1, le=50),
    db: Connection = Depends(get_db_connection),
):
    """
    Semantic search using vector embeddings.
    
    Requires OpenAI embeddings to be generated for knowledge base articles.
    """
    # Note: In production, you would:
    # 1. Generate embedding for the query using OpenAI
    # 2. Use cosine similarity to find closest articles
    
    # Placeholder - will be implemented with OpenAI integration
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Semantic search requires OpenAI integration (Step 10)",
    )


@router.get("/")
async def list_articles(
    pagination: PaginationParams = Depends(get_pagination),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query("published"),
    db: Connection = Depends(get_db_connection),
):
    """
    List knowledge base articles.
    """
    base_query = "SELECT * FROM knowledge_base WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM knowledge_base WHERE 1=1"
    
    params = []
    param_count = 1
    
    if category:
        base_query += f" AND category = ${param_count}"
        count_query += f" AND category = ${param_count}"
        params.append(category)
        param_count += 1
    
    if status:
        base_query += f" AND status = ${param_count}"
        count_query += f" AND status = ${param_count}"
        params.append(status)
        param_count += 1
    
    base_query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([pagination.page_size, pagination.offset])
    
    articles = await db.fetch(base_query, *params)
    total_count = await db.fetchval(count_query, *params[:-2])
    
    return {
        "articles": [dict(a) for a in articles],
        "total": int(total_count),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/{article_id}")
async def get_article(
    article_id: UUID,
    db: Connection = Depends(get_db_connection),
):
    """
    Get a specific knowledge base article.
    """
    article = await db.fetchrow(
        "SELECT * FROM knowledge_base WHERE id = $1",
        article_id,
    )
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found",
        )
    
    # Increment view count
    await db.execute(
        "UPDATE knowledge_base SET view_count = view_count + 1 WHERE id = $1",
        article_id,
    )
    
    return dict(article)


@router.post("/{article_id}/feedback")
async def submit_article_feedback(
    article_id: UUID,
    helpful: bool = Query(..., description="Was the article helpful?"),
    db: Connection = Depends(get_db_connection),
):
    """
    Submit feedback on a knowledge base article.
    """
    if helpful:
        await db.execute(
            "UPDATE knowledge_base SET helpful_count = helpful_count + 1 WHERE id = $1",
            article_id,
        )
    else:
        await db.execute(
            "UPDATE knowledge_base SET not_helpful_count = not_helpful_count + 1 WHERE id = $1",
            article_id,
        )
    
    return {"status": "recorded", "helpful": helpful}
