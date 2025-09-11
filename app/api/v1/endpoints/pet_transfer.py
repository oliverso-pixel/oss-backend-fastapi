# app/api/v1/endpoints/pet_transfer.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from datetime import datetime
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.pet import Pet
from app.schemas.pet import PetResponse
from app.schemas.base import PaginationParams, PaginatedResponse
from app.services.pet_transfer_service import PetTransferService
from app.schemas.pet_transfer import (
    PetTransferRequest, PetTransferResponse, PetTransferUpdate,
    PetTransferHistoryResponse, TransferStatus, TransferType
)

router = APIRouter()

@router.post("/pets/{pet_id}/transfer/request", response_model=PetTransferResponse)
def request_pet_transfer(
    pet_id: int,
    transfer_request: PetTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """請求轉移寵物給其他用戶"""
    transfer_service = PetTransferService(db)
    
    # 創建轉移請求
    try:
        transfer = transfer_service.create_transfer_request(
            pet_id=pet_id,
            from_user_id=current_user.id,
            to_user_id=transfer_request.to_user_id,
            transfer_type=transfer_request.transfer_type,
            transfer_reason=transfer_request.transfer_reason,
            transfer_fee=transfer_request.transfer_fee,
            notes=transfer_request.notes
        )
        
        return transfer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.get("/transfer/requests/received", response_model=PaginatedResponse)
def get_received_transfer_requests(
    status: Optional[TransferStatus] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取收到的寵物轉移請求"""
    transfer_service = PetTransferService(db)
    
    transfers, total = transfer_service.get_received_transfers(
        user_id=current_user.id,
        status=status,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # 轉換為響應格式
    items = [PetTransferResponse.model_validate(transfer) for transfer in transfers]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/transfer/requests/sent", response_model=PaginatedResponse)
def get_sent_transfer_requests(
    status: Optional[TransferStatus] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取發送的寵物轉移請求"""
    transfer_service = PetTransferService(db)
    
    transfers, total = transfer_service.get_sent_transfers(
        user_id=current_user.id,
        status=status,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # 轉換為響應格式
    items = [PetTransferResponse.model_validate(transfer) for transfer in transfers]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.post("/transfer/{transfer_id}/accept", response_model=PetTransferResponse)
def accept_transfer_request(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """接受寵物轉移請求"""
    transfer_service = PetTransferService(db)
    
    try:
        transfer = transfer_service.accept_transfer(
            transfer_id=transfer_id,
            user_id=current_user.id
        )
        return transfer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.post("/transfer/{transfer_id}/reject", response_model=PetTransferResponse)
def reject_transfer_request(
    transfer_id: int,
    reason: Optional[str] = Query(None, description="拒絕原因"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """拒絕寵物轉移請求"""
    transfer_service = PetTransferService(db)
    
    try:
        transfer = transfer_service.reject_transfer(
            transfer_id=transfer_id,
            user_id=current_user.id,
            reason=reason
        )
        return transfer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.post("/transfer/{transfer_id}/cancel", response_model=PetTransferResponse)
def cancel_transfer_request(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """取消寵物轉移請求（僅發起者可取消）"""
    transfer_service = PetTransferService(db)
    
    try:
        transfer = transfer_service.cancel_transfer(
            transfer_id=transfer_id,
            user_id=current_user.id
        )
        return transfer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.get("/pets/{pet_id}/transfer/history", response_model=List[PetTransferHistoryResponse])
def get_pet_transfer_history(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取寵物的轉移歷史記錄"""
    transfer_service = PetTransferService(db)
    
    # 檢查權限：只有當前擁有者或管理員可以查看完整歷史
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    # 檢查是否有權限查看
    if pet.user_id != current_user.id:
        # 如果不是擁有者，檢查是否是管理員
        is_admin = any(role.role.name in ['admin', 'super_admin'] for role in current_user.roles)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this pet's transfer history"
            )
    
    history = transfer_service.get_pet_transfer_history(pet_id)
    
    # 轉換為響應格式
    return [PetTransferHistoryResponse.model_validate(record) for record in history]

@router.get("/transfer/statistics", response_model=dict)
def get_transfer_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取用戶的寵物轉移統計數據"""
    transfer_service = PetTransferService(db)
    
    stats = transfer_service.get_user_transfer_statistics(current_user.id)
    
    return stats

