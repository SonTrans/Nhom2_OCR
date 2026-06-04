from fastapi import APIRouter, File, UploadFile
from backend.schema.ReceiptsCreate import ReceiptsCreate
from backend.service.ReceiptsService import *
from model.Tesseract import Tesseract

router = APIRouter(
    prefix="/api/receipt",
    tags=["receipt"]
)

@router.post("/create-receipt")
def create_receipt(receipt: ReceiptsCreate):
    return {
        "message": "Thành công",
        "receipt_id": save_receipt_service(receipt)
    }

@router.post("/upload-image")
async def solve_receipt(file: UploadFile = File(...)):
    contents = await file.read()

    # Xử lý ảnh
    # tesseract = Tesseract()
    # raw_text = tesseract.extract_text(contents)
    raw_text = "123"

    return {
        "message": "Upload thành công",
        "raw_text": raw_text
    }