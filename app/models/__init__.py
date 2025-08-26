# app/models/__init__.py
from app.models.base import BaseModel, TimestampMixin
from app.models.user import User
from app.models.auth import Role, Permission, UserRole, RolePermission, UserToken, TokenType, TokenBlacklist
from app.models.pet import Pet, Species, Gender
from app.models.post import Post, Visibility
from app.models.album import Album
from app.models.media import Media, MediaType, PostMedia, AlbumMedia
from app.models.merchant import Merchant, BusinessType, MerchantStatus
from app.models.social import Like, Comment, Tag, PostTag
from app.models.medical import (
    PetMedicalRecord, PetVaccination, VeterinaryClinic, 
    Veterinarian, VaccineType, VisitType
)

# 確保所有模型都被導入，這樣 SQLAlchemy 才能正確解析關係
__all__ = [
    # Base
    "BaseModel", "TimestampMixin",
    
    # User & Auth
    "User", "Role", "Permission", "UserRole", "RolePermission", 
    "UserToken", "TokenType", "TokenBlacklist",
    
    # Pet
    "Pet", "Species", "Gender",
    
    # Post & Album
    "Post", "Album", "Visibility",
    
    # Media
    "Media", "MediaType", "PostMedia", "AlbumMedia",
    
    # Merchant
    "Merchant", "BusinessType", "MerchantStatus",
    
    # Social
    "Like", "Comment", "Tag", "PostTag",
    
    # Medical
    "PetMedicalRecord", "PetVaccination", "VeterinaryClinic",
    "Veterinarian", "VaccineType", "VisitType",
]