# app/models/pet.py
from sqlalchemy import Column, BigInteger, String, Date, Text, Boolean, ForeignKey, Enum as SQLAlchemyEnum, DECIMAL
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class Species(str, enum.Enum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RABBIT = "rabbit"
    HAMSTER = "hamster"
    FISH = "fish"
    OTHER = "other"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"

class Pet(BaseModel):
    __tablename__ = "pets"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    species = Column(
        SQLAlchemyEnum(Species, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    breed = Column(String(100))
    gender = Column(
        SQLAlchemyEnum(Gender, values_callable=lambda x: [e.value for e in x]), 
        default=Gender.UNKNOWN
    )
    birth_date = Column(Date)
    weight = Column(DECIMAL(5, 2))
    description = Column(Text)
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    # 關聯
    owner = relationship("User", back_populates="pets")
    posts = relationship("Post", back_populates="pet")
    albums = relationship("Album", back_populates="pet")
    medical_records = relationship("PetMedicalRecord", back_populates="pet")
    vaccinations = relationship("PetVaccination", back_populates="pet")