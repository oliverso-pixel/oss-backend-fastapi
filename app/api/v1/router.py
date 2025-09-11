# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, social, pets, pet_transfer, posts, albums, media, products, merchants, orders, medical, vaccinations, notifications, admin

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(social.router, prefix="/social", tags=["social"])
router.include_router(pets.router, prefix="/pets", tags=["pets"])
router.include_router(pet_transfer.router, prefix="/pet-transfer", tags=["pet-transfer"])
router.include_router(posts.router, prefix="/posts", tags=["posts"])
router.include_router(albums.router, prefix="/albums", tags=["albums"])
router.include_router(media.router, prefix="/media", tags=["media"])
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(merchants.router, prefix="/merchants", tags=["merchants"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(medical.router, prefix="/medical", tags=["medical"])
router.include_router(vaccinations.router, prefix="/vaccinations", tags=["vaccinations"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])

