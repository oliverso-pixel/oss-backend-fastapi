# app/services/admin_service.py
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from app.models.user import User
from app.models.pet import Pet
from app.models.post import Post
from app.models.merchant import Merchant, MerchantStatus
from app.models.auth import Role, UserRole, Permission, RolePermission
from app.models.audit import AuditLog
from app.schemas.admin import (
    SystemStats, DashboardData, UserManagementAction, 
    MerchantApproval, SystemConfig
)
from app.core.security import get_password_hash
import secrets

class AdminService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_system_stats(self) -> SystemStats:
        """獲取系統統計數據"""
        today = date.today()
        
        stats = SystemStats(
            total_users=self.db.query(User).count(),
            active_users=self.db.query(User).filter(User.is_active == True).count(),
            total_pets=self.db.query(Pet).count(),
            total_posts=self.db.query(Post).filter(Post.is_deleted == False).count(),
            total_merchants=self.db.query(Merchant).count(),
            active_merchants=self.db.query(Merchant).filter(
                Merchant.status == MerchantStatus.APPROVED
            ).count(),
            total_products=0,  # TODO: 實現產品統計
            total_orders=0,    # TODO: 實現訂單統計
            total_revenue=0.0, # TODO: 實現收入統計
            new_users_today=self.db.query(User).filter(
                func.date(User.created_at) == today
            ).count(),
            new_posts_today=self.db.query(Post).filter(
                func.date(Post.created_at) == today
            ).count(),
            new_orders_today=0  # TODO: 實現今日訂單統計
        )
        
        return stats
    
    def get_dashboard_data(self) -> DashboardData:
        """獲取儀表板數據"""
        stats = self.get_system_stats()
        
        # 最近註冊的用戶
        recent_users = self.db.query(User).order_by(
            desc(User.created_at)
        ).limit(10).all()
        
        # 最近的活動記錄
        recent_activities = self._get_recent_activities()
        
        # 收入圖表數據（最近30天）
        revenue_chart = self._get_revenue_chart_data(days=30)
        
        # 用戶增長圖表數據（最近30天）
        user_growth_chart = self._get_user_growth_chart_data(days=30)
        
        return DashboardData(
            stats=stats,
            recent_users=recent_users,
            recent_orders=[],  # TODO: 實現最近訂單
            recent_activities=recent_activities,
            revenue_chart=revenue_chart,
            user_growth_chart=user_growth_chart
        )
    
    def manage_user(self, user_id: int, action: UserManagementAction, 
                   admin_id: int, reason: str = None) -> bool:
        """管理用戶"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if action == UserManagementAction.ACTIVATE:
            user.is_active = True
        elif action == UserManagementAction.DEACTIVATE:
            user.is_active = False
        elif action == UserManagementAction.VERIFY:
            user.is_verified = True
        elif action == UserManagementAction.UNVERIFY:
            user.is_verified = False
        elif action == UserManagementAction.RESET_PASSWORD:
            # 生成臨時密碼
            temp_password = secrets.token_urlsafe(12)
            user.password_hash = get_password_hash(temp_password)
            # TODO: 發送郵件通知用戶
        elif action == UserManagementAction.DELETE:
            self.db.delete(user)
        
        # 記錄審計日誌
        self._log_action(
            admin_id=admin_id,
            action=f"user.{action.value}",
            resource_type="user",
            resource_id=user_id,
            details={"reason": reason}
        )
        
        self.db.commit()
        return True
    
    def bulk_manage_users(self, user_ids: List[int], action: UserManagementAction, 
                         admin_id: int, reason: str = None) -> int:
        """批量管理用戶"""
        count = 0
        for user_id in user_ids:
            if self.manage_user(user_id, action, admin_id, reason):
                count += 1
        return count
    
    def update_user_roles(self, user_id: int, role_names: List[str], admin_id: int) -> bool:
        """更新用戶角色"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # 刪除現有角色
        self.db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        
        # 添加新角色
        for role_name in role_names:
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if role:
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    assigned_by=admin_id
                )
                self.db.add(user_role)
        
        # 記錄審計日誌
        self._log_action(
            admin_id=admin_id,
            action="user.update_roles",
            resource_type="user",
            resource_id=user_id,
            details={"roles": role_names}
        )
        
        self.db.commit()
        return True
    
    def search_users(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[User], int]:
        """搜索用戶"""
        search = f"%{query}%"
        q = self.db.query(User).filter(
            or_(
                User.username.ilike(search),
                User.email.ilike(search),
                User.display_name.ilike(search),
                User.phone.ilike(search)
            )
        )
        
        total = q.count()
        users = q.offset((page - 1) * per_page).limit(per_page).all()
        
        return users, total
    
    def review_merchant(self, merchant_id: int, approved: bool, 
                       admin_id: int, rejection_reason: str = None) -> bool:
        """審核商戶"""
        merchant = self.db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            return False
        
        if approved:
            merchant.status = MerchantStatus.APPROVED
            merchant.verified_at = datetime.utcnow()
            merchant.verified_by = admin_id
        else:
            merchant.status = MerchantStatus.REJECTED
            merchant.rejection_reason = rejection_reason
        
        # 記錄審計日誌
        self._log_action(
            admin_id=admin_id,
            action=f"merchant.{'approve' if approved else 'reject'}",
            resource_type="merchant",
            resource_id=merchant_id,
            details={"reason": rejection_reason} if rejection_reason else {}
        )
        
        self.db.commit()
        return True
    
    def get_pending_merchants(self, page: int = 1, per_page: int = 20) -> Tuple[List[Merchant], int]:
        """獲取待審核商戶"""
        q = self.db.query(Merchant).filter(Merchant.status == MerchantStatus.PENDING)
        total = q.count()
        merchants = q.offset((page - 1) * per_page).limit(per_page).all()
        return merchants, total
    
    def get_audit_logs(self, filters: Dict[str, Any] = None, 
                      page: int = 1, per_page: int = 20) -> Tuple[List[AuditLog], int]:
        """獲取審計日誌"""
        q = self.db.query(AuditLog)
        
        if filters:
            if filters.get("user_id"):
                q = q.filter(AuditLog.user_id == filters["user_id"])
            if filters.get("action"):
                q = q.filter(AuditLog.action == filters["action"])
            if filters.get("resource_type"):
                q = q.filter(AuditLog.resource_type == filters["resource_type"])
            if filters.get("start_date"):
                q = q.filter(AuditLog.created_at >= filters["start_date"])
            if filters.get("end_date"):
                q = q.filter(AuditLog.created_at <= filters["end_date"])
        
        q = q.order_by(desc(AuditLog.created_at))
        total = q.count()
        logs = q.offset((page - 1) * per_page).limit(per_page).all()
        
        return logs, total
    
    def _get_recent_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """獲取最近的系統活動"""
        activities = []
        
        # 最近的用戶註冊
        recent_users = self.db.query(User).order_by(
            desc(User.created_at)
        ).limit(5).all()
        
        for user in recent_users:
            activities.append({
                "type": "user_registration",
                "user_id": user.id,
                "username": user.username,
                "timestamp": user.created_at,
                "description": f"New user registered: {user.username}"
            })
        
        # 最近的貼文
        recent_posts = self.db.query(Post).order_by(
            desc(Post.created_at)
        ).limit(5).all()
        
        for post in recent_posts:
            activities.append({
                "type": "new_post",
                "user_id": post.user_id,
                "post_id": post.id,
                "timestamp": post.created_at,
                "description": f"New post created"
            })
        
        # 按時間排序
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return activities[:limit]
    
    def _get_revenue_chart_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """獲取收入圖表數據"""
        chart_data = []
        today = date.today()
        
        for i in range(days):
            current_date = today - timedelta(days=i)
            # TODO: 實現實際的收入計算
            revenue = 0.0
            
            chart_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "revenue": revenue
            })
        
        chart_data.reverse()
        return chart_data
    
    def _get_user_growth_chart_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """獲取用戶增長圖表數據"""
        chart_data = []
        today = date.today()
        
        for i in range(days):
            current_date = today - timedelta(days=i)
            new_users = self.db.query(User).filter(
                func.date(User.created_at) == current_date
            ).count()
            
            total_users = self.db.query(User).filter(
                func.date(User.created_at) <= current_date
            ).count()
            
            chart_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "new_users": new_users,
                "total_users": total_users
            })
        
        chart_data.reverse()
        return chart_data
    
    def _log_action(self, admin_id: int, action: str, resource_type: str, 
                   resource_id: int = None, details: Dict[str, Any] = None):
        """記錄審計日誌"""
        # TODO: 實現審計日誌記錄
        pass