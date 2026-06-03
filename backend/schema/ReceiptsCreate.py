from pydantic import BaseModel
from datetime import date
from typing import Optional

class ReceiptsCreate(BaseModel):
    user_id: int
    category_id: Optional[int] = None
    company_name: Optional[str] = None
    receipt_date: Optional[date] = None
    total_amount: Optional[float] = None