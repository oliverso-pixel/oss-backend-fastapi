# app/models/medical.py
from sqlalchemy import Column, BigInteger, Integer, String, Date, DateTime, Text, Boolean, ForeignKey, Enum as SQLAlchemyEnum, JSON, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
from app.core.database import Base
import enum

class VisitType(str, enum.Enum):
    ROUTINE_CHECKUP = "routine_checkup"
    VACCINATION = "vaccination"
    ILLNESS = "illness"
    INJURY = "injury"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    OTHER = "other"

class MedicalSpecies(str, enum.Enum):
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    OTHER = "other"

class MedicalRecordPermissionStatus(str, enum.Enum):
    PENDING = "pending"
    GRANTED = "granted"
    REJECTED = "rejected"
    REVOKED = "revoked"

class PetMedicalRecord(BaseModel):
    __tablename__ = "pet_medical_records"
    
    id = Column(BigInteger, primary_key=True, index=True)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    clinic_id = Column(BigInteger, ForeignKey("veterinary_clinics.id", ondelete="SET NULL"))
    veterinarian_id = Column(BigInteger, ForeignKey("veterinarians.id", ondelete="SET NULL"))
    visit_date = Column(Date, nullable=False)
    visit_type = Column(
        SQLAlchemyEnum(VisitType, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    chief_complaint = Column(Text)
    symptoms = Column(Text)
    diagnosis = Column(Text)
    treatment = Column(Text)
    prescription = Column(JSON)
    weight = Column(DECIMAL(5, 2))
    temperature = Column(DECIMAL(4, 1))
    heart_rate = Column(Integer)
    respiratory_rate = Column(Integer)
    notes = Column(Text)
    follow_up_date = Column(Date)
    attachments = Column(JSON)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    pet = relationship("Pet", back_populates="medical_records")
    clinic = relationship("VeterinaryClinic")
    vaccinations = relationship("PetVaccination", back_populates="medical_record")

class PetVaccination(BaseModel):
    __tablename__ = "pet_vaccinations"
    
    id = Column(BigInteger, primary_key=True, index=True)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    vaccine_type_id = Column(Integer, ForeignKey("vaccine_types.id"), nullable=False)
    medical_record_id = Column(BigInteger, ForeignKey("pet_medical_records.id", ondelete="SET NULL"))
    vaccination_date = Column(Date, nullable=False)
    batch_number = Column(String(100))
    manufacturer = Column(String(100))
    clinic_id = Column(BigInteger, ForeignKey("veterinary_clinics.id", ondelete="SET NULL"))
    veterinarian_id = Column(BigInteger, ForeignKey("veterinarians.id", ondelete="SET NULL"))
    next_due_date = Column(Date)
    notes = Column(Text)
    certificate_no = Column(String(100))
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    pet = relationship("Pet", back_populates="vaccinations")
    medical_record = relationship("PetMedicalRecord", back_populates="vaccinations")
    vaccine_type = relationship("VaccineType")

class VeterinaryClinic(BaseModel):
    __tablename__ = "veterinary_clinics"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    license_no = Column(String(100))
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(JSON)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    is_verified = Column(Boolean, default=False)

class Veterinarian(BaseModel):
    __tablename__ = "veterinarians"
    
    id = Column(BigInteger, primary_key=True, index=True)
    clinic_id = Column(BigInteger, ForeignKey("veterinary_clinics.id", ondelete="SET NULL"))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    name = Column(String(100), nullable=False)
    license_no = Column(String(100), unique=True)
    specialization = Column(String(200))
    phone = Column(String(20))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)

    user = relationship("User")

class VaccineType(Base):
    __tablename__ = "vaccine_types"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    species = Column(
        SQLAlchemyEnum(MedicalSpecies, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    name = Column(String(100), nullable=False)
    abbreviation = Column(String(20))
    description = Column(Text)
    recommended_age_weeks = Column(Integer)
    booster_interval_months = Column(Integer)
    is_core = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class MedicalRecordPermission(BaseModel):
    """病歷存取權限表"""
    __tablename__ = "medical_record_permissions"

    id = Column(BigInteger, primary_key=True, index=True)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    veterinarian_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        SQLAlchemyEnum(MedicalRecordPermissionStatus, values_callable=lambda x: [e.value for e in x]), 
        default=MedicalRecordPermissionStatus.PENDING,
        nullable=False
    )
    requested_at = Column(DateTime, server_default=func.now(), nullable=False)
    responded_at = Column(DateTime)
    # created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    pet = relationship("Pet")
    veterinarian = relationship("User", foreign_keys=[veterinarian_user_id])
    owner = relationship("User", foreign_keys=[owner_user_id])

    __table_args__ = (
        UniqueConstraint('pet_id', 'veterinarian_user_id', name='_pet_vet_uc'),
    )

