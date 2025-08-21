# scripts/check_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_database():
    """檢查資料庫連接和版本"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # 檢查資料庫類型和版本
            if 'mysql' in settings.DATABASE_URL or 'mariadb' in settings.DATABASE_URL:
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
                print(f"Database: MySQL/MariaDB")
                print(f"Version: {version}")
                
                # 檢查是否支援 RETURNING
                if 'MariaDB' in version:
                    parts = version.split('-')[0].split('.')
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    if major > 10 or (major == 10 and minor >= 5):
                        print("✓ Supports RETURNING clause")
                    else:
                        print("✗ Does not support RETURNING clause")
                else:  # MySQL
                    parts = version.split('.') 
                    major = int(parts[0])
                    if major >= 8:
                        print("✓ May support RETURNING clause (MySQL 8.0+)")
                    else:
                        print("✗ Does not support RETURNING clause")
            
            print("\n✓ Database connection successful!")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    check_database()