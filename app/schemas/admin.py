# app/schemas/admin.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserResponse
from enum import Enum

class SystemStats(BaseSchema):
    """系統統計數據"""
    total_users: int
    active_users: int
    total_pets: int
    total_posts: int
    total_merchants: int
    active_merchants: int
    total_products: int
    total_orders: int
    total_revenue: float
    new_users_today: int
    new_posts_today: int
    new_orders_today: int

class DashboardData(BaseSchema):
    """儀表板數據"""
    stats: SystemStats
    recent_users: List[UserResponse]
    recent_orders: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]
    revenue_chart: List[Dict[str, Any]]
    user_growth_chart: List[Dict[str, Any]]

class UserManagementAction(str, Enum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    VERIFY = "verify"
    UNVERIFY = "unverify"
    RESET_PASSWORD = "reset_password"
    DELETE = "delete"

class UserBulkAction(BaseSchema):
    """批量用戶操作"""
    user_ids: List[int]
    action: UserManagementAction
    reason: Optional[str] = None

class RoleUpdate(BaseSchema):
    """角色更新"""
    user_id: int
    role_names: List[str]

class MerchantApproval(BaseSchema):
    """商戶審核"""
    merchant_id: int
    approved: bool
    rejection_reason: Optional[str] = None

class SystemConfig(BaseSchema):
    """系統配置"""
    site_name: str
    site_description: str
    maintenance_mode: bool
    allow_registration: bool
    require_email_verification: bool
    commission_rate: float
    max_upload_size: int
    allowed_file_types: List[str]

class AuditLog(TimestampSchema):
    """審計日誌"""
    id: int
    user_id: int
    username: str
    action: str
    resource_type: str
    resource_id: Optional[int]
    details: Dict[str, Any]
    ip_address: str
    user_agent: str

class AdminNotification(BaseSchema):
    """管理員通知"""
    title: str
    message: str
    type: str  # info, warning, error, success
    target_roles: Optional[List[str]] = None
    target_users: Optional[List[int]] = None

