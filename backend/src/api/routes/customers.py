"""
Customers API Routes

Endpoints for customer management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from asyncpg import Connection

from src.database import get_db_connection
from src.api.dependencies import get_pagination, PaginationParams
from src.api.schemas.customers import (
    CustomerResponse,
    CustomerCreate,
    CustomerUpdate,
    CustomerListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=CustomerListResponse)
async def list_customers(
    pagination: PaginationParams = Depends(get_pagination),
    search: Optional[str] = Query(None, description="Search by name or email"),
    tier: Optional[str] = Query(None, description="Filter by customer tier"),
    db: Connection = Depends(get_db_connection),
):
    """
    List all customers with pagination and optional filters.
    """
    # Build query
    base_query = "SELECT * FROM customers WHERE is_active = TRUE"
    count_query = "SELECT COUNT(*) FROM customers WHERE is_active = TRUE"
    
    params = []
    param_count = 1
    
    if search:
        base_query += f" AND (full_name ILIKE ${param_count} OR email ILIKE ${param_count})"
        count_query += f" AND (full_name ILIKE ${param_count} OR email ILIKE ${param_count})"
        params.append(f"%{search}%")
        param_count += 1
    
    if tier:
        base_query += f" AND customer_tier = ${param_count}"
        count_query += f" AND customer_tier = ${param_count}"
        params.append(tier)
        param_count += 1
    
    # Add pagination
    base_query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([pagination.page_size, pagination.offset])
    
    # Execute queries
    customers = await db.fetch(base_query, *params)
    total_count = await db.fetchval(count_query, *params[:-2])
    
    return CustomerListResponse(
        customers=[CustomerResponse.model_validate(c) for c in customers],
        total=int(total_count),
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: Connection = Depends(get_db_connection),
):
    """
    Get a specific customer by ID.
    """
    customer = await db.fetchrow(
        "SELECT * FROM customers WHERE id = $1",
        customer_id,
    )
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    
    return CustomerResponse.model_validate(customer)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: Connection = Depends(get_db_connection),
):
    """
    Create a new customer.
    """
    customer = await db.fetchrow(
        """
        INSERT INTO customers (
            email, phone, full_name, company_name,
            customer_tier, preferred_channel, preferred_language,
            metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        customer_data.email,
        customer_data.phone,
        customer_data.full_name,
        customer_data.company_name,
        customer_data.customer_tier or "standard",
        customer_data.preferred_channel or "web_form",
        customer_data.preferred_language or "en",
        customer_data.metadata or {},
    )
    
    logger.info(f"Customer created: {customer['id']}")
    
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: Connection = Depends(get_db_connection),
):
    """
    Update an existing customer.
    """
    # Build update query dynamically
    updates = []
    params = []
    param_count = 1
    
    for field, value in customer_data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ${param_count}")
        params.append(value)
        param_count += 1
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    params.append(customer_id)
    
    query = f"""
    UPDATE customers
    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
    WHERE id = ${param_count}
    RETURNING *
    """
    
    customer = await db.fetchrow(query, *params)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    
    logger.info(f"Customer updated: {customer_id}")
    
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    db: Connection = Depends(get_db_connection),
):
    """
    Delete a customer (soft delete - sets is_active = FALSE).
    """
    result = await db.execute(
        "UPDATE customers SET is_active = FALSE WHERE id = $1",
        customer_id,
    )
    
    if result == "UPDATE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    
    logger.info(f"Customer deleted: {customer_id}")
