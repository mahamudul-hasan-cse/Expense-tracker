from pydantic import BaseModel


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
