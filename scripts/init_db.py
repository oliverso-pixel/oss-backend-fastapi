# scripts/init_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import settings
from app.core.database import engine, Base
from app.core.security import get_password_hash
from app.models import *
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# 完整的表格列表
EXPECTED_TABLES = [
    # 用戶與認證
    'users', 'roles', 'permissions', 'role_permissions', 'user_roles',
    'user_permissions', 'user_tokens', 'token_blacklist',
    
    # 寵物相關
    'pets',
    
    # 貼文與媒體
    'posts', 'media', 'post_media', 'albums', 'album_media',
    
    # 社交功能
    'tags', 'post_tags', 'friendships', 'follows', 'likes', 'comments',
    
    # 商戶與商品
    'merchants', 'merchant_documents', 'merchant_reviews',
    'product_categories', 'products', 'product_media',
    'orders', 'order_items',
    
    # 寵物醫療
    'veterinary_clinics', 'veterinarians', 'vaccine_types',
    'pet_medical_records', 'pet_vaccinations', 'pet_medications',
    'pet_health_reminders',
    
    # 其他功能
    'notifications', 'chat_rooms', 'chat_room_members', 'chat_messages',
    'audit_logs'
]

# 表格依賴關係（用於檢查外鍵完整性）
TABLE_DEPENDENCIES = {
    'user_roles': ['users', 'roles'],
    'role_permissions': ['roles', 'permissions'],
    'user_permissions': ['users', 'permissions'],
    'user_tokens': ['users'],
    'token_blacklist': ['users'],
    'pets': ['users'],
    'posts': ['users', 'pets'],
    'media': ['users'],
    'post_media': ['posts', 'media'],
    'albums': ['users', 'pets', 'media'],
    'album_media': ['albums', 'media'],
    'post_tags': ['posts', 'tags'],
    'friendships': ['users'],
    'follows': ['users'],
    'likes': ['users', 'posts'],
    'comments': ['users', 'posts'],
    'merchants': ['users'],
    'merchant_documents': ['merchants', 'users'],
    'merchant_reviews': ['merchants', 'users', 'orders'],
    'product_categories': [],  # 自引用
    'products': ['product_categories', 'merchants'],
    'product_media': ['products', 'media'],
    'orders': ['users'],
    'order_items': ['orders', 'products'],
    'veterinary_clinics': [],
    'veterinarians': ['veterinary_clinics'],
    'vaccine_types': [],
    'pet_medical_records': ['pets', 'veterinary_clinics', 'veterinarians', 'users'],
    'pet_vaccinations': ['pets', 'vaccine_types', 'pet_medical_records', 'veterinary_clinics', 'veterinarians', 'users'],
    'pet_medications': ['pets', 'pet_medical_records', 'users'],
    'pet_health_reminders': ['pets', 'users'],
    'notifications': ['users'],
    'chat_rooms': [],
    'chat_room_members': ['chat_rooms', 'users'],
    'chat_messages': ['chat_rooms', 'users', 'media'],
    'audit_logs': []
}

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

