# app/api/v1/endpoints/posts.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test():
    return {"message": "Auth endpoint working"}

