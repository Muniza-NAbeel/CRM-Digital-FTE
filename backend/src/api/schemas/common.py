"""
Common Pydantic schemas.
"""

from typing import Generic, TypeVar, List, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class BaseResponse(BaseModel):
    """
    Base response model.
    """
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Generic paginated response.
    """
    items: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        return self.page > 1
