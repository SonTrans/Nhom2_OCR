from fastapi import APIRouter, File, HTTPException, UploadFile
from backend.schema.ReceiptsCreate import ReceiptsCreate
from backend.schema.AssignBudget import AssignBudget
from backend.service.ReceiptsService import *
from backend.service.BudgetsService import add_amount_to_budget_service
from model.Tesseract import Tesseract
from model.vlm_model import extract_receipt_fields


def _is_ocr_error(text: str) -> bool:
    error_signals = [
        "Loi he thong Tesseract:",
        "Loi:",
        "Error:",
        "Could not find tesseract",
        "not installed or it's not in your PATH",
    ]
    if not isinstance(text, str):
        return False
    cleaned = text.strip().lower()
    return any(signal.lower() in cleaned for signal in error_signals)

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

    tesseract = Tesseract()
    raw_text = tesseract.extract_text(contents)
    is_error = _is_ocr_error(raw_text)
    receipt_data = {"company": None, "date": None, "total": None} if is_error else extract_receipt_fields(raw_text)

    return {
        "message": "Upload thành công",
        "raw_text": raw_text,
        "receipt": receipt_data,
        "ocr_error": raw_text if is_error else None
    }


@router.post("/assign-budget")
async def assign_receipt_to_budget(payload: AssignBudget):
    try:
        budgets = add_amount_to_budget_service(payload.user_id, payload.receipt_total, payload.confirmed_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "Budget đã được cập nhật",
        "budgets": budgets,
        "budget": budgets[0] if budgets else None
    }