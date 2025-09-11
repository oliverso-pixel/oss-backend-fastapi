# scripts/init_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, create_engine, inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import settings
from app.core.database import engine, Base
from app.core.security import get_password_hash
from app.models import *
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 完整的表格列表
EXPECTED_TABLES = [
    # 用戶與認證
    'users', 'roles', 'permissions', 'role_permissions', 'user_roles',
    'user_permissions', 'user_tokens', 'token_blacklist',
    
    # 寵物相關
    'pets', 'pet_transfer_history',
    
    # 貼文與媒體
    'posts', 'media', 'post_media', 'albums', 'album_media',
    
    # 社交功能
    'tags', 'post_tags', 'friendships', 'follows', 'likes', 'comments',
    
    # 商戶與商品
    'merchants', 'merchant_documents', 'merchant_reviews',
    'product_categories', 'products', 'product_media',
    'orders', 'order_items',
    
    # 寵物醫療
    'veterinary_clinics', 'clinic_treatable_species', 'clinic_equipment',
    'clinic_services', 'clinic_reviews', 'veterinarians', 
    'veterinarian_schedules', 'veterinarian_special_schedules',
    'vaccine_types', 'pet_medical_records', 'pet_vaccinations', 
    'pet_medications', 'pet_health_reminders',
    
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
    'pet_transfer_history': ['pets', 'users'],
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
    'clinic_treatable_species': ['veterinary_clinics'],
    'clinic_equipment': ['veterinary_clinics'],
    'clinic_services': ['veterinary_clinics'],
    'clinic_reviews': ['veterinary_clinics', 'users', 'pets', 'pet_medical_records'],
    'veterinarians': ['veterinary_clinics'],
    'veterinarian_schedules': ['veterinarians', 'veterinary_clinics'],
    'veterinarian_special_schedules': ['veterinarians', 'veterinary_clinics'],
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
            'unexpected': [],
            'details': {}
        },
        'total_tables': 0,
        'expected_tables': len(EXPECTED_TABLES),
        'total_records': 0,
        'integrity': {
            'foreign_keys': True,
            'indexes': True,
            'constraints': True,
            'orphaned_records': [],
            'missing_references': [],
            'issues': []
        },
        'data_quality': {
            'empty_tables': [],
            'critical_data': {}
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
                    
                    if record_count == 0:
                        results['data_quality']['empty_tables'].append(table)
                        print(f"⚠️  Table '{table}': Empty (0 records)")
                    else:
                        print(f"✅ Table '{table}': {record_count} records, {len(columns)} columns, {len(indexes)} indexes")
            else:
                results['tables']['missing'].append(table)
                results['status'] = 'incomplete'
                print(f"❌ Table '{table}': Missing")
        
        # 3. 檢查意外的表格
        results['tables']['unexpected'] = list(set(existing_tables) - set(EXPECTED_TABLES))
        if results['tables']['unexpected']:
            print(f"\n📌 Unexpected tables found: {', '.join(sorted(results['tables']['unexpected']))}")
        
        # 4. 檢查外鍵完整性
        if detailed:
            print("\n🔍 Checking foreign key integrity...")
            fk_issues = check_foreign_keys_detailed(conn)
            if fk_issues['orphaned_records']:
                results['integrity']['foreign_keys'] = False
                results['integrity']['orphaned_records'] = fk_issues['orphaned_records']
                results['integrity']['issues'].extend([f"Orphaned records in {issue['table']}" for issue in fk_issues['orphaned_records']])
            if fk_issues['missing_references']:
                results['integrity']['missing_references'] = fk_issues['missing_references']
                results['integrity']['issues'].extend(fk_issues['missing_references'])
        
        # 5. 檢查關鍵數據
        if detailed and 'roles' in results['tables']['found']:
            print("\n🔑 Checking critical data...")
            critical_issues = check_critical_data_detailed(conn)
            results['data_quality']['critical_data'] = critical_issues['data']
            if critical_issues['issues']:
                results['integrity']['issues'].extend(critical_issues['issues'])
                if 'No admin users found' in critical_issues['issues']:
                    results['status'] = 'needs_initialization'
        
        # 6. 檢查資料完整性
        if detailed:
            print("\n🔍 Checking data integrity...")
            integrity_issues = check_data_integrity(conn)
            if integrity_issues:
                results['integrity']['issues'].extend(integrity_issues)
                results['status'] = 'unhealthy'
    
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
    
    if results['data_quality']['empty_tables']:
        print(f"   Empty Tables: {len(results['data_quality']['empty_tables'])}")
    
    if results['integrity']['issues']:
        print(f"\n⚠️  Integrity Issues Found:")
        for issue in results['integrity']['issues'][:5]:
            print(f"   - {issue}")
        if len(results['integrity']['issues']) > 5:
            print(f"   ... and {len(results['integrity']['issues']) - 5} more issues")
    
    return results

def check_foreign_keys_detailed(conn) -> Dict:
    """詳細檢查外鍵約束完整性"""
    issues = {
        'orphaned_records': [],
        'missing_references': []
    }
    
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
            
            foreign_keys = list(fk_result)
            
            # 檢查孤立記錄
            for fk in foreign_keys:
                column_name = fk.COLUMN_NAME
                ref_table = fk.REFERENCED_TABLE_NAME
                ref_column = fk.REFERENCED_COLUMN_NAME
                
                # 檢查是否有孤立的記錄
                orphaned = conn.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM `{table}` t1
                    LEFT JOIN `{ref_table}` t2 ON t1.`{column_name}` = t2.`{ref_column}`
                    WHERE t1.`{column_name}` IS NOT NULL 
                    AND t2.`{ref_column}` IS NULL
                """)).scalar()
                
                if orphaned > 0:
                    issues['orphaned_records'].append({
                        'table': table,
                        'column': column_name,
                        'references': f"{ref_table}.{ref_column}",
                        'count': orphaned
                    })
            
            # 檢查是否缺少預期的外鍵
            expected_refs = set(deps)
            actual_refs = set([fk.REFERENCED_TABLE_NAME for fk in foreign_keys])
            missing_refs = expected_refs - actual_refs
            
            if missing_refs:
                issues['missing_references'].append(
                    f"Table '{table}' missing foreign keys to: {', '.join(missing_refs)}"
                )
                
        except Exception as e:
            issues['missing_references'].append(f"Error checking foreign keys for '{table}': {str(e)}")
    
    return issues

def check_critical_data_detailed(conn) -> Dict:
    """詳細檢查關鍵數據是否存在"""
    results = {
        'data': {},
        'issues': []
    }
    
    # 檢查必要的角色
    required_roles = ['super_admin', 'admin', 'user', 'merchant', 'veterinarian']
    role_check = conn.execute(text("""
        SELECT name, COUNT(*) as count 
        FROM roles 
        WHERE name IN :roles
        GROUP BY name
    """), {"roles": tuple(required_roles)})
    
    existing_roles = {row.name: row.count for row in role_check}
    results['data']['roles'] = existing_roles
    
    for role in required_roles:
        if role not in existing_roles:
            results['issues'].append(f"Missing required role: '{role}'")
    
    # 檢查是否有管理員用戶
    admin_check = conn.execute(text("""
        SELECT u.username, r.name as role_name
        FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name IN ('super_admin', 'admin')
    """))
    
    admin_users = list(admin_check)
    results['data']['admin_users'] = [{'username': u.username, 'role': u.role_name} for u in admin_users]
    
    if not admin_users:
        results['issues'].append("No admin users found")
    
    # 檢查權限表
    permission_stats = conn.execute(text("""
        SELECT module, COUNT(*) as count
        FROM permissions
        GROUP BY module
    """))
    
    permission_modules = {row.module: row.count for row in permission_stats}
    results['data']['permission_modules'] = permission_modules
    
    if not permission_modules:
        results['issues'].append("No permissions defined")
    
    # 檢查角色權限配置
    role_permission_check = conn.execute(text("""
        SELECT r.name, COUNT(rp.permission_id) as permission_count
        FROM roles r
        LEFT JOIN role_permissions rp ON r.id = rp.role_id
        GROUP BY r.id, r.name
    """))
    
    role_permissions = {row.name: row.permission_count for row in role_permission_check}
    results['data']['role_permissions'] = role_permissions
    
    # 檢查超級管理員是否有權限
    if 'super_admin' in role_permissions and role_permissions['super_admin'] == 0:
        results['issues'].append("Super admin role has no permissions assigned")
    
    # 檢查基礎數據
    basic_data_checks = [
        ('vaccine_types', "SELECT COUNT(*) FROM vaccine_types", 10, "vaccine types"),
        ('product_categories', "SELECT COUNT(*) FROM product_categories", 5, "product categories"),
        ('tags', "SELECT COUNT(*) FROM tags", 5, "tags")
    ]
    
    for table, query, min_count, description in basic_data_checks:
        count = conn.execute(text(query)).scalar()
        results['data'][table] = count
        if count < min_count:
            results['issues'].append(f"Insufficient {description}: {count} (expected at least {min_count})")
    
    return results

def check_data_integrity(conn) -> List[str]:
    """檢查資料完整性問題"""
    issues = []
    
    # 1. 檢查重複的用戶名或郵箱
    duplicate_check = conn.execute(text("""
        SELECT 'username' as field, username as value, COUNT(*) as count
        FROM users
        GROUP BY username
        HAVING COUNT(*) > 1
        UNION ALL
        SELECT 'email' as field, email as value, COUNT(*) as count
        FROM users
        GROUP BY email
        HAVING COUNT(*) > 1
    """))
    
    for row in duplicate_check:
        issues.append(f"Duplicate {row.field}: {row.value} ({row.count} occurrences)")
    
    # 2. 檢查無效的外鍵引用
    fk_checks = [
        ("user_roles without valid user", """
            SELECT COUNT(*) FROM user_roles ur
            LEFT JOIN users u ON ur.user_id = u.id
            WHERE u.id IS NULL
        """),
        ("user_roles without valid role", """
            SELECT COUNT(*) FROM user_roles ur
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE r.id IS NULL
        """),
        ("posts without valid user", """
            SELECT COUNT(*) FROM posts p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE u.id IS NULL
        """),
        ("pets without valid user", """
            SELECT COUNT(*) FROM pets p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE u.id IS NULL
        """)
    ]
    
    for description, query in fk_checks:
        count = conn.execute(text(query)).scalar()
        if count > 0:
            issues.append(f"{description}: {count} records")
    
    # 3. 檢查資料一致性
    consistency_checks = [
        ("Users with invalid privacy_level", """
            SELECT COUNT(*) FROM users
            WHERE privacy_level NOT IN ('public', 'friends', 'private')
        """),
        ("Posts with invalid visibility", """
            SELECT COUNT(*) FROM posts
            WHERE visibility NOT IN ('public', 'friends', 'private')
        """),
        ("Orders with mismatched totals", """
            SELECT COUNT(*) FROM orders o
            WHERE ABS(o.total - (o.subtotal + o.shipping_fee + o.tax)) > 0.01
        """)
    ]
    
    for description, query in consistency_checks:
        try:
            count = conn.execute(text(query)).scalar()
            if count > 0:
                issues.append(f"{description}: {count} records")
        except:
            pass  # 表可能不存在
    
    # 4. 檢查時間邏輯
    time_checks = [
        ("Future created_at dates", """
            SELECT table_name, COUNT(*) as count
            FROM (
                SELECT 'users' as table_name FROM users WHERE created_at > NOW()
                UNION ALL
                SELECT 'posts' as table_name FROM posts WHERE created_at > NOW()
                UNION ALL
                SELECT 'orders' as table_name FROM orders WHERE created_at > NOW()
            ) t
            GROUP BY table_name
        """)
    ]
    
    for description, query in time_checks:
        try:
            result = conn.execute(text(query))
            for row in result:
                if row.count > 0:
                    issues.append(f"{description} in {row.table_name}: {row.count} records")
        except:
            pass
    
    return issues

def generate_integrity_report(output_file: str = None):
    """生成詳細的資料庫完整性報告"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"db_integrity_report_{timestamp}.txt"
    
    print(f"\n📝 Generating integrity report...")
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"Database Integrity Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    
    # 執行完整檢查
    status = check_db_status(detailed=True)
    
    # 基本信息
    report_lines.append("\n## Database Overview")
    report_lines.append(f"Status: {status['status'].upper()}")
    report_lines.append(f"Total Tables: {status['total_tables']} (Expected: {status['expected_tables']})")
    report_lines.append(f"Total Records: {status['total_records']}")
    
    # 表格狀態
    report_lines.append("\n## Table Status")
    report_lines.append(f"Found: {len(status['tables']['found'])}")
    report_lines.append(f"Missing: {len(status['tables']['missing'])}")
    report_lines.append(f"Unexpected: {len(status['tables']['unexpected'])}")
    
    if status['tables']['missing']:
        report_lines.append("\n### Missing Tables:")
        for table in status['tables']['missing']:
            report_lines.append(f"  - {table}")
    
    if status['tables']['unexpected']:
        report_lines.append("\n### Unexpected Tables:")
        for table in status['tables']['unexpected']:
            report_lines.append(f"  - {table}")
    
    # 表格詳情
    report_lines.append("\n## Table Details")
    for table in sorted(status['tables']['found']):
        details = status['tables']['details'].get(table, {})
        report_lines.append(f"\n### {table}")
        report_lines.append(f"  Records: {details.get('records', 0)}")
        report_lines.append(f"  Columns: {details.get('columns', 0)}")
        report_lines.append(f"  Indexes: {details.get('indexes', 0)}")
    
    # 資料品質
    report_lines.append("\n## Data Quality")
    if status['data_quality']['empty_tables']:
        report_lines.append(f"\n### Empty Tables ({len(status['data_quality']['empty_tables'])}):")
        for table in status['data_quality']['empty_tables']:
            report_lines.append(f"  - {table}")
    
    # 完整性問題
    if status['integrity']['issues']:
        report_lines.append("\n## Integrity Issues")
        for issue in status['integrity']['issues']:
            report_lines.append(f"  - {issue}")
    
    # 孤立記錄
    if status['integrity']['orphaned_records']:
        report_lines.append("\n## Orphaned Records")
        for orphan in status['integrity']['orphaned_records']:
            report_lines.append(f"  - {orphan['table']}.{orphan['column']} -> {orphan['references']}: {orphan['count']} records")
    
    # 寫入檔案
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✅ Report saved to: {output_file}")
    
    # 顯示摘要
    print("\n📊 Report Summary:")
    print(f"   Status: {status['status'].upper()}")
    print(f"   Total Issues: {len(status['integrity']['issues'])}")
    if status['integrity']['orphaned_records']:
        total_orphans = sum(o['count'] for o in status['integrity']['orphaned_records'])
        print(f"   Orphaned Records: {total_orphans}")

def fix_common_issues(dry_run: bool = True):
    """修復常見的資料庫問題"""
    print(f"\n🔧 {'Checking' if dry_run else 'Fixing'} common database issues...")
    
    fixes_applied = []
    
    with engine.begin() as conn:
        # 1. 刪除孤立的記錄
        orphan_queries = [
            ("user_roles", "DELETE ur FROM user_roles ur LEFT JOIN users u ON ur.user_id = u.id WHERE u.id IS NULL"),
            ("user_roles", "DELETE ur FROM user_roles ur LEFT JOIN roles r ON ur.role_id = r.id WHERE r.id IS NULL"),
            ("posts", "DELETE p FROM posts p LEFT JOIN users u ON p.user_id = u.id WHERE u.id IS NULL"),
            ("pets", "DELETE p FROM pets p LEFT JOIN users u ON p.user_id = u.id WHERE u.id IS NULL")
        ]
        
        for table, query in orphan_queries:
            try:
                if dry_run:
                    check_query = query.replace("DELETE", "SELECT COUNT(*) as count FROM", 1)
                    count = conn.execute(text(check_query)).scalar()
                    if count > 0:
                        print(f"  Would delete {count} orphaned records from {table}")
                        fixes_applied.append(f"Delete {count} orphaned records from {table}")
                else:
                    result = conn.execute(text(query))
                    if result.rowcount > 0:
                        print(f"  ✅ Deleted {result.rowcount} orphaned records from {table}")
                        fixes_applied.append(f"Deleted {result.rowcount} orphaned records from {table}")
            except Exception as e:
                print(f"  ⚠️  Error processing {table}: {str(e)}")
        
        # 2. 修復缺失的預設值
        default_fixes = [
            ("UPDATE users SET created_at = NOW() WHERE created_at IS NULL", "users.created_at"),
            ("UPDATE users SET updated_at = NOW() WHERE updated_at IS NULL", "users.updated_at"),
            ("UPDATE users SET is_active = TRUE WHERE is_active IS NULL", "users.is_active"),
            ("UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL", "users.is_verified")
        ]
        
        for query, field in default_fixes:
            try:
                if dry_run:
                    check_query = query.replace("UPDATE", "SELECT COUNT(*) as count FROM", 1).split("SET")[0] + " WHERE " + query.split("WHERE")[1]
                    count = conn.execute(text(check_query)).scalar()
                    if count > 0:
                        print(f"  Would fix {count} NULL values in {field}")
                        fixes_applied.append(f"Fix {count} NULL values in {field}")
                else:
                    result = conn.execute(text(query))
                    if result.rowcount > 0:
                        print(f"  ✅ Fixed {result.rowcount} NULL values in {field}")
                        fixes_applied.append(f"Fixed {result.rowcount} NULL values in {field}")
            except Exception as e:
                print(f"  ⚠️  Error fixing {field}: {str(e)}")
    
    if dry_run:
        print(f"\n💡 Dry run complete. {len(fixes_applied)} issues found.")
        if fixes_applied:
            print("   Run with --fix-issues to apply these fixes.")
    else:
        print(f"\n✅ Fixed {len(fixes_applied)} issues.")
    
    return fixes_applied

def verify_installation() -> bool:
    """
    驗證安裝完整性
    
    Returns:
        bool: 是否通過驗證
    """
    print("\n🔍 Verifying installation...")
    
    # 檢查資料庫狀態
    db_status = check_db_status(detailed=True)
    
    # 定義驗證規則
    verification_rules = {
        'critical': {
            'All tables exist': len(db_status['tables']['missing']) == 0,
            'Admin user exists': any('admin' in str(issue).lower() for issue in db_status['integrity']['issues']) == False,
            'Roles configured': db_status['data_quality']['critical_data'].get('roles', {}) and len(db_status['data_quality']['critical_data']['roles']) >= 3,
            'Permissions configured': sum(db_status['data_quality']['critical_data'].get('permission_modules', {}).values()) >= 20,
        },
        'important': {
            'No orphaned records': len(db_status['integrity'].get('orphaned_records', [])) == 0,
            'Role permissions assigned': all(count > 0 for role, count in db_status['data_quality']['critical_data'].get('role_permissions', {}).items() if role in ['super_admin', 'admin']),
            'Basic data initialized': all(db_status['data_quality']['critical_data'].get(table, 0) > 0 for table in ['vaccine_types', 'product_categories']),
        },
        'recommended': {
            'No empty critical tables': not any(table in ['users', 'roles', 'permissions'] for table in db_status['data_quality']['empty_tables']),
            'Test users created': db_status['tables']['details'].get('users', {}).get('records', 0) > 1,
            'Sample data exists': db_status['total_records'] > 100,
        }
    }
    
    # 評估每個類別
    results = {}
    for category, rules in verification_rules.items():
        results[category] = {rule: passed for rule, passed in rules.items()}
    
    # 顯示結果
    print("\n📋 Installation Verification Results:")
    
    all_critical_passed = all(results['critical'].values())
    all_important_passed = all(results['important'].values())
    all_recommended_passed = all(results['recommended'].values())
    
    print("\n### Critical Requirements:")
    for rule, passed in results['critical'].items():
        print(f"   {'✅' if passed else '❌'} {rule}")
    
    print("\n### Important Requirements:")
    for rule, passed in results['important'].items():
        print(f"   {'✅' if passed else '⚠️'} {rule}")
    
    print("\n### Recommended:")
    for rule, passed in results['recommended'].items():
        print(f"   {'✅' if passed else 'ℹ️'} {rule}")
    
    # 總體評估
    if all_critical_passed and all_important_passed:
        print("\n✅ Installation verification PASSED!")
        return True
    elif all_critical_passed:
        print("\n⚠️  Installation is functional but has some issues.")
        print("   Run: python init_db.py --fix-issues")
        return True
    else:
        print("\n❌ Installation verification FAILED!")
        print("   Critical requirements not met. Please check the issues above.")
        return False

# 保留原有函數...
def init_data_from_sql(sql_file_path: str = None) -> Dict:
    """從 SQL 檔案初始化數據"""
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
    
    return results

def execute_sql_file(file_path: str, return_results: bool = True):
    """執行 SQL 檔案（保留原有實現）"""
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
        delimiter = ';'
        
        for line in sql_content.split('\n'):
            stripped_line = line.strip()
            
            # 處理 DELIMITER 命令
            if stripped_line.upper().startswith('DELIMITER'):
                new_delimiter = stripped_line.split()[1]
                if new_delimiter != delimiter:
                    # 完成當前語句
                    if current_statement:
                        statement = '\n'.join(current_statement).strip()
                        if statement:
                            statements.append(statement)
                        current_statement = []
                    delimiter = new_delimiter
                continue
            
            if stripped_line.startswith('--') or stripped_line.startswith('#'):
                continue
            
            # 檢查是否包含分隔符
            if delimiter in line and not in_string:
                parts = line.split(delimiter)
                for i, part in enumerate(parts[:-1]):
                    current_statement.append(part)
                    statement = '\n'.join(current_statement).strip()
                    if statement:
                        statements.append(statement)
                    current_statement = []
                current_statement = [parts[-1]] if parts[-1].strip() else []
            else:
                current_statement.append(line)
            
            # 追蹤字符串狀態
            for i, char in enumerate(line):
                if char in ["'", '"', '`'] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
        
        # 處理最後的語句
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement)
        
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
                    
                    elif statement_upper.startswith('CREATE FUNCTION'):
                        print(f"✅ Created function")
                    
                    elif statement_upper.startswith('CREATE VIEW'):
                        print(f"✅ Created view")
                        
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
    """從 SQL 語句中提取表名"""
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

