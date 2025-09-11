# app/schemas/pet.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.models.pet import Species, Gender

class PetBase(BaseSchema):
    """寵物基礎 Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    species: Species
    breed: Optional[str] = Field(None, max_length=100)
    gender: Gender = Gender.UNKNOWN
    birth_date: Optional[date] = None
    weight: Optional[float] = Field(None, ge=0, le=500)  # 0-500 公斤
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    
    @field_validator('birth_date')
    def validate_birth_date(cls, v):
        if v and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v
    
    @field_validator('weight')
    def validate_weight(cls, v):
        if v is not None and v < 0:
            raise ValueError('Weight must be positive')
        return v

class PetCreate(PetBase):
    """創建寵物 Schema"""
    pass

class PetUpdate(BaseSchema):
    """更新寵物 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    birth_date: Optional[date] = None
    weight: Optional[float] = Field(None, ge=0, le=500)
    description: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None

class PetInDB(PetBase, TimestampSchema):
    """資料庫中的寵物 Schema"""
    id: int
    user_id: int
    is_active: bool
    age_years: Optional[float] = None
    age_months: Optional[int] = None

class PetResponse(PetInDB):
    """寵物響應 Schema"""
    owner_username: Optional[str] = None
    
    @property
    def age_display(self) -> str:
        """顯示年齡"""
        if self.birth_date:
            today = date.today()
            age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            if age >= 1:
                return f"{age} 歲"
            else:
                months = (today.year - self.birth_date.year) * 12 + today.month - self.birth_date.month
                return f"{months} 個月"
        return "未知"

class PetListResponse(BaseSchema):
    """寵物列表響應"""
    pets: List[PetResponse]
    total: int

class PetStatistics(BaseSchema):
    """寵物統計資料"""
    total_pets: int
    active_pets: int
    species_distribution: dict
    avg_age_years: Optional[float]
    total_posts: int
    total_albums: int
    last_activity: Optional[datetime]

