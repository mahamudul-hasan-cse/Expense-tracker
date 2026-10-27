import math

from sqlalchemy.orm import Query

from app.schemas.pagination import PaginationInfo


def paginate(query: Query, page: int, limit: int) -> tuple[list, PaginationInfo]:
    """Apply page/limit to an ordered query and describe the result."""
    total_items = query.order_by(None).count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return items, PaginationInfo(
        page=page,
        limit=limit,
        total_items=total_items,
        total_pages=math.ceil(total_items / limit) if total_items > 0 else 1,
    )
