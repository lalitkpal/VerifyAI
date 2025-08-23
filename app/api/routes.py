from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
async def get_users():
    return {"message": "List of users"}

@router.post("/users")
async def create_user(user: dict):
    return {"message": "User created", "user": user}

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"message": "User details", "user_id": user_id}

@router.put("/users/{user_id}")
async def update_user(user_id: int, user: dict):
    return {"message": "User updated", "user_id": user_id, "user": user}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    return {"message": "User deleted", "user_id": user_id}