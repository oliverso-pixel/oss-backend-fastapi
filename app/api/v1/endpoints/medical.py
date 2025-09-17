# app/api/v1/endpoints/medical.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.medical import MedicalSpecies
from app.services.medical_service import MedicalService
from app.schemas.base import PaginatedResponse
from app.schemas.medical import (
    MedicalRecordCreate, MedicalRecordResponse,
    AccessRequestResponse, VeterinaryClinicResponse,
    VaccinationResponse, VaccineTypeResponse
)

router = APIRouter()

# --- Clinics & Vaccine Types ---

@router.get("/clinics", response_model=PaginatedResponse)
def list_veterinary_clinics(
    search: Optional[str] = Query(None, description="依診所名稱搜尋"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Any:
    """獲取或搜尋獸醫診所列表。"""
    medical_service = MedicalService(db)
    clinics, total = medical_service.list_clinics(search=search, skip=(page - 1) * per_page, limit=per_page)
    
    return PaginatedResponse(
        items=[VeterinaryClinicResponse.model_validate(c) for c in clinics],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

@router.get("/vaccine-types", response_model=List[VaccineTypeResponse])
def list_vaccine_types(
    species: Optional[MedicalSpecies] = Query(None, description="依物種篩選 (dog, cat, rabbit, other)"),
    db: Session = Depends(get_db)
) -> Any:
    """獲取所有可用的疫苗類型列表。"""
    medical_service = MedicalService(db)
    vaccine_types = medical_service.list_vaccine_types(species=species)
    return [VaccineTypeResponse.model_validate(vt) for vt in vaccine_types]

# --- Medical Records & Vaccinations ---

@router.post("/records", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_pet_medical_record(
    record_data: MedicalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    創建新的寵物病歷，可同時包含疫苗接種記錄。
    """
    medical_service = MedicalService(db)
    record = medical_service.create_medical_record_with_vaccinations(current_user, record_data)
    
    # 手動填充回應模型
    record_dict = record.__dict__
    processed_vaccinations = []
    if record.vaccinations:
        for vax in record.vaccinations:
            vax_dict = vax.__dict__
            vax_dict['vaccine_name'] = vax.vaccine_type.name if vax.vaccine_type else 'N/A'
            processed_vaccinations.append(VaccinationResponse.model_validate(vax_dict))
    record_dict['vaccinations'] = processed_vaccinations
            
    return MedicalRecordResponse.model_validate(record_dict)

@router.get("/pets/{pet_id}/records", response_model=List[MedicalRecordResponse])
def get_pet_medical_records(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定寵物的所有病歷 (包含疫苗記錄)。"""
    medical_service = MedicalService(db)
    records = medical_service.get_medical_records(current_user, pet_id)

    # 手動處理並填充 vaccine_name 以符合 Response Model
    response_list = []
    for record in records:
        record_dict = record.__dict__
        processed_vaccinations = []
        if record.vaccinations:
            for vax in record.vaccinations:
                vax_dict = vax.__dict__
                vax_dict['vaccine_name'] = vax.vaccine_type.name if vax.vaccine_type else 'N/A'
                processed_vaccinations.append(VaccinationResponse.model_validate(vax_dict))
        
        record_dict['vaccinations'] = processed_vaccinations
        response_list.append(MedicalRecordResponse.model_validate(record_dict))
        
    return response_list

@router.get("/pets/{pet_id}/vaccinations", response_model=List[VaccinationResponse])
def get_pet_vaccination_records(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定寵物的所有疫苗接種記錄 (針卡)。"""
    medical_service = MedicalService(db)
    records = medical_service.get_vaccination_records(current_user, pet_id)
    # 手動填充疫苗名稱
    response = []
    for record in records:
        record_dict = record.__dict__
        record_dict['vaccine_name'] = record.vaccine_type.name if record.vaccine_type else 'N/A'
        response.append(VaccinationResponse.model_validate(record_dict))
    return response

# --- Access Management ---

@router.post("/pets/{pet_id}/request-access", status_code=status.HTTP_202_ACCEPTED)
def request_medical_record_access(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獸醫請求查看特定寵物的病歷。"""
    medical_service = MedicalService(db)
    medical_service.request_medical_access(current_user, pet_id)
    return {"message": "Access request sent to the pet owner."}

@router.get("/access-requests/pending", response_model=List[AccessRequestResponse])
def get_pending_access_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """飼主查看待處理的病歷存取請求。"""
    medical_service = MedicalService(db)
    return medical_service.get_pending_access_requests(current_user)

@router.post("/access-requests/{request_id}/approve")
def approve_access_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """飼主批准病歷存取請求。"""
    medical_service = MedicalService(db)
    medical_service.respond_to_access_request(current_user, request_id, approve=True)
    return {"message": "Access granted successfully."}

@router.post("/access-requests/{request_id}/reject")
def reject_access_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """飼主拒絕病歷存取請求。"""
    medical_service = MedicalService(db)
    medical_service.respond_to_access_request(current_user, request_id, approve=False)
    return {"message": "Access request rejected."}

