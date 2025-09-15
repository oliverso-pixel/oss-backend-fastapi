# app/api/v1/endpoints/medical.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.services.medical_service import MedicalService
from app.schemas.medical import (
    PetMedicalRecordCreate, PetMedicalRecordResponse,
    PetVaccinationCreate, PetVaccinationResponse,
    MedicalAccessRequestResponse
)

router = APIRouter()

# --- Medical Records ---

@router.post("/records", response_model=PetMedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_pet_medical_record(
    record_data: PetMedicalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """創建新的寵物病歷。僅飼主、管理員或授權獸醫可操作。"""
    medical_service = MedicalService(db)
    return medical_service.create_medical_record(current_user, record_data)

@router.get("/pets/{pet_id}/records", response_model=List[PetMedicalRecordResponse])
def get_pet_medical_records(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定寵物的所有病歷。"""
    medical_service = MedicalService(db)
    return medical_service.get_medical_records(current_user, pet_id)

# --- Vaccinations ---

@router.post("/vaccinations", response_model=PetVaccinationResponse, status_code=status.HTTP_201_CREATED)
def create_pet_vaccination_record(
    vaccination_data: PetVaccinationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """為寵物新增疫苗接種記錄。"""
    medical_service = MedicalService(db)
    return medical_service.create_vaccination_record(current_user, vaccination_data)

@router.get("/pets/{pet_id}/vaccinations", response_model=List[PetVaccinationResponse])
def get_pet_vaccination_records(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定寵物的所有疫苗接種記錄。"""
    medical_service = MedicalService(db)
    return medical_service.get_vaccination_records(current_user, pet_id)

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

@router.get("/access-requests/pending", response_model=List[MedicalAccessRequestResponse])
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

