from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AssignBudget(BaseModel):
    user_id: int
    receipt_total: float
    confirmed_at: Optional[datetime] = None
