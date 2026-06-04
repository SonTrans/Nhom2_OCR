from fastapi import APIRouter
from backend.schema.BudgetCreate import BudgetCreate
from backend.service.BudgetsService import *

router = APIRouter(
    prefix="/api/budget",
    tags=["budgets"]
)

@router.get("/get-budgets/{user_id}")
def get_budgets(user_id: int):
    budgets = get_budget_by_user_id_service(user_id)
    return budgets

@router.post("/create-budget")
def create_budget(budget: BudgetCreate):

    budget_id = create_budget_service(budget)

    return {
        "message": "Tạo budget thành công",
        "budget_id": budget_id
    }