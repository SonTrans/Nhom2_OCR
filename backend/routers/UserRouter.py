from fastapi import APIRouter
from backend.schema.UserCreate import UserCreate
from backend.service.UserService import *

router = APIRouter(
    prefix="/api/user",
    tags=["Users"]
)

@router.post("/signup")
def signup(user: UserCreate):
    user_id = create_user_service(user.username, user.password)
    return {
        "message": "Thành công",
        "user_id": user_id
    }

@router.post("/login")
def login(user: UserCreate):
    user_id = login_service(user.username, user.password)
    if user_id is None:
        return {
            "message": "Thất bại",
            "user_id": None
        }
    return {
        "message": "Thành công",
        "user_id": user_id
    }