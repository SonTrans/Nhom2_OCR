from fastapi import FastAPI
from backend.routers.UserRouter import router as user_router

app = FastAPI()

app.include_router(user_router)