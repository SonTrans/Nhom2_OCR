class Budgets:
    def __init__(self, id=None, start_date=None, end_date=None, budget=None):
        self.id = id
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget

    def __str__(self):
        return (
            f"Budget(id={self.id}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}, "
            f"budget={self.budget})"
        )