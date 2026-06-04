from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from backend.routers.UserRouter import router as user_router
from backend.routers.ReceiptsRouter import router as receipts_router
from backend.routers.BudgetsRouter import router as budgets_router

app = FastAPI()

frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/static/login_page.html")

app.include_router(user_router)
app.include_router(receipts_router)
app.include_router(budgets_router)