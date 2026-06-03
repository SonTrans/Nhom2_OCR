from pydantic import BaseModel
from datetime import date
from typing import Optional

class BudgetCreate(BaseModel):
    user_id: int
    budget: float
    total_amount: Optional[float] = 0