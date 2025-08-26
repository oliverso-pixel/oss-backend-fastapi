#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine
from app.core.security import verify_password, get_password_hash

def check_admin_user():
    """檢查 admin 用戶狀態"""
    print("🔍 Checking admin user...")
    
    with engine.connect() as conn:
        # 檢查 admin 用戶
        result = conn.execute(text("""
            SELECT id, username, email, password_hash, is_active, is_verified 
            FROM users 
            WHERE username = 'admin'
        """)).first()
        
        if not result:
            print("❌ Admin user not found!")
            return False
        
        print(f"✅ Admin user found:")
        print(f"   ID: {result.id}")
        print(f"   Username: {result.username}")
        print(f"   Email: {result.email}")
        print(f"   Active: {result.is_active}")
        print(f"   Verified: {result.is_verified}")
        print(f"   Password hash: {result.password_hash[:20]}...")
        
        # 檢查密碼
        test_password = "admin123456"
        if verify_password(test_password, result.password_hash):
            print(f"✅ Password '{test_password}' is correct")
        else:
            print(f"❌ Password '{test_password}' is incorrect")
            
            # 顯示正確的密碼哈希
            correct_hash = get_password_hash(test_password)
            print(f"\n📝 Correct password hash should be:")
            print(f"   {correct_hash}")
        
        # 檢查角色
        roles_result = conn.execute(text("""
            SELECT r.name, r.display_name 
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
        """), {"user_id": result.id})
        
        roles = list(roles_result)
        if roles:
            print(f"\n👥 User roles:")
            for role in roles:
                print(f"   - {role.name} ({role.display_name})")
        else:
            print("\n⚠️  User has no roles assigned")
        
        return True

def create_or_fix_admin():
    """創建或修復 admin 用戶"""
    print("\n🔧 Creating/fixing admin user...")
    
    with engine.begin() as conn:
        # 檢查是否存在
        existing = conn.execute(text("SELECT id FROM users WHERE username = 'admin'")).first()
        
        if existing:
            # 更新現有用戶的密碼
            print("📝 Updating existing admin user...")
            password_hash = get_password_hash("admin123456")
            
            conn.execute(text("""
                UPDATE users 
                SET password_hash = :password_hash,
                    is_active = TRUE,
                    is_verified = TRUE,
                    updated_at = NOW()
                WHERE username = 'admin'
            """), {"password_hash": password_hash})
            
            admin_id = existing.id
            print("✅ Admin password updated")
        else:
            # 創建新用戶
            print("📝 Creating new admin user...")
            password_hash = get_password_hash("admin123456")
            
            result = conn.execute(text("""
                INSERT INTO users 
                (username, email, password_hash, display_name, is_active, is_verified, created_at, updated_at) 
                VALUES
                ('admin', 'admin@oss.com', :password_hash, '系統管理員', TRUE, TRUE, NOW(), NOW())
            """), {"password_hash": password_hash})
            
            admin_id = result.lastrowid
            print("✅ Admin user created")
        
        # 確保有 super_admin 角色
        super_admin_role = conn.execute(text("SELECT id FROM roles WHERE name = 'super_admin'")).first()
        
        if not super_admin_role:
            print("❌ super_admin role not found! Please run --init-data first")
            return False
        
        # 檢查是否已有角色分配
        existing_role = conn.execute(text("""
            SELECT * FROM user_roles 
            WHERE user_id = :user_id AND role_id = :role_id
        """), {"user_id": admin_id, "role_id": super_admin_role.id}).first()
        
        if not existing_role:
            # 分配角色
            conn.execute(text("""
                INSERT INTO user_roles (user_id, role_id, assigned_at) 
                VALUES (:user_id, :role_id, NOW())
            """), {"user_id": admin_id, "role_id": super_admin_role.id})
            print("✅ super_admin role assigned")
        else:
            print("ℹ️  super_admin role already assigned")
        
        print("\n✅ Admin user is ready!")
        print("📝 Login credentials:")
        print("   Username: admin")
        print("   Password: admin123456")
        
        return True

def test_admin_login():
    """測試 admin 登入"""
    print("\n🧪 Testing admin login...")
    
    from app.services.auth_service import AuthService
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        user = auth_service.authenticate_user("admin", "admin123456")
        
        if user:
            print("✅ Login test successful!")
            print(f"   User ID: {user.id}")
            print(f"   Username: {user.username}")
        else:
            print("❌ Login test failed!")
    except Exception as e:
        print(f"❌ Error during login test: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Admin user management')
    parser.add_argument('--fix', action='store_true', help='Create or fix admin user')
    parser.add_argument('--test', action='store_true', help='Test admin login')
    
    args = parser.parse_args()
    
    if args.fix:
        create_or_fix_admin()
        test_admin_login()
    elif args.test:
        test_admin_login()
    else:
        # 預設檢查
        if not check_admin_user():
            print("\n💡 Run with --fix to create/fix admin user")