def check_db_status(detailed: bool = True) -> Dict:
    """
    檢查資料庫狀態和完整性
    
    Args:
        detailed: 是否顯示詳細信息
        
    Returns:
        dict: 檢查結果
    """
    print("\n📊 Checking database status...")
    
    results = {
        'status': 'healthy',
        'tables': {
            'found': [],
            'missing': [],
            'details': {}
        },
        'total_tables': 0,
        'expected_tables': len(EXPECTED_TABLES),
        'total_records': 0,
        'integrity': {
            'foreign_keys': True,
            'indexes': True,
            'constraints': True,
            'issues': []
        }
    }
    
    with engine.connect() as conn:
        # 1. 獲取所有表
        result = conn.execute(text("SHOW TABLES"))
        existing_tables = [row[0] for row in result]
        results['total_tables'] = len(existing_tables)
        
        # 2. 檢查預期表格
        for table in EXPECTED_TABLES:
            if table in existing_tables:
                results['tables']['found'].append(table)
                
                # 獲取表格詳細信息
                if detailed:
                    # 記錄數
                    count_result = conn.execute(text(f"SELECT COUNT(*) as count FROM `{table}`"))
                    record_count = count_result.first().count
                    
                    # 表格結構
                    columns_result = conn.execute(text(f"SHOW COLUMNS FROM `{table}`"))
                    columns = [row[0] for row in columns_result]
                    
                    # 索引
                    indexes_result = conn.execute(text(f"SHOW INDEXES FROM `{table}`"))
                    indexes = list(set([row[2] for row in indexes_result]))  # Key_name
                    
                    results['tables']['details'][table] = {
                        'records': record_count,
                        'columns': len(columns),
                        'indexes': len(indexes)
                    }
                    results['total_records'] += record_count
                    
                    if record_count > 0:
                        print(f"✅ Table '{table}': {record_count} records, {len(columns)} columns, {len(indexes)} indexes")
                    else:
                        print(f"⚠️  Table '{table}': Empty (0 records)")
            else:
                results['tables']['missing'].append(table)
                results['status'] = 'incomplete'
                print(f"❌ Table '{table}': Missing")
        
        # 3. 檢查意外的表格
        unexpected_tables = set(existing_tables) - set(EXPECTED_TABLES)
        if unexpected_tables:
            print(f"\n📌 Unexpected tables found: {', '.join(sorted(unexpected_tables))}")
        
        # 4. 檢查外鍵完整性
        if detailed:
            print("\n🔍 Checking foreign key integrity...")
            fk_issues = check_foreign_keys(conn)
            if fk_issues:
                results['integrity']['foreign_keys'] = False
                results['integrity']['issues'].extend(fk_issues)
                results['status'] = 'unhealthy'
        
        # 5. 檢查關鍵數據
        if detailed and 'roles' in results['tables']['found']:
            print("\n🔑 Checking critical data...")
            critical_issues = check_critical_data(conn)
            if critical_issues:
                results['integrity']['issues'].extend(critical_issues)
                results['status'] = 'needs_initialization'
    
    # 生成摘要
    print(f"\n📊 Database Status Summary:")
    print(f"   Status: {results['status'].upper()}")
    print(f"   Tables: {len(results['tables']['found'])}/{results['expected_tables']}")
    print(f"   Total Records: {results['total_records']}")
    
    if results['tables']['missing']:
        print(f"   Missing Tables: {len(results['tables']['missing'])}")
        print(f"      {', '.join(results['tables']['missing'][:5])}")
        if len(results['tables']['missing']) > 5:
            print(f"      ... and {len(results['tables']['missing']) - 5} more")
    
    if results['integrity']['issues']:
        print(f"\n⚠️  Integrity Issues Found:")
        for issue in results['integrity']['issues'][:5]:
            print(f"   - {issue}")
        if len(results['integrity']['issues']) > 5:
            print(f"   ... and {len(results['integrity']['issues']) - 5} more issues")
    
    return results

def check_foreign_keys(conn) -> List[str]:
    """檢查外鍵約束完整性"""
    issues = []
    
    # 檢查每個表的外鍵
    for table, deps in TABLE_DEPENDENCIES.items():
        try:
            # 檢查表是否存在
            table_exists = conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table"),
                {"table": table}
            ).scalar() > 0
            
            if not table_exists:
                continue
            
            # 獲取外鍵信息
            fk_result = conn.execute(text(f"""
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = '{table}'
                    AND REFERENCED_TABLE_NAME IS NOT NULL
            """))
            
            fk_count = 0
            for fk in fk_result:
                fk_count += 1
                # 可以在這裡添加更詳細的外鍵檢查
            
            # 檢查是否缺少預期的外鍵
            if deps and fk_count < len(deps):
                issues.append(f"Table '{table}' may have missing foreign keys")
                
        except Exception as e:
            issues.append(f"Error checking foreign keys for '{table}': {str(e)}")
    
    return issues

def check_critical_data(conn) -> List[str]:
    """檢查關鍵數據是否存在"""
    issues = []
    
    # 檢查必要的角色
    required_roles = ['super_admin', 'admin', 'user']
    for role in required_roles:
        count = conn.execute(
            text("SELECT COUNT(*) FROM roles WHERE name = :name"),
            {"name": role}
        ).scalar()
        if count == 0:
            issues.append(f"Missing required role: '{role}'")
    
    # 檢查是否有管理員用戶
    admin_count = conn.execute(text("""
        SELECT COUNT(*) FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name IN ('super_admin', 'admin')
    """)).scalar()
    
    if admin_count == 0:
        issues.append("No admin users found")
    
    # 檢查權限表
    permission_count = conn.execute(text("SELECT COUNT(*) FROM permissions")).scalar()
    if permission_count == 0:
        issues.append("No permissions defined")
    
    # 檢查疫苗類型
    vaccine_count = conn.execute(text("SELECT COUNT(*) FROM vaccine_types")).scalar()
    if vaccine_count == 0:
        issues.append("No vaccine types defined")
    
    return issues

