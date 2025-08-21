# scripts/init_db_with_seed.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine
from app.core.security import get_password_hash

def init_db_with_seed():
    """初始化資料庫並添加種子數據"""
    try:
        # 先嘗試刪除所有表
        print("Dropping existing tables...")
        try:
            # 獲取連接並禁用外鍵檢查
            with engine.connect() as conn:
                # 檢查是否是 MySQL/MariaDB
                if 'mysql' in settings.DATABASE_URL or 'mariadb' in settings.DATABASE_URL:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                    result = conn.execute(text("SHOW TABLES"))
                    tables = result.fetchall()
                    for table in tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table[0]}"))
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                else:
                    Base.metadata.drop_all(bind=engine)
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not drop tables: {e}")
        
        print("Creating database tables...")
        # 導入所有模型
        from app.models.user import User
        from app.models.auth import Role, Permission, UserRole, RolePermission, UserToken
        from app.models.pet import Pet
        from app.models.post import Post
        from app.models.album import Album
        from app.models.media import Media, PostMedia, AlbumMedia
        from app.models.merchant import Merchant
        from app.models.social import Like, Comment, Tag, PostTag
        from app.models.medical import (
            PetMedicalRecord, PetVaccination, VeterinaryClinic, 
            Veterinarian, VaccineType
        )
        
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully!")
        
        # 創建 session 並禁用 autoflush 以避免 RETURNING 問題
        with Session(engine, autoflush=False) as session:
            # 創建基本權限 - 逐個添加而不是批量添加
            print("Creating permissions...")
            permissions = []
            permission_data = [
                {"module": "user", "action": "read", "name": "user.read", "description": "讀取用戶信息"},
                {"module": "user", "action": "write", "name": "user.write", "description": "修改用戶信息"},
                {"module": "user", "action": "delete", "name": "user.delete", "description": "刪除用戶"},
                {"module": "admin", "action": "access", "name": "admin.access", "description": "訪問管理後台"},
                {"module": "product", "action": "create", "name": "product.create", "description": "創建商品"},
                {"module": "product", "action": "update", "name": "product.update", "description": "更新商品"},
                {"module": "product", "action": "delete", "name": "product.delete", "description": "刪除商品"},
            ]
            
            for perm_data in permission_data:
                perm = Permission(**perm_data)
                session.add(perm)
                session.flush()  # 立即 flush 以獲取 ID
                permissions.append(perm)
            
            print(f"✓ Created {len(permissions)} permissions")
            
            # 創建角色
            print("Creating roles...")
            admin_role = Role(name="admin", display_name="管理員", description="系統管理員", is_system=True)
            user_role = Role(name="user", display_name="普通用戶", description="普通用戶", is_system=True)
            merchant_role = Role(name="merchant", display_name="商家", description="商家用戶", is_system=True)
            
            session.add(admin_role)
            session.add(user_role)
            session.add(merchant_role)
            session.flush()
            
            print("✓ Created roles")
            
            # 為角色分配權限
            print("Assigning permissions to roles...")
            # 管理員擁有所有權限
            for perm in permissions:
                session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))
            
            # 普通用戶權限
            user_perms = ["user.read", "user.write"]
            for perm in permissions:
                if perm.name in user_perms:
                    session.add(RolePermission(role_id=user_role.id, permission_id=perm.id))
            
            # 商家權限
            merchant_perms = ["user.read", "user.write", "product.create", "product.update", "product.delete"]
            for perm in permissions:
                if perm.name in merchant_perms:
                    session.add(RolePermission(role_id=merchant_role.id, permission_id=perm.id))
            
            session.flush()
            print("✓ Assigned permissions to roles")
            
            # 創建測試用戶
            print("Creating test users...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("Admin123!"),
                display_name="System Admin",
                is_active=True,
                is_verified=True
            )
            
            test_user = User(
                username="testuser",
                email="test@example.com",
                password_hash=get_password_hash("Test123!"),
                display_name="Test User",
                is_active=True,
                is_verified=True
            )
            
            session.add(admin_user)
            session.add(test_user)
            session.flush()
            
            print("✓ Created test users")
            
            # 分配角色
            print("Assigning roles to users...")
            session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            session.add(UserRole(user_id=test_user.id, role_id=user_role.id))
            
            # 最終提交
            session.commit()
            print("✓ Seed data created successfully!")
            
            # 測試查詢
            print("\nTesting queries...")
            users = session.query(User).all()
            print(f"✓ Found {len(users)} users")
            
            roles = session.query(Role).all()
            print(f"✓ Found {len(roles)} roles")
            
            perms = session.query(Permission).all()
            print(f"✓ Found {len(perms)} permissions")
            
            # 測試用戶角色關聯
            admin = session.query(User).filter_by(username="admin").first()
            if admin:
                print(f"✓ Admin user has {len(admin.roles)} roles")
            
            print("\nDatabase initialization complete!")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_db_with_seed()