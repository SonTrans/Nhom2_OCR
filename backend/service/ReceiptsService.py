from backend.repository.ReceiptsRepo import *
from backend.schema.ReceiptsCreate import ReceiptsCreate

def save_receipt_service(receipt: ReceiptsCreate):
    receipt_id = create_receipt(receipt.user_id,
                                receipt.category_id,
                                receipt.company_name,
                                receipt.date,
                                receipt.total_amount
                                )
    return receipt_id