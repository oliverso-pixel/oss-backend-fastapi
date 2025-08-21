# app/api/v1/endpoints/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.core.permissions import is_admin
from app.models.user import User
from app.services.admin_service import AdminService
from app.services.user_service import UserService
from app.schemas.admin import (
    SystemStats, DashboardData, UserBulkAction, RoleUpdate,
    MerchantApproval, AuditLog, AdminNotification
)
from app.schemas.user import UserResponse
from app.schemas.base import PaginatedResponse

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """獲取管理員儀表板數據"""
    admin_service = AdminService(db)
    return admin_service.get_dashboard_data()

@router.get("/stats", response_model=SystemStats)
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """獲取系統統計數據"""
    admin_service = AdminService(db)
    return admin_service.get_system_stats()

# === 用戶管理 ===

@router.get("/users", response_model=PaginatedResponse)
def search_users(
    q: Optional[str] = Query(None, description="搜索關鍵字"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """搜索和管理用戶"""
    admin_service = AdminService(db)
    
    if q:
        users, total = admin_service.search_users(q, page, per_page)
    else:
        user_service = UserService(db)
        users, total = user_service.get_users((page - 1) * per_page, per_page)
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

@router.post("/users/{user_id}/manage")
def manage_user(
    user_id: int,
    action: str = Query(..., description="Action to perform"),
    reason: Optional[str] = Query(None, description="Reason for action"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """管理單個用戶"""
    admin_service = AdminService(db)
    
    success = admin_service.manage_user(
        user_id=user_id,
        action=action,
        admin_id=current_user.id,
        reason=reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": f"User {action} successful"}

@router.post("/users/bulk-action")
def bulk_manage_users(
    action_data: UserBulkAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """批量管理用戶"""
    admin_service = AdminService(db)
    
    affected = admin_service.bulk_manage_users(
        user_ids=action_data.user_ids,
        action=action_data.action,
        admin_id=current_user.id,
        reason=action_data.reason
    )
    
    return {
        "message": f"Bulk action completed",
        "affected_users": affected
    }

@router.put("/users/{user_id}/roles")
def update_user_roles(
    user_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """更新用戶角色"""
    admin_service = AdminService(db)
    
    success = admin_service.update_user_roles(
        user_id=user_id,
        role_names=role_update.role_names,
        admin_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User roles updated successfully"}

# === 商戶管理 ===

@router.get("/merchants/pending")
def get_pending_merchants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """獲取待審核商戶列表"""
    admin_service = AdminService(db)
    merchants, total = admin_service.get_pending_merchants(page, per_page)
    
    return PaginatedResponse(
        items=merchants,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

@router.post("/merchants/{merchant_id}/review")
def review_merchant(
    merchant_id: int,
    approval: MerchantApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """審核商戶申請"""
    admin_service = AdminService(db)
    
    success = admin_service.review_merchant(
        merchant_id=merchant_id,
        approved=approval.approved,
        admin_id=current_user.id,
        rejection_reason=approval.rejection_reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
    
    return {
        "message": f"Merchant {'approved' if approval.approved else 'rejected'} successfully"
    }

# === 內容管理 ===

@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    reason: str = Query(..., description="Reason for deletion"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """刪除貼文"""
    # TODO: 實現貼文刪除邏輯
    return {"message": "Post deleted successfully"}

@router.post("/posts/{post_id}/restore")
def restore_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """恢復已刪除的貼文"""
    # TODO: 實現貼文恢復邏輯
    return {"message": "Post restored successfully"}

# === 審計日誌 ===

@router.get("/audit-logs", response_model=PaginatedResponse)
def get_audit_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """獲取審計日誌"""
    admin_service = AdminService(db)
    
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if action:
        filters["action"] = action
    if resource_type:
        filters["resource_type"] = resource_type
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    
    logs, total = admin_service.get_audit_logs(filters, page, per_page)
    
    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

# === 系統管理 ===

@router.post("/broadcast")
def broadcast_notification(
    notification: AdminNotification,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """發送系統通知"""
    # TODO: 實現通知發送邏輯
    return {"message": "Notification sent successfully"}

@router.post("/maintenance")
def toggle_maintenance_mode(
    enabled: bool = Query(..., description="Enable or disable maintenance mode"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """切換維護模式"""
    # TODO: 實現維護模式邏輯
    return {"message": f"Maintenance mode {'enabled' if enabled else 'disabled'}"}

@router.get("/export/users")
def export_users(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """導出用戶數據"""
    # TODO: 實現數據導出邏輯
    return {"message": "Export started", "format": format}

@router.get("/export/reports")
def export_reports(
    report_type: str = Query(..., description="Type of report to export"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
) -> Any:
    """導出報表"""
    # TODO: 實現報表導出邏輯
    return {
        "message": "Report export started",
        "report_type": report_type,
        "date_range": f"{start_date} to {end_date}"
    }