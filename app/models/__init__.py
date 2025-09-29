# app/models/__init__.py
from app.models.base import BaseModel, TimestampMixin
from app.models.user import User, PrivacyLevel
from app.models.auth import (
    Role, Permission, UserRole, RolePermission, 
    UserToken, TokenType, TokenBlacklist
)
from app.models.pet import Pet, Species, Gender
from app.models.pet_transfer import TransferStatus, TransferType, PetTransferHistory
from app.models.post import Post, Visibility
from app.models.album import Album
from app.models.media import Media, MediaType, PostMedia, AlbumMedia
from app.models.merchant import Merchant, BusinessType, MerchantStatus
from app.models.social import (
    Friendship, FriendshipStatus, Follow, Like, Comment, 
    Tag, PostTag, ChatRoom, ChatRoomMember, ChatMessage, 
    Notification
)
from app.models.medical import (
    PetMedicalRecord, PetVaccination, VeterinaryClinic, 
    Veterinarian, VaccineType, VisitType
)

# 確保所有模型都被導入，這樣 SQLAlchemy 才能正確解析關係
__all__ = [
    # Base
    "BaseModel", "TimestampMixin",
    
    # User & Auth
    "User", "PrivacyLevel", "Role", "Permission", "UserRole", 
    "RolePermission", "UserToken", "TokenType", "TokenBlacklist",
    
    # Pet
    "Pet", "Species", "Gender",

    # pet_transfer
    "TransferStatus", "TransferType", "PetTransferHistory",
    
    # Post & Album
    "Post", "Album", "Visibility",
    
    # Media
    "Media", "MediaType", "PostMedia", "AlbumMedia",
    
    # Merchant
    "Merchant", "BusinessType", "MerchantStatus",
    
    # Social
    "Friendship", "FriendshipStatus", "Follow", "Like", 
    "Comment", "Tag", "PostTag", "ChatRoom", "ChatRoomMember", 
    "ChatMessage", "Notification",
    
    # Medical
    "PetMedicalRecord", "PetVaccination", "VeterinaryClinic",
    "Veterinarian", "VaccineType", "VisitType",
]

