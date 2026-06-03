from fastapi import APIRouter
from backend.schema.ReceiptsCreate import ReceiptsCreate
from backend.service.ReceiptsService import *
from fastapi import APIRouter
from fastapi import File, UploadFile

router = APIRouter(
    prefix="/api/receipt",
    tags=["receipt"]
)

router.post("/create-receipt")
def create_receipt(receipt: ReceiptsCreate):
    return {
        "message": "Thành công",
        "receipt_id": save_receipt_service(receipt)
    }

@router.post("/upload-image")
async def solve_receipt(file: UploadFile = File(...)):
    contents = await file.read()

    # Xử lý ảnh

    return # Trả về dict sau khi xử lý