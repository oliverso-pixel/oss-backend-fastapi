# app/api/v1/endpoints/vaccinations.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test():
    return {"message": "Auth endpoint working"}