def drop_all_tables():
    """刪除所有表、視圖、函數和其他資料庫物件（危險操作，僅用於開發環境）"""
    response = input("⚠️  WARNING: This will delete all tables, views, functions and data. Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    # 二次確認
    response = input("⚠️  FINAL WARNING: Type 'DROP EVERYTHING' to confirm: ")
    if response != 'DROP EVERYTHING':
        print("❌ Operation cancelled.")
        return
    
    print("🗑️  Dropping all database objects...")
    
    try:
        with engine.begin() as conn:
            # 先禁用外鍵檢查
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 1. 刪除所有視圖
            print("\n📐 Dropping views...")
            result = conn.execute(text("""
                SELECT TABLE_NAME 
                FROM information_schema.VIEWS 
                WHERE TABLE_SCHEMA = DATABASE()
            """))
            views = [row[0] for row in result]
            
            for view in views:
                try:
                    print(f"   Dropping view: {view}")
                    conn.execute(text(f"DROP VIEW IF EXISTS `{view}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping view {view}: {str(e)}")
            
            if views:
                print(f"   ✅ Dropped {len(views)} views")
            else:
                print(f"   ℹ️  No views found")
            
            # 2. 刪除所有函數
            print("\n🔧 Dropping functions...")
            result = conn.execute(text("""
                SELECT ROUTINE_NAME 
                FROM information_schema.ROUTINES 
                WHERE ROUTINE_SCHEMA = DATABASE() 
                AND ROUTINE_TYPE = 'FUNCTION'
            """))
            functions = [row[0] for row in result]
            
            for function in functions:
                try:
                    print(f"   Dropping function: {function}")
                    conn.execute(text(f"DROP FUNCTION IF EXISTS `{function}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping function {function}: {str(e)}")
            
            if functions:
                print(f"   ✅ Dropped {len(functions)} functions")
            else:
                print(f"   ℹ️  No functions found")
            
            # 3. 刪除所有存儲過程
            print("\n📦 Dropping procedures...")
            result = conn.execute(text("""
                SELECT ROUTINE_NAME 
                FROM information_schema.ROUTINES 
                WHERE ROUTINE_SCHEMA = DATABASE() 
                AND ROUTINE_TYPE = 'PROCEDURE'
            """))
            procedures = [row[0] for row in result]
            
            for procedure in procedures:
                try:
                    print(f"   Dropping procedure: {procedure}")
                    conn.execute(text(f"DROP PROCEDURE IF EXISTS `{procedure}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping procedure {procedure}: {str(e)}")
            
            if procedures:
                print(f"   ✅ Dropped {len(procedures)} procedures")
            else:
                print(f"   ℹ️  No procedures found")
            
            # 4. 刪除所有觸發器
            print("\n⚡ Dropping triggers...")
            result = conn.execute(text("""
                SELECT TRIGGER_NAME 
                FROM information_schema.TRIGGERS 
                WHERE TRIGGER_SCHEMA = DATABASE()
            """))
            triggers = [row[0] for row in result]
            
            for trigger in triggers:
                try:
                    print(f"   Dropping trigger: {trigger}")
                    conn.execute(text(f"DROP TRIGGER IF EXISTS `{trigger}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping trigger {trigger}: {str(e)}")
            
            if triggers:
                print(f"   ✅ Dropped {len(triggers)} triggers")
            else:
                print(f"   ℹ️  No triggers found")
            
            # 5. 刪除所有表
            print("\n📊 Dropping tables...")
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            
            # 過濾掉視圖（如果還有的話）
            actual_tables = []
            for table in tables:
                table_type = conn.execute(text(f"""
                    SELECT TABLE_TYPE 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = '{table}'
                """)).scalar()
                
                if table_type == 'BASE TABLE':
                    actual_tables.append(table)
            
            # 按照反向依賴順序刪除表
            # 先嘗試刪除所有表，如果失敗則單獨處理
            for table in actual_tables:
                try:
                    print(f"   Dropping table: {table}")
                    conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping table {table}: {str(e)}")
            
            if actual_tables:
                print(f"   ✅ Dropped {len(actual_tables)} tables")
            else:
                print(f"   ℹ️  No tables found")
            
            # 6. 刪除所有事件（如果有的話）
            print("\n⏰ Dropping events...")
            result = conn.execute(text("""
                SELECT EVENT_NAME 
                FROM information_schema.EVENTS 
                WHERE EVENT_SCHEMA = DATABASE()
            """))
            events = [row[0] for row in result]
            
            for event in events:
                try:
                    print(f"   Dropping event: {event}")
                    conn.execute(text(f"DROP EVENT IF EXISTS `{event}`"))
                except Exception as e:
                    print(f"   ⚠️  Error dropping event {event}: {str(e)}")
            
            if events:
                print(f"   ✅ Dropped {len(events)} events")
            else:
                print(f"   ℹ️  No events found")
            
            # 重新啟用外鍵檢查
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # 顯示摘要
            print("\n📊 Drop Summary:")
            total_objects = len(views) + len(functions) + len(procedures) + len(triggers) + len(actual_tables) + len(events)
            print(f"   Total objects dropped: {total_objects}")
            print(f"   - Views: {len(views)}")
            print(f"   - Functions: {len(functions)}")
            print(f"   - Procedures: {len(procedures)}")
            print(f"   - Triggers: {len(triggers)}")
            print(f"   - Tables: {len(actual_tables)}")
            print(f"   - Events: {len(events)}")
            
            print("\n✅ All database objects dropped successfully!")
            
    except Exception as e:
        print(f"❌ Error during drop operation: {str(e)}")
        # 嘗試重新啟用外鍵檢查
        try:
            with engine.connect() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        except:
            pass

def list_all_db_objects():
    """列出所有資料庫物件（用於檢查）"""
    print("\n📋 Listing all database objects...")
    
    try:
        with engine.connect() as conn:
            # 1. 列出所有表
            result = conn.execute(text("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_TYPE, TABLE_NAME
            """))
            tables = list(result)
            
            if tables:
                print("\n📊 Tables and Views:")
                for table_name, table_type in tables:
                    print(f"   [{table_type}] {table_name}")
            
            # 2. 列出所有函數和存儲過程
            result = conn.execute(text("""
                SELECT ROUTINE_NAME, ROUTINE_TYPE 
                FROM information_schema.ROUTINES 
                WHERE ROUTINE_SCHEMA = DATABASE()
                ORDER BY ROUTINE_TYPE, ROUTINE_NAME
            """))
            routines = list(result)
            
            if routines:
                print("\n🔧 Functions and Procedures:")
                for routine_name, routine_type in routines:
                    print(f"   [{routine_type}] {routine_name}")
            
            # 3. 列出所有觸發器
            result = conn.execute(text("""
                SELECT TRIGGER_NAME, EVENT_OBJECT_TABLE, EVENT_MANIPULATION 
                FROM information_schema.TRIGGERS 
                WHERE TRIGGER_SCHEMA = DATABASE()
                ORDER BY EVENT_OBJECT_TABLE, TRIGGER_NAME
            """))
            triggers = list(result)
            
            if triggers:
                print("\n⚡ Triggers:")
                for trigger_name, table_name, event in triggers:
                    print(f"   {trigger_name} (on {table_name} {event})")
            
            # 4. 列出所有事件
            result = conn.execute(text("""
                SELECT EVENT_NAME, STATUS 
                FROM information_schema.EVENTS 
                WHERE EVENT_SCHEMA = DATABASE()
                ORDER BY EVENT_NAME
            """))
            events = list(result)
            
            if events:
                print("\n⏰ Events:")
                for event_name, status in events:
                    print(f"   {event_name} ({status})")
            
            # 顯示總計
            print("\n📊 Summary:")
            print(f"   Total objects: {len(tables) + len(routines) + len(triggers) + len(events)}")
            
    except Exception as e:
        print(f"❌ Error listing objects: {str(e)}")

def clean_db_objects(object_types: List[str] = None):
    """選擇性清理特定類型的資料庫物件"""
    valid_types = ['tables', 'views', 'functions', 'procedures', 'triggers', 'events']
    
    if not object_types:
        print(f"❌ Please specify object types to clean: {', '.join(valid_types)}")
        return
    
    invalid_types = [t for t in object_types if t not in valid_types]
    if invalid_types:
        print(f"❌ Invalid object types: {', '.join(invalid_types)}")
        print(f"   Valid types: {', '.join(valid_types)}")
        return
    
    print(f"\n🧹 Cleaning database objects: {', '.join(object_types)}")
    response = input("Are you sure? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    try:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            cleaned_count = 0
            
            if 'views' in object_types:
                result = conn.execute(text("""
                    SELECT TABLE_NAME 
                    FROM information_schema.VIEWS 
                    WHERE TABLE_SCHEMA = DATABASE()
                """))
                views = [row[0] for row in result]
                
                for view in views:
                    conn.execute(text(f"DROP VIEW IF EXISTS `{view}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(views)} views")
            
            if 'functions' in object_types:
                result = conn.execute(text("""
                    SELECT ROUTINE_NAME 
                    FROM information_schema.ROUTINES 
                    WHERE ROUTINE_SCHEMA = DATABASE() 
                    AND ROUTINE_TYPE = 'FUNCTION'
                """))
                functions = [row[0] for row in result]
                
                for function in functions:
                    conn.execute(text(f"DROP FUNCTION IF EXISTS `{function}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(functions)} functions")
            
            if 'procedures' in object_types:
                result = conn.execute(text("""
                    SELECT ROUTINE_NAME 
                    FROM information_schema.ROUTINES 
                    WHERE ROUTINE_SCHEMA = DATABASE() 
                    AND ROUTINE_TYPE = 'PROCEDURE'
                """))
                procedures = [row[0] for row in result]
                
                for procedure in procedures:
                    conn.execute(text(f"DROP PROCEDURE IF EXISTS `{procedure}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(procedures)} procedures")
            
            if 'triggers' in object_types:
                result = conn.execute(text("""
                    SELECT TRIGGER_NAME 
                    FROM information_schema.TRIGGERS 
                    WHERE TRIGGER_SCHEMA = DATABASE()
                """))
                triggers = [row[0] for row in result]
                
                for trigger in triggers:
                    conn.execute(text(f"DROP TRIGGER IF EXISTS `{trigger}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(triggers)} triggers")
            
            if 'events' in object_types:
                result = conn.execute(text("""
                    SELECT EVENT_NAME 
                    FROM information_schema.EVENTS 
                    WHERE EVENT_SCHEMA = DATABASE()
                """))
                events = [row[0] for row in result]
                
                for event in events:
                    conn.execute(text(f"DROP EVENT IF EXISTS `{event}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(events)} events")
            
            if 'tables' in object_types:
                result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                
                actual_tables = []
                for table in tables:
                    table_type = conn.execute(text(f"""
                        SELECT TABLE_TYPE 
                        FROM information_schema.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table}'
                    """)).scalar()
                    
                    if table_type == 'BASE TABLE':
                        actual_tables.append(table)
                
                for table in actual_tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                    cleaned_count += 1
                print(f"✅ Dropped {len(actual_tables)} tables")
            
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            print(f"\n✅ Total objects cleaned: {cleaned_count}")
            
    except Exception as e:
        print(f"❌ Error during cleaning: {str(e)}")

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
    parser.add_argument('--exportSQL', type=str, nargs='?', const='', help='Export current data to SQL file')
    parser.add_argument('--importSQL', type=str, help='Import data from SQL file')
    parser.add_argument('--report', type=str, nargs='?', const='', help='Generate integrity report')
    parser.add_argument('--fix-issues', action='store_true', help='Fix common database issues')
    parser.add_argument('--check-issues', action='store_true', help='Check for common issues (dry run)')
    parser.add_argument('--list-objects', action='store_true', help='List all database objects')
    parser.add_argument('--clean-objects', nargs='+', choices=['tables', 'views', 'functions', 'procedures', 'triggers', 'events'], help='Clean specific types of database objects')
    
    args = parser.parse_args()
    
    if args.check:
        check_database()
        check_db_status(detailed=True)
    elif args.verify:
        verify_installation()
    elif args.report is not None:
        generate_integrity_report(args.report if args.report else None)
    elif args.check_issues:
        fix_common_issues(dry_run=True)
    elif args.fix_issues:
        fix_common_issues(dry_run=False)
    elif args.drop:
        drop_all_tables()
    elif args.reset:
        reset_all_data()
    elif args.clean:
        clean_specific_data(args.clean)
    elif args.exportSQL is not None:
        export_data(args.exportSQL if args.exportSQL else None)
    elif args.importSQL:
        import_data(args.importSQL)
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
        execute_sql_file(args.sql)
    elif args.init_data:
        init_data_from_sql()
    elif args.list_objects:
        list_all_db_objects()
    elif args.clean_objects:
        clean_db_objects(args.clean_objects)
    else:
        # 預設檢查狀態
        check_database()
        status = check_db_status()
        
        print("\n💡 Available commands:")
        print("   --check         : Check database status")
        print("   --verify        : Verify installation")
        print("   --report [file] : Generate integrity report")
        print("   --check-issues  : Check for common issues")
        print("   --fix-issues    : Fix common issues")
        print("   --sql <file>    : Create tables from SQL file")
        print("   --init-data     : Initialize data")
        print("   --complete      : Complete installation (recommended)")
        print("   --reset         : Reset all data (keep tables)")
        print("   --clean <tables>: Clean specific tables")
        print("   --exportSQL [file] : Export current data")
        print("   --importSQL <file> : Import data from file")
        print("   --drop          : Drop all tables (dangerous!)")