from backend.repository.BudgetsRepo import *
from backend.schema.BudgetCreate import BudgetCreate
from datetime import date, timedelta

def map_budget(row):
    return {
        "id": row[0],
        "user_id": row[1],
        "start_date": row[2],
        "end_date": row[3],
        "budget": row[4],
        "total_amount": row[5]
    }

def get_budget_by_user_id_service(user_id):

    budgets = get_all_budgets_by_user_id(user_id)

    return [map_budget(b) for b in budgets]


def get_current_budget_for_user_service(user_id):
    from datetime import date

    today = date.today()
    budget = get_current_budget_by_user_id(user_id, today)
    return map_budget(budget) if budget else None


def add_amount_to_budget_service(user_id, amount, confirmed_at=None):
    from datetime import date, datetime

    if confirmed_at is None:
        confirmed_at = datetime.now()

    if isinstance(confirmed_at, date) and not isinstance(confirmed_at, datetime):
        effective_date = confirmed_at
    else:
        effective_date = confirmed_at.date()

    updated_budgets = update_budget_totals_by_date_range(user_id, amount, effective_date)
    if not updated_budgets:
        raise ValueError("Không tìm thấy budget hiện tại cho người dùng.")

    return [map_budget(b) for b in updated_budgets]


def create_budget_service(budget: BudgetCreate):

    today = date.today()
    end_of_month = get_end_of_month(today)

    budget_id = create_budget_repo(
        user_id=budget.user_id,
        start_date=today,
        end_date=end_of_month,
        budget=budget.budget,
        total_amount=0
    )

    return budget_id

def get_end_of_month(today: date):
    # sang tháng sau ngày 1
    next_month = today.replace(day=28) + timedelta(days=4)
    # quay về ngày cuối tháng
    return next_month - timedelta(days=next_month.day)