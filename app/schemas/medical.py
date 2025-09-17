# app/schemas/medical.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.models.medical import VisitType, MedicalRecordPermissionStatus, MedicalSpecies
from app.schemas.user import UserPublicResponse
from app.schemas.pet import PetResponse

# --- 診所 Schemas ---

class VeterinaryClinicResponse(BaseSchema):
    id: int
    name: str
    phone: Optional[str] = None
    address: Optional[dict] = None
    is_verified: bool

    class Config:
        from_attributes = True

# --- 疫苗類型 Schemas ---

class VaccineTypeResponse(BaseSchema):
    id: int
    name: str
    species: MedicalSpecies
    is_core: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True

# --- 疫苗記錄 Schemas ---

class VaccinationNestedCreate(BaseSchema):
    """在新增病歷時，巢狀建立疫苗記錄"""
    vaccine_type_id: int
    vaccination_date: date
    next_due_date: Optional[date] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None

class VaccinationResponse(VaccinationNestedCreate, TimestampSchema):
    id: int
    pet_id: int
    created_by: int
    vaccine_name: str = Field(..., description="疫苗名稱")

    @field_validator('vaccine_name', mode='before')
    def set_vaccine_name(cls, v, values):
        # 這個驗證器實際上不會被使用，因為我們將在 service 層手動填充
        # 但保留它作為一個清晰的標記
        return v

# --- 醫療記錄 Schemas ---

class MedicalRecordBase(BaseSchema):
    visit_date: date
    visit_type: VisitType
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    notes: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0)
    temperature: Optional[float] = Field(None)
    clinic_id: Optional[int] = None

class MedicalRecordCreate(MedicalRecordBase):
    pet_id: int
    vaccinations: Optional[List[VaccinationNestedCreate]] = []

class MedicalRecordResponse(MedicalRecordBase, TimestampSchema):
    id: int
    pet_id: int
    created_by: int
    vaccinations: List[VaccinationResponse] = []
    clinic: Optional[VeterinaryClinicResponse] = None

# --- 權限請求 Schemas ---

class AccessRequestResponse(TimestampSchema):
    id: int
    pet: PetResponse
    veterinarian: UserPublicResponse
    status: MedicalRecordPermissionStatus
    requested_at: datetime
    responded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

