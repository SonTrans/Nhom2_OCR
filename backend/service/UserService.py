from backend.repository.UserRepo import *

def create_user_service(username, password):
    return create_user_repo

def login_service(username, password):
    user = get_user_by_username(username)
    if user is None:
        return None
    if user["password"] != password:
        return None

    return user["id"]