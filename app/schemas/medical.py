# app/schemas/medical.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.models.medical import VisitType, MedicalRecordPermissionStatus
from app.schemas.user import UserPublicResponse
from app.schemas.pet import PetResponse

# --- Medical Record Schemas ---
class PetMedicalRecordBase(BaseSchema):
    visit_date: date
    visit_type: VisitType
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    notes: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0)
    temperature: Optional[float] = Field(None)
    
class PetMedicalRecordCreate(PetMedicalRecordBase):
    pet_id: int

class PetMedicalRecordUpdate(PetMedicalRecordBase):
    pass

class PetMedicalRecordResponse(PetMedicalRecordBase, TimestampSchema):
    id: int
    pet_id: int
    created_by: int

# --- Vaccination Schemas ---
class PetVaccinationBase(BaseSchema):
    vaccine_type_id: int
    vaccination_date: date
    next_due_date: Optional[date] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None

class PetVaccinationCreate(PetVaccinationBase):
    pet_id: int

class PetVaccinationUpdate(PetVaccinationBase):
    pass
    
class PetVaccinationResponse(PetVaccinationBase, TimestampSchema):
    id: int
    pet_id: int

# --- Access Permission Schemas ---
class MedicalAccessRequestResponse(TimestampSchema):
    id: int
    pet: PetResponse
    veterinarian: UserPublicResponse
    status: MedicalRecordPermissionStatus
    requested_at: datetime
    responded_at: Optional[datetime] = None