def init_data_from_sql(sql_file_path: str = None) -> Dict:
    """
    從 SQL 檔案初始化數據
    
    Args:
        sql_file_path: SQL 檔案路徑
        
    Returns:
        dict: 執行結果
    """
    if sql_file_path is None:
        sql_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts',
            'init_data.sql'
        )
    
    print(f"\n📝 Initializing data from: {sql_file_path}")
    
    # 先檢查資料庫狀態
    db_status = check_db_status(detailed=False)
    if db_status['tables']['missing']:
        print(f"❌ Cannot initialize data: {len(db_status['tables']['missing'])} tables are missing")
        print("   Please create tables first using: python init_db.py --sql create_tables.sql")
        return {'status': 'error', 'message': 'Missing tables'}
    
    # 執行初始數據 SQL
    results = execute_sql_file(sql_file_path)
    
    # 創建預設管理員（如果需要）
    # if results['successful'] > 0:
    #     try:
    #         create_default_admin()
    #     except Exception as e:
    #         print(f"⚠️  Warning: Could not create default admin: {e}")
    
    return results

def reset_all_data():
    """重設所有數據（保留表結構，清空數據並重新初始化）"""
    print("\n🔄 Reset All Data")
    print("This will:")
    print("  1. Keep all table structures")
    print("  2. Delete ALL data from all tables")
    print("  3. Re-initialize with default data")
    
    response = input("\n⚠️  WARNING: This will delete ALL DATA. Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return False
    
    # 二次確認
    response = input("⚠️  FINAL WARNING: Type 'RESET ALL DATA' to confirm: ")
    if response != 'RESET ALL DATA':
        print("❌ Operation cancelled.")
        return False
    
    print("\n🗑️  Starting data reset...")
    
    try:
        with engine.begin() as conn:
            # 1. 禁用外鍵檢查
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 2. 獲取所有表並按依賴順序排序
            result = conn.execute(text("SHOW TABLES"))
            all_tables = [row[0] for row in result]
            
            # 3. 清空所有表（按反向依賴順序）
            tables_to_clear = []
            
            # 先處理沒有被其他表依賴的表
            leaf_tables = [
                'audit_logs', 'chat_messages', 'chat_room_members',
                'notifications', 'pet_health_reminders', 'pet_medications',
                'pet_vaccinations', 'pet_medical_records',
                'order_items', 'product_media', 'merchant_reviews',
                'merchant_documents', 'comments', 'likes', 'follows',
                'friendships', 'post_tags', 'album_media', 'post_media',
                'token_blacklist', 'user_tokens', 'user_permissions',
                'user_roles', 'role_permissions'
            ]
            
            # 然後是中間層表
            middle_tables = [
                'products', 'merchants', 'orders', 'albums', 'posts',
                'media', 'pets', 'veterinarians', 'tags'
            ]
            
            # 最後是基礎表
            base_tables = [
                'users', 'roles', 'permissions', 'vaccine_types',
                'veterinary_clinics', 'product_categories', 'chat_rooms'
            ]
            
            # 組合所有表
            ordered_tables = leaf_tables + middle_tables + base_tables
            
            # 清空表
            for table in ordered_tables:
                if table in all_tables:
                    print(f"   Clearing table: {table}")
                    conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            
            # 4. 重新啟用外鍵檢查
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            print("✅ All tables cleared successfully!")
            
        # 5. 重新初始化數據
        print("\n📝 Re-initializing data...")
        
        # 執行初始數據 SQL
        data_sql = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'init_data.sql'
        )
        
        if os.path.exists(data_sql):
            results = execute_sql_file(data_sql)
            
            if results['successful'] > 0:
                print("✅ Data re-initialization completed!")
                
                # 顯示初始化結果
                print("\n📊 Reset Summary:")
                print(f"   Tables cleared: {len(ordered_tables)}")
                print(f"   Data statements executed: {results['successful']}")
                
                if results['data_inserted']:
                    total_rows = sum(item['rows'] for item in results['data_inserted'])
                    print(f"   Total rows inserted: {total_rows}")
                
                # 驗證安裝
                print("\n🔍 Verifying reset...")
                verify_installation()
                
                return True
            else:
                print("❌ Data initialization failed!")
                return False
        else:
            print(f"❌ Data file not found: {data_sql}")
            return False
            
    except Exception as e:
        print(f"❌ Error during reset: {str(e)}")
        return False

