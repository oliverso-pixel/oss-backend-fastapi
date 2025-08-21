# scripts/test_models.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine
from app.models import *
import uuid

def test_models():
    """測試模型是否能正確載入"""
    try:
        print("Testing model loading...")
        
        # 不要重新創建表，因為已經有數據了
        print("✓ Using existing tables")
        
        # 測試創建用戶 - 使用唯一的 email 和 username
        with Session(engine) as session:
            # 生成唯一的測試數據
            unique_id = str(uuid.uuid4())[:8]
            test_user = User(
                username=f"test_user_{unique_id}",
                email=f"test_{unique_id}@example.com",
                password_hash="hashed_password",
                display_name=f"Test User {unique_id}"
            )
            session.add(test_user)
            session.commit()
            print(f"✓ Test user created with ID: {test_user.id}")
            
            # 測試查詢
            user = session.query(User).filter_by(id=test_user.id).first()
            print(f"✓ User retrieved: {user.username}")
            
            # 測試關聯
            # 先檢查是否有角色
            roles = session.query(Role).all()
            if roles:
                print(f"✓ Found {len(roles)} roles")
                # 分配一個角色給用戶
                user_role = session.query(Role).filter_by(name="user").first()
                if user_role:
                    session.add(UserRole(user_id=test_user.id, role_id=user_role.id))
                    session.commit()
                    print(f"✓ Assigned 'user' role to test user")
            
            # 清理測試數據
            session.query(UserRole).filter_by(user_id=test_user.id).delete()
            session.delete(test_user)
            session.commit()
            print("✓ Test data cleaned up")
        
        print("\nAll models loaded successfully!")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_models()