class Receipts:
    def __init__(
        self,
        id=None,
        user_id=None,
        category_id=None,
        company_name=None,
        receipt_date=None,
        total_amount=None
    ):
        self.id = id
        self.user_id = user_id
        self.category_id = category_id
        self.company_name = company_name
        self.receipt_date = receipt_date
        self.total_amount = total_amount

    def __str__(self):
        return (
            f"Receipt(id={self.id}, "
            f"user_id={self.user_id}, "
            f"category_id={self.category_id}, "
            f"company_name={self.company_name}, "
            f"receipt_date={self.receipt_date}, "
            f"total_amount={self.total_amount})"
        )