def clean_specific_data(table_names: List[str] = None):
    """清理特定表的數據"""
    if not table_names:
        print("❌ No tables specified")
        return
    
    print(f"\n🧹 Cleaning data from tables: {', '.join(table_names)}")
    response = input("Are you sure? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    try:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            for table in table_names:
                try:
                    # 檢查表是否存在
                    exists = conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table"),
                        {"table": table}
                    ).scalar() > 0
                    
                    if exists:
                        # 獲取記錄數
                        count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                        
                        # 清空表
                        conn.execute(text(f"TRUNCATE TABLE `{table}`"))
                        print(f"✅ Cleared {count} records from '{table}'")
                    else:
                        print(f"⚠️  Table '{table}' does not exist")
                        
                except Exception as e:
                    print(f"❌ Error clearing '{table}': {str(e)}")
            
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def export_data(output_file: str = None):
    """導出當前數據為 SQL 文件"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"backup_data_{timestamp}.sql"
    
    print(f"\n💾 Exporting data to: {output_file}")
    
    try:
        import subprocess
        
        # 構建 mysqldump 命令
        db_url = settings.DATABASE_URL
        # 解析資料庫連接信息
        import re
        match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/(.+)', db_url)
        if match:
            user, password, host, database = match.groups()
            
            cmd = [
                'mysqldump',
                f'-h{host.split(":")[0]}',
                f'-u{user}',
                f'-p{password}',
                '--no-create-info',  # 只導出數據
                '--complete-insert',
                '--skip-extended-insert',
                database
            ]
            
            with open(output_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            print(f"✅ Data exported successfully to {output_file}")
            
            # 顯示文件大小
            file_size = os.path.getsize(output_file)
            print(f"   File size: {file_size:,} bytes")
            
        else:
            print("❌ Could not parse database URL")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Export failed: {str(e)}")
    except FileNotFoundError:
        print("❌ mysqldump command not found. Please install MySQL client tools.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def import_data(input_file: str):
    """從 SQL 文件導入數據"""
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return
    
    print(f"\n📥 Importing data from: {input_file}")
    response = input("This will add data to existing tables. Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    try:
        # 執行 SQL 文件
        results = execute_sql_file(input_file)
        
        print(f"\n✅ Import completed!")
        print(f"   Successful statements: {results['successful']}")
        print(f"   Failed statements: {results['failed']}")
        
        if results['data_inserted']:
            total_rows = sum(item['rows'] for item in results['data_inserted'])
            print(f"   Total rows inserted: {total_rows}")
            
    except Exception as e:
        print(f"❌ Import error: {str(e)}")

def verify_installation() -> bool:
    """
    驗證安裝完整性
    
    Returns:
        bool: 是否通過驗證
    """
    print("\n🔍 Verifying installation...")
    
    # 檢查資料庫狀態
    db_status = check_db_status(detailed=True)
    
    if db_status['status'] != 'healthy':
        print(f"\n❌ Installation verification failed: {db_status['status']}")
        return False
    
    # 檢查關鍵數據
    with engine.connect() as conn:
        checks = {
            'Admin user exists': conn.execute(
                text("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            ).scalar() > 0,
            
            'Roles configured': conn.execute(
                text("SELECT COUNT(*) FROM roles")
            ).scalar() >= 5,
            
            'Permissions configured': conn.execute(
                text("SELECT COUNT(*) FROM permissions")
            ).scalar() >= 20,
            
            'Role permissions configured': conn.execute(
                text("SELECT COUNT(*) FROM role_permissions")
            ).scalar() > 0,
            
            'Vaccine types configured': conn.execute(
                text("SELECT COUNT(*) FROM vaccine_types")
            ).scalar() >= 10,
            
            'Product categories configured': conn.execute(
                text("SELECT COUNT(*) FROM product_categories")
            ).scalar() >= 6
        }
    
    all_passed = all(checks.values())
    
    print("\n📋 Installation Verification:")
    for check, passed in checks.items():
        print(f"   {'✅' if passed else '❌'} {check}")
    
    if all_passed:
        print("\n✅ Installation verification passed!")
    else:
        print("\n❌ Installation verification failed!")
        print("   Run: python init_db.py --init-data")
    
    return all_passed

def execute_sql_file(file_path: str, return_results: bool = True):
    """
    執行 SQL 檔案（保留原有實現）
    """
    print(f"\n📄 Executing SQL file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SQL file not found: {file_path}")
    
    results = {
        'total_statements': 0,
        'successful': 0,
        'failed': 0,
        'errors': [],
        'tables_created': [],
        'data_inserted': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf8') as f:
            sql_content = f.read()
        
        # 分割 SQL 語句
        statements = []
        current_statement = []
        in_string = False
        string_char = None
        
        for line in sql_content.split('\n'):
            stripped_line = line.strip()
            if stripped_line.startswith('--') or stripped_line.startswith('#'):
                continue
            
            for i, char in enumerate(line):
                if char in ["'", '"', '`'] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                if char == ';' and not in_string:
                    current_statement.append(line[:i])
                    statement = '\n'.join(current_statement).strip()
                    if statement:
                        statements.append(statement)
                    current_statement = [line[i+1:]]
                    break
            else:
                current_statement.append(line)
        
        last_statement = '\n'.join(current_statement).strip()
        if last_statement:
            statements.append(last_statement)
        
        # 執行語句
        with engine.begin() as conn:
            for i, statement in enumerate(statements):
                if not statement.strip():
                    continue
                
                results['total_statements'] += 1
                
                try:
                    result = conn.execute(text(statement))
                    results['successful'] += 1
                    
                    statement_upper = statement.upper().strip()
                    if statement_upper.startswith('CREATE TABLE'):
                        table_name = extract_table_name(statement, 'CREATE TABLE')
                        if table_name:
                            results['tables_created'].append(table_name)
                            print(f"✅ Created table: {table_name}")
                    
                    elif statement_upper.startswith('INSERT'):
                        table_name = extract_table_name(statement, 'INSERT')
                        row_count = result.rowcount
                        if table_name:
                            results['data_inserted'].append({
                                'table': table_name,
                                'rows': row_count
                            })
                            if row_count > 0:
                                print(f"✅ Inserted {row_count} rows into {table_name}")
                    
                except SQLAlchemyError as e:
                    results['failed'] += 1
                    error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                    
                    # 忽略某些預期的錯誤
                    if "Duplicate entry" in error_msg or "already exists" in error_msg:
                        print(f"⚠️  Skipped (already exists): Statement {i+1}")
                        continue
                    
                    results['errors'].append({
                        'statement_index': i + 1,
                        'error': error_msg,
                        'statement_preview': statement[:100] + '...' if len(statement) > 100 else statement
                    })
                    print(f"❌ Error in statement {i+1}: {error_msg[:100]}...")
        
        # 輸出總結
        print(f"\n📊 Execution Summary:")
        print(f"   Total statements: {results['total_statements']}")
        print(f"   Successful: {results['successful']}")
        print(f"   Failed: {results['failed']}")
        
        if results['tables_created']:
            print(f"   Tables created: {len(results['tables_created'])}")
        
        if results['data_inserted']:
            total_rows = sum(item['rows'] for item in results['data_inserted'])
            print(f"   Data rows inserted: {total_rows}")
        
        return results
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        results['errors'].append({
            'statement_index': 0,
            'error': f"Fatal error: {str(e)}",
            'statement_preview': 'N/A'
        })
        return results

def extract_table_name(statement: str, statement_type: str) -> str:
    """從 SQL 語句中提取表名（保留原有實現）"""
    import re
    
    if statement_type == 'CREATE TABLE':
        match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', statement, re.IGNORECASE)
        if match:
            return match.group(1)
    
    elif statement_type == 'INSERT':
        match = re.search(r'INSERT\s+(?:IGNORE\s+)?INTO\s+[`"]?(\w+)[`"]?', statement, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def create_default_admin():
    """創建預設管理員帳號"""
    print("\n👤 Creating default admin user...")
    
    with engine.begin() as conn:
        # 檢查是否已存在
        existing = conn.execute(text("SELECT id FROM users WHERE username = 'admin'")).first()
        if existing:
            print("ℹ️  Admin user already exists")
            return
        
        admin_password_hash = get_password_hash("admin123456")
        
        # 插入管理員用戶
        result = conn.execute(text("""
            INSERT INTO users 
            (username, email, password_hash, display_name, is_active, is_verified, created_at, updated_at) 
            VALUES
            ('admin', 'admin@oss.com', :password_hash, '系統管理員', TRUE, TRUE, NOW(), NOW())
        """), {"password_hash": admin_password_hash})
        
        admin_id = result.lastrowid
        
        # 獲取 super_admin 角色 ID
        super_admin_role = conn.execute(text("SELECT id FROM roles WHERE name = 'super_admin'")).first()
        
        if super_admin_role:
            # 分配超級管理員角色
            conn.execute(text("""
                INSERT INTO user_roles (user_id, role_id, assigned_at) 
                VALUES (:user_id, :role_id, NOW())
            """), {"user_id": admin_id, "role_id": super_admin_role.id})
            
            print("✅ Default admin user created successfully!")
            print("📝 Default admin credentials:")
            print("   Username: admin")
            print("   Password: admin123456")
            print("   ⚠️  Please change the password after first login!")

def drop_all_tables():
    """刪除所有表（危險操作，僅用於開發環境）"""
    response = input("⚠️  WARNING: This will delete all tables and data. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        print("🗑️  Dropping all tables...")
        
        # 先禁用外鍵檢查
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 獲取所有表名
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            
            # 刪除所有表
            for table in tables:
                print(f"   Dropping table: {table}")
                conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
            
            # 重新啟用外鍵檢查
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        
        print("✅ All tables dropped!")
    else:
        print("❌ Operation cancelled.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database initialization and management script')
    parser.add_argument('--drop', action='store_true', help='Drop all tables before initialization')
    parser.add_argument('--check', action='store_true', help='Check database status')
    parser.add_argument('--verify', action='store_true', help='Verify installation completeness')
    parser.add_argument('--sql', type=str, help='Initialize tables from SQL file')
    parser.add_argument('--init-data', action='store_true', help='Initialize data from init_data.sql')
    parser.add_argument('--complete', action='store_true', help='Complete installation (tables + data)')
    parser.add_argument('--reset', action='store_true', help='Reset all data (keep tables, reinitialize data)')
    parser.add_argument('--clean', nargs='+', help='Clean specific tables (e.g., --clean posts comments)')
    parser.add_argument('--exportsql', type=str, nargs='?', const='', help='Export current data to SQL file')
    parser.add_argument('--importsql', type=str, help='Import data from SQL file')
    
    args = parser.parse_args()
    
    if args.check:
        check_database()
        check_db_status(detailed=True)
    elif args.verify:
        verify_installation()
    elif args.drop:
        drop_all_tables()
    elif args.reset:
        reset_all_data()
    elif args.clean:
        clean_specific_data(args.clean)
    elif args.exportsql is not None:
        export_data(args.exportsql if args.exportsql else None)
    elif args.importsql :
        import_data(args.importsql)
    elif args.complete:
        # 完整安裝流程
        print("🚀 Starting complete installation...")
        
        # 1. 創建表格
        tables_sql = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'create_tables.sql'
        )
        if os.path.exists(tables_sql):
            print("\n[Step 1/3] Creating tables...")
            execute_sql_file(tables_sql)
        
        # 2. 初始化數據
        data_sql = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'init_data.sql'
        )
        if os.path.exists(data_sql):
            print("\n[Step 2/3] Initializing data...")
            init_data_from_sql(data_sql)
        
        # 3. 驗證安裝
        print("\n[Step 3/3] Verifying installation...")
        verify_installation()
        
    elif args.sql:
        sql_path = args.sql if args.sql != '' else None
        execute_sql_file(sql_path or 'scripts/create_tables.sql')
    elif args.init_data:
        init_data_from_sql()
    else:
        # 預設檢查狀態
        check_database()
        status = check_db_status()
        
        print("\n💡 Available commands:")
        print("   --check         : Check database status")
        print("   --verify        : Verify installation")
        print("   --sql <file>    : Create tables from SQL file")
        print("   --init-data     : Initialize data")
        print("   --complete      : Complete installation (recommended)")
        print("   --reset         : Reset all data (keep tables)")
        print("   --clean <tables>: Clean specific tables")
        print("   --export [file] : Export current data")
        print("   --import <file> : Import data from file")
        print("   --drop          : Drop all tables (dangerous!)")