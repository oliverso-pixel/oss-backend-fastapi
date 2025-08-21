# scripts/cleanup_duplicates.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine
from app.models.user import User

def cleanup_duplicates():
    """清理重複的用戶數據"""
    try:
        with Session(engine) as session:
            # 查找重複的 email
            print("Checking for duplicate emails...")
            result = session.execute(
                text("""
                    SELECT email, COUNT(*) as count 
                    FROM users 
                    GROUP BY email 
                    HAVING COUNT(*) > 1
                """)
            )
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"Found {len(duplicates)} duplicate emails")
                for email, count in duplicates:
                    print(f"  - {email}: {count} occurrences")
                    
                    # 保留最新的一個，刪除其他的
                    users = session.query(User).filter_by(email=email).order_by(User.id.desc()).all()
                    for user in users[1:]:  # 跳過第一個（最新的）
                        print(f"    Deleting user: {user.username} (ID: {user.id})")
                        session.delete(user)
                
                session.commit()
                print("✓ Duplicates cleaned up")
            else:
                print("✓ No duplicate emails found")
            
            # 同樣檢查 username
            print("\nChecking for duplicate usernames...")
            result = session.execute(
                text("""
                    SELECT username, COUNT(*) as count 
                    FROM users 
                    GROUP BY username 
                    HAVING COUNT(*) > 1
                """)
            )
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"Found {len(duplicates)} duplicate usernames")
                for username, count in duplicates:
                    print(f"  - {username}: {count} occurrences")
            else:
                print("✓ No duplicate usernames found")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_duplicates()