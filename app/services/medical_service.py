# app/services/medical_service.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.user import User
from app.models.pet import Pet
from app.models.medical import PetMedicalRecord, PetVaccination, MedicalRecordPermission, Veterinarian, MedicalRecordPermissionStatus
from app.schemas.medical import PetMedicalRecordCreate, PetMedicalRecordUpdate, PetVaccinationCreate, PetVaccinationUpdate
from app.services.privacy_service import PrivacyService
from app.services.notification_service import NotificationService

class MedicalService:
    def __init__(self, db: Session):
        self.db = db
        self.privacy_service = PrivacyService(db)
        self.notification_service = NotificationService(db)

    def _check_permission(self, user: User, pet_id: int) -> Pet:
        """核心權限檢查：檢查用戶是否為飼主、管理員或有授權的獸醫"""
        pet = self.db.query(Pet).filter(Pet.id == pet_id).first()
        if not pet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

        is_owner = pet.user_id == user.id
        is_admin = self.privacy_service.is_admin(user)
        
        has_vet_permission = False
        if self.privacy_service.is_vet(user):
            permission = self.db.query(MedicalRecordPermission).filter(
                MedicalRecordPermission.pet_id == pet_id,
                MedicalRecordPermission.veterinarian_user_id == user.id,
                MedicalRecordPermission.status == MedicalRecordPermissionStatus.GRANTED
            ).first()
            if permission:
                has_vet_permission = True

        if not (is_owner or is_admin or has_vet_permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access these medical records.")
            
        return pet

    # --- Medical Records ---
    def create_medical_record(self, user: User, record_data: PetMedicalRecordCreate) -> PetMedicalRecord:
        pet = self._check_permission(user, record_data.pet_id)
        
        new_record = PetMedicalRecord(
            **record_data.model_dump(),
            created_by=user.id
        )
        self.db.add(new_record)
        self.db.commit()
        self.db.refresh(new_record)
        return new_record

    def get_medical_records(self, user: User, pet_id: int) -> List[PetMedicalRecord]:
        pet = self._check_permission(user, pet_id)
        return self.db.query(PetMedicalRecord).filter(PetMedicalRecord.pet_id == pet_id).order_by(PetMedicalRecord.visit_date.desc()).all()

    # --- Vaccinations ---
    def create_vaccination_record(self, user: User, vaccination_data: PetVaccinationCreate) -> PetVaccination:
        pet = self._check_permission(user, vaccination_data.pet_id)
        
        new_vaccination = PetVaccination(
            **vaccination_data.model_dump(),
            created_by=user.id
        )
        self.db.add(new_vaccination)
        self.db.commit()
        self.db.refresh(new_vaccination)
        return new_vaccination

    def get_vaccination_records(self, user: User, pet_id: int) -> List[PetVaccination]:
        pet = self._check_permission(user, pet_id)
        return self.db.query(PetVaccination).filter(PetVaccination.pet_id == pet_id).order_by(PetVaccination.vaccination_date.desc()).all()

    # --- Access Request Logic ---
    def request_medical_access(self, vet_user: User, pet_id: int) -> MedicalRecordPermission:
        if not self.privacy_service.is_vet(vet_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only veterinarians can request access.")

        pet = self.db.query(Pet).filter(Pet.id == pet_id).first()
        if not pet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

        existing_request = self.db.query(MedicalRecordPermission).filter(
            MedicalRecordPermission.pet_id == pet_id,
            MedicalRecordPermission.veterinarian_user_id == vet_user.id
        ).first()

        if existing_request and existing_request.status in [MedicalRecordPermissionStatus.PENDING, MedicalRecordPermissionStatus.GRANTED]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access request already exists or has been granted.")

        if existing_request:
            existing_request.status = MedicalRecordPermissionStatus.PENDING
            permission_request = existing_request
        else:
            permission_request = MedicalRecordPermission(
                pet_id=pet_id,
                veterinarian_user_id=vet_user.id,
                owner_user_id=pet.user_id
            )
            self.db.add(permission_request)

        # Send notification to pet owner
        self.notification_service.create_notification(
            user_id=pet.user_id,
            type="medical_access_request",
            title="病歷存取請求",
            content=f"獸醫 {vet_user.display_name or vet_user.username} 請求查看您寵物 {pet.name} 的病歷。",
            data={"pet_id": pet_id, "vet_id": vet_user.id}
        )
        
        self.db.commit()
        self.db.refresh(permission_request)
        return permission_request

    def get_pending_access_requests(self, owner: User) -> List[MedicalRecordPermission]:
        return self.db.query(MedicalRecordPermission).options(
            joinedload(MedicalRecordPermission.pet),
            joinedload(MedicalRecordPermission.veterinarian)
        ).filter(
            MedicalRecordPermission.owner_user_id == owner.id,
            MedicalRecordPermission.status == MedicalRecordPermissionStatus.PENDING
        ).all()

    def respond_to_access_request(self, owner: User, request_id: int, approve: bool):
        request = self.db.query(MedicalRecordPermission).filter(
            MedicalRecordPermission.id == request_id,
            MedicalRecordPermission.owner_user_id == owner.id,
            MedicalRecordPermission.status == MedicalRecordPermissionStatus.PENDING
        ).first()

        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or already handled.")

        request.status = MedicalRecordPermissionStatus.GRANTED if approve else MedicalRecordPermissionStatus.REJECTED
        request.responded_at = func.now()
        
        self.db.commit()
        # TODO: Notify the veterinarian of the outcome
        return request
