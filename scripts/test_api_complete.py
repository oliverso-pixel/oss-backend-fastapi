# scripts/test_api_complete.py
import requests
import json
import sys
import os
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import random
import string
import jwt

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class CompletePetSocialAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.access_token = None
        self.refresh_token = None
        self.test_user = None
        self.test_user_id = None
        self.test_pet_id = None
        self.test_post_id = None
        self.test_album_id = None
        self.test_media_id = None
        self.test_product_id = None
        self.test_order_id = None
        self.admin_token = None
        
        # 用於測試非管理員訪問的普通用戶
        self.normal_user_token = None
        self.normal_user = None
        
        # Test results tracking
        self.test_results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def print_result(self, success: bool, message: str, details: Any = None):
        """統一的結果輸出格式"""
        self.test_results['total'] += 1
        if success:
            self.test_results['passed'] += 1
            symbol = "✅"
        else:
            self.test_results['failed'] += 1
            symbol = "❌"
            self.test_results['errors'].append(message)
        
        print(f"{symbol} {message}")
        if details:
            if isinstance(details, (dict, list)):
                print(f"  Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
            else:
                print(f"  Details: {details}")
    
    def print_section(self, title: str):
        """打印測試區段標題"""
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print(f"{'='*60}")
    
    def generate_random_string(self, length: int = 8) -> str:
        """生成隨機字符串"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    # ========== 基礎連接測試 ==========
    
    def test_basic_connectivity(self):
        """測試基礎連接"""
        self.print_section("Basic Connectivity Tests")
        
        # Health check
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.print_result(True, "Health check passed", response.json())
            else:
                self.print_result(False, f"Health check failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Health check error: {str(e)}")
        
        # Root endpoint
        try:
            response = requests.get(f"{self.base_url}/")
            self.print_result(response.status_code == 200, "Root endpoint working")
            
            response = requests.get(f"{self.api_v1}")
            self.print_result(response.status_code == 200, "API v1 root working")
        except Exception as e:
            self.print_result(False, f"Root endpoint error: {str(e)}")
    
    # ========== 認證測試 ==========
    
    def test_authentication_flow(self):
        """完整的認證流程測試"""
        self.print_section("Authentication Flow Tests")
        
        # 1. 註冊新用戶
        unique_id = self.generate_random_string()
        register_data = {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "TestPassword123!",
            "display_name": f"Test User {unique_id}",
            "bio": "This is a test user created by API tester",
            "phone": "+886912345678"
        }
        
        try:
            response = requests.post(f"{self.api_v1}/auth/register", json=register_data)
            if response.status_code == 200:
                user_data = response.json()
                self.test_user = register_data
                self.test_user_id = user_data.get("id")
                self.print_result(True, f"User registered: {register_data['username']}")
            else:
                self.print_result(False, f"Registration failed: {response.status_code}", response.text)
                return
        except Exception as e:
            self.print_result(False, f"Registration error: {str(e)}")
            return
        
        # 2. 登入
        try:
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={
                    "username": self.test_user["username"],
                    "password": self.test_user["password"]
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
                self.print_result(True, "Login successful")
                
                # 保存為普通用戶 token
                self.normal_user_token = self.access_token
                self.normal_user = self.test_user.copy()
            else:
                self.print_result(False, f"Login failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Login error: {str(e)}")
        
        # 3. 獲取當前用戶信息
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                self.print_result(response.status_code == 200, "Get current user info")
            except Exception as e:
                self.print_result(False, f"Get user error: {str(e)}")

        # 4. 測試 Logout
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
                if response.status_code == 200:
                    self.print_result(True, "Logout successful")
                    
                    # 測試 logout 後 token 是否失效
                    response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                    if response.status_code == 401:
                        self.print_result(
                            True,
                            "Token properly invalidated after logout"
                        )
                    else:
                        self.print_result(
                            False,
                            f"Token efficient after logout, response code: {response.status_code}"
                        )
                else:
                    self.print_result(False, f"Logout failed: {response.status_code}")
            except Exception as e:
                self.print_result(False, f"Logout error: {str(e)}")
            
            # 重新登入以繼續測試
            try:
                response = requests.post(
                    f"{self.api_v1}/auth/login",
                    data={
                        "username": self.test_user["username"],
                        "password": self.test_user["password"]
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    self.print_result(True, "Re-login after logout successful")
            except Exception as e:
                self.print_result(False, f"Re-login error: {str(e)}")
        
        # 5. 刷新令牌
        if self.refresh_token:
            try:
                response = requests.post(
                    f"{self.api_v1}/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                if response.status_code == 200:
                    new_tokens = response.json()
                    self.access_token = new_tokens.get("access_token")
                    self.print_result(True, "Token refreshed")
                else:
                    self.print_result(False, "Token refresh failed")
            except Exception as e:
                self.print_result(False, f"Token refresh error: {str(e)}")

        
        # 6. 修改密碼
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                response = requests.post(
                    f"{self.api_v1}/auth/change-password",
                    json={
                        "old_password": self.test_user["password"],
                        "new_password": "NewPassword123!"
                    },
                    headers=headers
                )
                if response.status_code == 200:
                    self.print_result(True, "Password changed")
                    self.test_user["password"] = "NewPassword123!"
                    
                    # 測試舊 token 是否失效
                    # time.sleep(1)  # 等待一秒確保處理完成
                    # response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                    # if response.status_code == 401:
                    #     self.print_result(
                    #         True,
                    #         "Old tokens invalidated after password change"
                    #     )
                    # else:
                    #     self.print_result(
                    #         False,
                    #         f"Old tokens efficient after password change, response code: {response.status_code}"
                    #     )

                    time.sleep(2)
            
                    # 4. 測試舊 token 是否失效
                    response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                    if response.status_code == 401:
                        self.print_result(True, "Old token properly invalidated after password change")
                        
                        # 5. 用新密碼登入
                        response = requests.post(
                            f"{self.api_v1}/auth/login",
                            data={
                                "username": self.test_user["username"],
                                "password": "NewPassword123!"
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )
                        
                        if response.status_code == 200:
                            new_tokens = response.json()
                            new_access_token = new_tokens.get("access_token")
                            
                            # 6. 測試新 token 是否有效
                            new_headers = {"Authorization": f"Bearer {new_access_token}"}
                            response = requests.get(f"{self.api_v1}/users/me", headers=new_headers)
                            
                            self.print_result(
                                response.status_code == 200,
                                "New token works after password change"
                            )
                            
                            # 更新 token 供後續測試使用
                            self.access_token = new_access_token
                            self.refresh_token = new_tokens.get("refresh_token")
                        else:
                            self.print_result(False, "Failed to login with new password")
                    else:
                        self.print_result(
                            False,
                            f"Old token still valid after password change (status: {response.status_code})"
                        )
                        
                        # 嘗試獲取更多調試信息
                        response = requests.get(
                            f"{self.api_v1}/auth/token/status",
                            headers=headers
                        )
                        if response.status_code == 200:
                            print(f"  Token status: {json.dumps(response.json(), indent=2)}")
                else:
                    self.print_result(False, f"Password change failed: {response.status_code}")
            except Exception as e:
                self.print_result(False, f"Password change error: {str(e)}")

        self.normal_user_token = self.access_token
        self.test_logout()

    # ========== 管理員功能測試 ==========
    
    def test_admin_features(self):
        """測試管理員功能"""
        self.print_section("Admin Features Tests")
        
        # 嘗試以管理員身份登入
        try:
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={"username": "admin", "password": "admin123456"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                self.admin_token = response.json().get("access_token")
                self.print_result(True, "Admin login successful")
            else:
                self.print_result(False, "Admin login failed")
                return
        except Exception as e:
            self.print_result(False, f"Admin login error: {str(e)}")
            return
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # 1. 獲取儀表板
        try:
            response = requests.get(f"{self.api_v1}/admin/dashboard", headers=headers)
            self.print_result(response.status_code == 200, "Get admin dashboard")
        except Exception as e:
            self.print_result(False, f"Dashboard error: {str(e)}")
        
        # 2. 獲取系統統計
        try:
            response = requests.get(f"{self.api_v1}/admin/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self.print_result(True, "Get system stats", {
                    "total_users": stats.get("total_users"),
                    "total_pets": stats.get("total_pets"),
                    "total_posts": stats.get("total_posts")
                })
            else:
                self.print_result(False, "Get stats failed")
        except Exception as e:
            self.print_result(False, f"Stats error: {str(e)}")
        
        # 3. 獲取待審核商戶
        try:
            response = requests.get(
                f"{self.api_v1}/admin/merchants/pending",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Get pending merchants")
        except Exception as e:
            self.print_result(False, f"Pending merchants error: {str(e)}")
        
        # 4. 獲取審計日誌
        try:
            response = requests.get(
                f"{self.api_v1}/admin/audit-logs?page=1&per_page=10",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Get audit logs")
        except Exception as e:
            self.print_result(False, f"Audit logs error: {str(e)}")

        # 5. 管理用戶（使用管理員權限）
        if self.test_user_id:
            try:
                # 停用用戶
                response = requests.post(
                    f"{self.api_v1}/admin/users/{self.test_user_id}/manage?action=deactivate&reason=test",
                    headers=headers
                )
                self.print_result(
                    response.status_code == 200,
                    "Admin can deactivate users"
                )
                
                # 重新啟用用戶
                response = requests.post(
                    f"{self.api_v1}/admin/users/{self.test_user_id}/manage?action=activate",
                    headers=headers
                )
                self.print_result(
                    response.status_code == 200,
                    "Admin can activate users"
                )
            except Exception as e:
                self.print_result(False, f"User management error: {str(e)}")
        
        # 6. 測試管理員登出
        try:
            response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
            if response.status_code == 200:
                self.print_result(True, "Admin logout successful")
                
                # 驗證登出後無法訪問管理功能
                response = requests.get(f"{self.api_v1}/admin/dashboard", headers=headers)
                self.print_result(
                    response.status_code == 401,
                    "Admin token invalidated after logout"
                )
            else:
                self.print_result(False, "Admin logout failed")
        except Exception as e:
            self.print_result(False, f"Admin logout error: {str(e)}")
    
    # ========== Token 過期測試 ==========
    
    def test_token_expiration(self):
        """測試 Token 過期處理"""
        self.print_section("Token Expiration Tests")
        
        if not self.access_token:
            print("⚠️  Skipping token expiration tests: No access token")
            return
        
        # 1. 創建一個過期的 token（模擬）
        # 注意：這需要知道你的 JWT secret key，在實際測試中可能需要調整
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        try:
            response = requests.get(f"{self.api_v1}/users/me", headers=headers)
            self.print_result(
                response.status_code == 401,
                "Expired token properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Expired token test error: {str(e)}")
        
        # 2. 測試 refresh token 過期處理
        expired_refresh_token = "expired_refresh_token_12345"
        try:
            response = requests.post(
                f"{self.api_v1}/auth/refresh",
                json={"refresh_token": expired_refresh_token}
            )
            self.print_result(
                response.status_code == 401,
                "Expired refresh token properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Expired refresh token test error: {str(e)}")
        
        # 3. 測試 token 格式錯誤
        malformed_token = "this.is.not.a.valid.jwt.token"
        headers = {"Authorization": f"Bearer {malformed_token}"}
        
        try:
            response = requests.get(f"{self.api_v1}/users/me", headers=headers)
            self.print_result(
                response.status_code == 401,
                "Malformed token properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Malformed token test error: {str(e)}")

    # ========== 權限測試 ==========
    
    def test_permission_boundaries(self):
        """測試權限邊界（非管理員訪問管理功能）"""
        self.print_section("Permission Boundary Tests")

        self.test_login()
        
        if not self.normal_user_token:
            print("⚠️  Skipping permission tests: No normal user token")
            return
        
        headers = {"Authorization": f"Bearer {self.normal_user_token}"}
        
        # 1. 嘗試訪問管理員儀表板
        try:
            response = requests.get(f"{self.api_v1}/admin/dashboard", headers=headers)
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from admin dashboard"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from admin dashboard, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Admin dashboard test error: {str(e)}")
        
        # 2. 嘗試獲取系統統計
        try:
            response = requests.get(f"{self.api_v1}/admin/stats", headers=headers)
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from system stats"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from system stats, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"System stats test error: {str(e)}")
        
        # 3. 嘗試管理其他用戶
        try:
            response = requests.post(
                f"{self.api_v1}/admin/users/1/manage?action=deactivate",
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from managing other users"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from , response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"User management test error: {str(e)}")
        
        # 4. 嘗試審核商戶
        try:
            response = requests.get(
                f"{self.api_v1}/admin/merchants/pending",
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from merchant review"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from merchant review, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Merchant review test error: {str(e)}")
        
        # 5. 嘗試查看審計日誌
        try:
            response = requests.get(
                f"{self.api_v1}/admin/audit-logs",
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from audit logs"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from audit logs, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Audit logs test error: {str(e)}")
        
        # 6. 嘗試發送系統通知
        try:
            response = requests.post(
                f"{self.api_v1}/admin/broadcast",
                json={
                    "title": "Test Notification",
                    "message": "This should not work",
                    "type": "info"
                },
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from broadcasting"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from broadcasting, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Broadcast test error: {str(e)}")
        
        # 7. 嘗試切換維護模式
        try:
            response = requests.post(
                f"{self.api_v1}/admin/maintenance?enabled=true",
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from maintenance mode"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from maintenance mode, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Maintenance mode test error: {str(e)}")
        
        # 8. 嘗試導出數據
        try:
            response = requests.get(
                f"{self.api_v1}/admin/export/users?format=csv",
                headers=headers
            )
            if response.status_code == 403:
                self.print_result(
                    True,
                    "Normal user blocked from data export"
                )
            else:
                self.print_result(
                    False,
                    f"Incorrect user from data export, response code: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Data export test error: {str(e)}")

        self.test_logout()
    
    # ========== 跨用戶資源訪問測試 ==========
    
    def test_cross_user_access(self):
        """測試跨用戶資源訪問控制"""
        self.print_section("Cross-User Access Control Tests")
        
        # 需要創建第二個用戶
        unique_id = self.generate_random_string()
        second_user_data = {
            "username": f"testuser2_{unique_id}",
            "email": f"test2_{unique_id}@example.com",
            "password": "TestPassword123!",
            "display_name": f"Test User 2 {unique_id}"
        }
        
        # 註冊第二個用戶
        try:
            response = requests.post(f"{self.api_v1}/auth/register", json=second_user_data)
            if response.status_code != 200:
                self.print_result(False, "Second user registration failed")
                return
            
            # 登入第二個用戶
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={
                    "username": second_user_data["username"],
                    "password": second_user_data["password"]
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                second_user_token = response.json().get("access_token")
                second_user_headers = {"Authorization": f"Bearer {second_user_token}"}
                
                # 使用第一個用戶的 token
                if self.normal_user_token and self.test_pet_id:
                    first_user_headers = {"Authorization": f"Bearer {self.normal_user_token}"}
                    
                    # 1. 第二個用戶嘗試更新第一個用戶的寵物
                    try:
                        response = requests.put(
                            f"{self.api_v1}/pets/{self.test_pet_id}",
                            json={"name": "Hacked Pet Name"},
                            headers=second_user_headers
                        )
                        self.print_result(
                            response.status_code in [403, 404],
                            "Cross-user pet update blocked"
                        )
                    except Exception as e:
                        self.print_result(False, f"Cross-user pet test error: {str(e)}")
                    
                    # 2. 第二個用戶嘗試刪除第一個用戶的貼文
                    if self.test_post_id:
                        try:
                            response = requests.delete(
                                f"{self.api_v1}/posts/{self.test_post_id}",
                                headers=second_user_headers
                            )
                            self.print_result(
                                response.status_code in [403, 404],
                                "Cross-user post deletion blocked"
                            )
                        except Exception as e:
                            self.print_result(False, f"Cross-user post test error: {str(e)}")
            else:
                self.print_result(False, "Second user login failed")
        except Exception as e:
            self.print_result(False, f"Cross-user test setup error: {str(e)}")
    
    # ========== 並發和 Session 測試 ==========
    
    def test_concurrent_sessions(self):
        """測試並發會話管理"""
        self.print_section("Concurrent Session Tests")
        
        if not self.test_user:
            print("⚠️  Skipping session tests: No test user")
            return
        
        # 1. 同一用戶多次登入
        tokens = []
        try:
            for i in range(3):
                response = requests.post(
                    f"{self.api_v1}/auth/login",
                    data={
                        "username": self.test_user["username"],
                        "password": self.test_user["password"]
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    token = response.json().get("access_token")
                    tokens.append(token)
            
            self.print_result(
                len(tokens) == 3,
                f"Multiple concurrent logins allowed ({len(tokens)} tokens)"
            )
            
            # 2. 測試所有 token 是否都有效
            valid_tokens = 0
            for token in tokens:
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                if response.status_code == 200:
                    valid_tokens += 1
            
            self.print_result(
                valid_tokens == len(tokens),
                f"All concurrent tokens valid ({valid_tokens}/{len(tokens)})"
            )
            
            # 3. 登出一個 token，確認其他 token 仍然有效
            if len(tokens) >= 2:
                # 登出第一個 token
                headers = {"Authorization": f"Bearer {tokens[0]}"}
                response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
                
                if response.status_code == 200:
                    # 檢查第一個 token 是否失效
                    response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                    token1_invalid = response.status_code == 401
                    
                    # 檢查第二個 token 是否仍然有效
                    headers2 = {"Authorization": f"Bearer {tokens[1]}"}
                    response = requests.get(f"{self.api_v1}/users/me", headers=headers2)
                    token2_valid = response.status_code == 200
                    
                    self.print_result(
                        token1_invalid and token2_valid,
                        "Selective token invalidation works correctly"
                    )
            
        except Exception as e:
            self.print_result(False, f"Concurrent session test error: {str(e)}")
    
    # ========== 速率限制測試 ==========
    
    def test_rate_limiting(self):
        """測試 API 速率限制"""
        self.print_section("Rate Limiting Tests")
        
        # 1. 測試登入嘗試限制
        fake_user = f"fake_user_{self.generate_random_string()}"
        login_attempts = 0
        rate_limited = False
        
        try:
            for i in range(10):  # 嘗試 10 次錯誤登入
                response = requests.post(
                    f"{self.api_v1}/auth/login",
                    data={
                        "username": fake_user,
                        "password": "wrong_password"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                login_attempts += 1
                
                # 檢查是否被速率限制（通常返回 429 Too Many Requests）
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            if rate_limited:
                self.print_result(
                    True,
                    f"Login rate limiting activated after {login_attempts} attempts"
                )
            else:
                self.print_result(
                    False,
                    f"No rate limiting detected after {login_attempts} login attempts"
                )
        except Exception as e:
            self.print_result(False, f"Rate limiting test error: {str(e)}")
        
        # 2. 測試 API 請求速率限制
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            request_count = 0
            rate_limited = False
            
            try:
                # 快速發送多個請求
                start_time = time.time()
                for i in range(100):  # 在短時間內發送 100 個請求
                    response = requests.get(f"{self.api_v1}/posts", headers=headers)
                    request_count += 1
                    
                    if response.status_code == 429:
                        rate_limited = True
                        break
                
                elapsed_time = time.time() - start_time
                
                if rate_limited:
                    self.print_result(
                        True,
                        f"API rate limiting activated after {request_count} requests in {elapsed_time:.2f}s"
                    )
                else:
                    self.print_result(
                        False,
                        f"No API rate limiting detected after {request_count} requests"
                    )
            except Exception as e:
                self.print_result(False, f"API rate limiting test error: {str(e)}")
    
    # ========== 登入 ==========

    def test_login(self):

        # 1. 註冊新用戶
        unique_id = self.generate_random_string()
        register_data = {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "TestPassword123!",
            "display_name": f"Test User {unique_id}",
            "bio": "This is a test user created by API tester",
            "phone": "+886912345678"
        }
        
        try:
            response = requests.post(f"{self.api_v1}/auth/register", json=register_data)
            if response.status_code == 200:
                user_data = response.json()
                self.test_user = register_data
                self.test_user_id = user_data.get("id")
                self.print_result(True, f"User registered: {register_data['username']}")
            else:
                self.print_result(False, f"Registration failed: {response.status_code}", response.text)
                return
        except Exception as e:
            self.print_result(False, f"Registration error: {str(e)}")
            return
        
        # 2. 登入
        try:
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={
                    "username": self.test_user["username"],
                    "password": self.test_user["password"]
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
                self.print_result(True, "Login successful")
                
                # 保存為普通用戶 token
                self.normal_user_token = self.access_token
                self.normal_user = self.test_user.copy()
            else:
                self.print_result(False, f"Login failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Login error: {str(e)}")

    # ========== 登出 ==========

    def test_logout(self):

        if self.normal_user_token:
            headers = {"Authorization": f"Bearer {self.normal_user_token}"}
            try:
                response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
                if response.status_code == 200:
                    self.print_result(True, "Logout successful")
                else:
                    self.print_result(False, f"Logout failed: {response.status_code}")
            except Exception as e:
                self.print_result(False, f"Logout error: {str(e)}")
    
    # ========== 登出error ==========

    def test_logout_error_handling(self):
        """測試 logout 的錯誤處理"""
        self.print_section("Logout Error Handling Tests")
        
        # 1. 測試使用過期的 token 登出
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNiIsImp0aSI6ImtSUWZLcUZLczVBcVpYeXNlUGNwR0EiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU2MjY0MjUxLCJpYXQiOjE3NTYyNjMzNTF9._J5S2kZvD26_23p33OmrubNC5PEcE0arT0WbQCFMsLg"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        try:
            response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
            if response.status_code == 401:
                error_detail = response.json().get("detail", "")
                self.print_result(
                    "expired" in error_detail.lower() or "invalid" in error_detail.lower(),
                    f"Expired token logout returns 401 with message: {error_detail}"
                )
            else:
                self.print_result(
                    False,
                    f"Unexpected status code for expired token: {response.status_code}"
                )
        except Exception as e:
            self.print_result(False, f"Expired token logout test error: {str(e)}")
        
        # 2. 測試使用無效格式的 token 登出
        invalid_token = "this.is.not.a.valid.jwt"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        try:
            response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
            self.print_result(
                response.status_code == 401,
                f"Invalid token logout returns 401"
            )
        except Exception as e:
            self.print_result(False, f"Invalid token logout test error: {str(e)}")
        
        # 3. 測試沒有 token 的登出
        try:
            response = requests.post(f"{self.api_v1}/auth/logout")
            self.print_result(
                response.status_code == 401,
                "No token logout returns 401"
            )
        except Exception as e:
            self.print_result(False, f"No token logout test error: {str(e)}")
        
        # 4. 測試正常 token 登出（如果有的話）
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
                self.print_result(
                    response.status_code == 200,
                    "Valid token logout returns 200"
                )
                
                # 測試登出後 token 是否失效
                response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                self.print_result(
                    response.status_code == 401,
                    "Token properly invalidated after logout"
                )
            except Exception as e:
                self.print_result(False, f"Valid token logout test error: {str(e)}")

    # ========== 寵物管理測試 ==========
    
    def test_pet_management(self):
        """測試寵物管理功能"""
        if not self.access_token:
            print("⚠️  Skipping pet tests: No access token")
            return
        
        self.print_section("Pet Management Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 創建寵物
        pet_data = {
            "name": f"TestPet_{self.generate_random_string(5)}",
            "species": "dog",
            "breed": "Golden Retriever",
            "gender": "male",
            "birth_date": "2022-01-15",
            "weight": 25.5,
            "description": "A friendly test dog"
        }
        
        try:
            response = requests.post(
                f"{self.api_v1}/pets",
                json=pet_data,
                headers=headers
            )
            if response.status_code == 201:
                pet = response.json()
                self.test_pet_id = pet.get("id")
                self.print_result(True, f"Pet created: {pet_data['name']}")
                
                # 驗證返回的數據
                assert pet.get("name") == pet_data["name"]
                assert pet.get("species") == pet_data["species"]
                assert pet.get("owner_username") is not None
            else:
                self.print_result(False, f"Pet creation failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Pet creation error: {str(e)}")
        
        # 2. 獲取我的寵物列表
        try:
            response = requests.get(f"{self.api_v1}/pets", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.print_result(True, f"Get my pets: {data.get('total', 0)} pets found")
            else:
                self.print_result(False, "Get pets failed")
        except Exception as e:
            self.print_result(False, f"Get pets error: {str(e)}")
        
        # 3. 獲取單個寵物
        if self.test_pet_id:
            try:
                response = requests.get(
                    f"{self.api_v1}/pets/{self.test_pet_id}",
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Get pet by ID")
            except Exception as e:
                self.print_result(False, f"Get pet error: {str(e)}")
        
        # 4. 更新寵物
        if self.test_pet_id:
            update_data = {
                "weight": 26.0,
                "description": "Updated description"
            }
            try:
                response = requests.put(
                    f"{self.api_v1}/pets/{self.test_pet_id}",
                    json=update_data,
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Update pet")
            except Exception as e:
                self.print_result(False, f"Update pet error: {str(e)}")
        
        # 5. 搜索寵物
        try:
            response = requests.get(
                f"{self.api_v1}/pets/search?q=Test",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Search pets")
        except Exception as e:
            self.print_result(False, f"Search pets error: {str(e)}")
        
        # 6. 獲取寵物統計
        if self.test_pet_id:
            try:
                response = requests.get(
                    f"{self.api_v1}/pets/{self.test_pet_id}/statistics",
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Get pet statistics")
            except Exception as e:
                self.print_result(False, f"Pet statistics error: {str(e)}")
        
        # 7. 測試未登入訪問（應該失敗）
        try:
            response = requests.get(f"{self.api_v1}/pets")
            self.print_result(
                response.status_code == 401,
                "Unauthenticated access properly blocked"
            )
        except Exception as e:
            self.print_result(False, f"Auth test error: {str(e)}")

        self.test_logout()
    
    # ========== 貼文測試 ==========
    
    def test_post_management(self):
        """測試貼文功能"""
        if not self.access_token:
            print("⚠️  Skipping post tests: No access token")
            return
        
        self.print_section("Post Management Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 創建貼文
        post_data = {
            "content": f"Test post created at {datetime.now()}",
            "visibility": "public",
            "location": "Taipei, Taiwan",
            "tags": ["test", "api", "寵物"]
        }
        
        if self.test_pet_id:
            post_data["pet_id"] = self.test_pet_id
        
        try:
            response = requests.post(
                f"{self.api_v1}/posts",
                json=post_data,
                headers=headers
            )
            if response.status_code == 200:
                post = response.json()
                self.test_post_id = post.get("id")
                self.print_result(True, "Post created")
            else:
                self.print_result(False, f"Post creation failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Post creation error: {str(e)}")
        
        # 2. 獲取貼文列表
        try:
            response = requests.get(f"{self.api_v1}/posts", headers=headers)
            self.print_result(response.status_code == 200, "Get post list")
        except Exception as e:
            self.print_result(False, f"Get post list error: {str(e)}")
        
        # 3. 獲取時間軸
        try:
            response = requests.get(f"{self.api_v1}/posts/timeline", headers=headers)
            self.print_result(response.status_code == 200, "Get timeline")
        except Exception as e:
            self.print_result(False, f"Get timeline error: {str(e)}")
        
        # 4. 按讚
        if self.test_post_id:
            try:
                response = requests.post(
                    f"{self.api_v1}/posts/{self.test_post_id}/like",
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Like post")
            except Exception as e:
                self.print_result(False, f"Like post error: {str(e)}")
        
        # 5. 評論
        if self.test_post_id:
            comment_data = {"content": "Great post! 👍"}
            try:
                response = requests.post(
                    f"{self.api_v1}/posts/{self.test_post_id}/comments",
                    json=comment_data,
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Add comment")
            except Exception as e:
                self.print_result(False, f"Add comment error: {str(e)}")
    
    # ========== 相簿測試 ==========
    
    def test_album_management(self):
        """測試相簿功能"""
        if not self.access_token:
            print("⚠️  Skipping album tests: No access token")
            return
        
        self.print_section("Album Management Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 創建相簿
        album_data = {
            "title": f"Test Album {self.generate_random_string(5)}",
            "description": "A test album created by API",
            "visibility": "private"
        }
        
        if self.test_pet_id:
            album_data["pet_id"] = self.test_pet_id
        
        try:
            response = requests.post(
                f"{self.api_v1}/albums",
                json=album_data,
                headers=headers
            )
            if response.status_code == 200:
                album = response.json()
                self.test_album_id = album.get("id")
                self.print_result(True, "Album created")
            else:
                self.print_result(False, f"Album creation failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Album creation error: {str(e)}")
        
        # 2. 獲取相簿列表
        try:
            response = requests.get(f"{self.api_v1}/albums", headers=headers)
            self.print_result(response.status_code == 200, "Get album list")
        except Exception as e:
            self.print_result(False, f"Get album list error: {str(e)}")
        
        # 3. 分享相簿
        if self.test_album_id:
            share_data = {"visibility": "public"}
            try:
                response = requests.post(
                    f"{self.api_v1}/albums/{self.test_album_id}/share",
                    json=share_data,
                    headers=headers
                )
                self.print_result(response.status_code == 200, "Share album")
            except Exception as e:
                self.print_result(False, f"Share album error: {str(e)}")
    
    # ========== 商戶測試 ==========
    
    def test_merchant_flow(self):
        """測試商戶流程"""
        if not self.access_token:
            print("⚠️  Skipping merchant tests: No access token")
            return
        
        self.print_section("Merchant Flow Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 申請成為商戶
        merchant_data = {
            "shop_name": f"Test Pet Shop {self.generate_random_string(5)}",
            "shop_slug": f"test-shop-{self.generate_random_string(8)}",
            "business_type": "individual",
            "description": "A test pet shop",
            "contact_email": f"shop_{self.generate_random_string(5)}@example.com",
            "contact_phone": "+886912345678",
            "address": {
                "city": "台北市",
                "district": "大安區",
                "street": "測試路123號"
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_v1}/merchants/apply",
                json=merchant_data,
                headers=headers
            )
            if response.status_code == 200:
                self.print_result(True, "Merchant application submitted")
            else:
                self.print_result(False, f"Merchant application failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Merchant application error: {str(e)}")
        
        # 2. 獲取商戶狀態
        try:
            response = requests.get(f"{self.api_v1}/merchants/status", headers=headers)
            self.print_result(response.status_code == 200, "Get merchant status")
        except Exception as e:
            self.print_result(False, f"Get merchant status error: {str(e)}")
    
    # ========== 商品測試 ==========
    
    def test_product_management(self):
        """測試商品管理"""
        if not self.access_token:
            print("⚠️  Skipping product tests: No access token")
            return
        
        self.print_section("Product Management Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 獲取商品分類
        try:
            response = requests.get(f"{self.api_v1}/products/categories")
            self.print_result(response.status_code == 200, "Get product categories")
        except Exception as e:
            self.print_result(False, f"Get categories error: {str(e)}")
        
        # 2. 搜索商品
        try:
            response = requests.get(
                f"{self.api_v1}/products?q=dog&category=pet-food"
            )
            self.print_result(response.status_code == 200, "Search products")
        except Exception as e:
            self.print_result(False, f"Search products error: {str(e)}")
        
        # 3. 獲取熱門商品
        try:
            response = requests.get(f"{self.api_v1}/products/popular")
            self.print_result(response.status_code == 200, "Get popular products")
        except Exception as e:
            self.print_result(False, f"Get popular products error: {str(e)}")
    
    # ========== 醫療記錄測試 ==========
    
    def test_medical_records(self):
        """測試醫療記錄功能"""
        if not self.access_token or not self.test_pet_id:
            print("⚠️  Skipping medical tests: No access token or pet")
            return
        
        self.print_section("Medical Records Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 創建醫療記錄
        medical_data = {
            "pet_id": self.test_pet_id,
            "visit_date": str(date.today()),
            "visit_type": "routine_checkup",
            "chief_complaint": "Annual health check",
            "diagnosis": "Healthy",
            "treatment": "No treatment needed",
            "weight": 26.0,
            "temperature": 38.5,
            "notes": "Pet is in good health"
        }
        
        try:
            response = requests.post(
                f"{self.api_v1}/medical/records",
                json=medical_data,
                headers=headers
            )
            if response.status_code == 200:
                self.print_result(True, "Medical record created")
            else:
                self.print_result(False, f"Medical record creation failed: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Medical record error: {str(e)}")
        
        # 2. 獲取寵物醫療記錄
        try:
            response = requests.get(
                f"{self.api_v1}/pets/{self.test_pet_id}/medical-records",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Get pet medical records")
        except Exception as e:
            self.print_result(False, f"Get medical records error: {str(e)}")
    
    # ========== 疫苗記錄測試 ==========
    
    def test_vaccination_records(self):
        """測試疫苗記錄功能"""
        if not self.access_token or not self.test_pet_id:
            print("⚠️  Skipping vaccination tests: No access token or pet")
            return
        
        self.print_section("Vaccination Records Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 獲取疫苗類型
        try:
            response = requests.get(
                f"{self.api_v1}/vaccinations/types?species=dog",
                headers=headers
            )
            if response.status_code == 200:
                self.print_result(True, "Get vaccine types")
                vaccines = response.json()
                
                # 2. 創建疫苗記錄
                if vaccines and len(vaccines) > 0:
                    vaccine_data = {
                        "pet_id": self.test_pet_id,
                        "vaccine_type_id": vaccines[0].get("id"),
                        "vaccination_date": str(date.today()),
                        "next_due_date": str(date.today() + timedelta(days=365)),
                        "batch_number": "TEST123",
                        "notes": "Test vaccination"
                    }
                    
                    try:
                        response = requests.post(
                            f"{self.api_v1}/vaccinations",
                            json=vaccine_data,
                            headers=headers
                        )
                        self.print_result(
                            response.status_code == 200,
                            "Create vaccination record"
                        )
                    except Exception as e:
                        self.print_result(False, f"Create vaccination error: {str(e)}")
            else:
                self.print_result(False, "Get vaccine types failed")
        except Exception as e:
            self.print_result(False, f"Get vaccine types error: {str(e)}")
        
        # 3. 獲取寵物疫苗記錄
        try:
            response = requests.get(
                f"{self.api_v1}/pets/{self.test_pet_id}/vaccinations",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Get pet vaccinations")
        except Exception as e:
            self.print_result(False, f"Get vaccinations error: {str(e)}")
    
    # ========== 通知測試 ==========
    
    def test_notifications(self):
        """測試通知功能"""
        if not self.access_token:
            print("⚠️  Skipping notification tests: No access token")
            return
        
        self.print_section("Notification Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 獲取通知列表
        try:
            response = requests.get(f"{self.api_v1}/notifications", headers=headers)
            self.print_result(response.status_code == 200, "Get notifications")
        except Exception as e:
            self.print_result(False, f"Get notifications error: {str(e)}")
        
        # 2. 獲取未讀通知數
        try:
            response = requests.get(
                f"{self.api_v1}/notifications/unread-count",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Get unread count")
        except Exception as e:
            self.print_result(False, f"Get unread count error: {str(e)}")
        
        # 3. 標記所有為已讀
        try:
            response = requests.post(
                f"{self.api_v1}/notifications/mark-all-read",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Mark all as read")
        except Exception as e:
            self.print_result(False, f"Mark all read error: {str(e)}")

    # ========== 隱私功能測試 ==========
    
    def test_user_privacy_features(self):
        """測試用戶隱私功能"""
        self.print_section("User Privacy Features Tests")
        
        if not self.access_token:
            print("⚠️  Skipping privacy tests: No access token")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 獲取當前用戶的隱私設置
        try:
            response = requests.get(
                f"{self.api_v1}/users/{self.test_user_id}/privacy",
                headers=headers
            )
            if response.status_code == 200:
                current_privacy = response.json()
                self.print_result(True, f"Get privacy settings: {current_privacy}")
            else:
                self.print_result(False, f"Failed to get privacy settings: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Get privacy settings error: {str(e)}")
        
        # 2. 更新隱私設置為私密
        try:
            privacy_update = {
                "privacy_level": "private",
                "show_email": False,
                "show_phone": False,
                "show_online_status": False,
                "show_last_seen": False
            }
            
            response = requests.put(
                f"{self.api_v1}/users/{self.test_user_id}/privacy",
                json=privacy_update,
                headers=headers
            )
            
            if response.status_code == 200:
                self.print_result(True, "Privacy settings updated to private")
            else:
                self.print_result(False, f"Failed to update privacy: {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Update privacy error: {str(e)}")
        
        # 3. 創建第二個用戶來測試隱私
        unique_id = self.generate_random_string()
        second_user_data = {
            "username": f"privacytest_{unique_id}",
            "email": f"privacy_{unique_id}@example.com",
            "password": "TestPassword123!",
            "display_name": f"Privacy Test User {unique_id}"
        }
        
        try:
            # 註冊第二個用戶
            response = requests.post(f"{self.api_v1}/auth/register", json=second_user_data)
            if response.status_code == 200:
                second_user_id = response.json().get("id")
                
                # 登入第二個用戶
                response = requests.post(
                    f"{self.api_v1}/auth/login",
                    data={
                        "username": second_user_data["username"],
                        "password": second_user_data["password"]
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    second_token = response.json().get("access_token")
                    second_headers = {"Authorization": f"Bearer {second_token}"}
                    
                    # 4. 第二個用戶嘗試查看第一個用戶（隱私模式）
                    response = requests.get(
                        f"{self.api_v1}/users/{self.test_user_id}",
                        headers=second_headers
                    )
                    
                    if response.status_code == 200:
                        visible_data = response.json()
                        # 檢查是否只包含最少資訊
                        has_minimal_data = all(key in visible_data for key in ["id", "username", "display_name"])
                        has_private_data = any(key in visible_data for key in ["email", "phone", "last_login_at"])
                        
                        self.print_result(
                            has_minimal_data and not has_private_data,
                            f"Private user shows minimal data only: {list(visible_data.keys())}"
                        )
                    else:
                        self.print_result(False, f"Failed to get user: {response.status_code}")
            else:
                self.print_result(False, "Failed to create second user")
        except Exception as e:
            self.print_result(False, f"Privacy test error: {str(e)}")
        
        # 5. 恢復為公開設置
        try:
            privacy_update = {
                "privacy_level": "public",
                "show_email": True,
                "show_phone": True,
                "show_online_status": True,
                "show_last_seen": True
            }
            
            response = requests.put(
                f"{self.api_v1}/users/{self.test_user_id}/privacy",
                json=privacy_update,
                headers=headers
            )
            
            self.print_result(
                response.status_code == 200,
                "Privacy settings restored to public"
            )
        except Exception as e:
            self.print_result(False, f"Restore privacy error: {str(e)}")

    # ========== 社交功能測試 ==========
    
    def test_social_features(self):
        """測試社交功能"""
        if not self.access_token:
            print("⚠️  Skipping social tests: No access token")
            return
        
        self.print_section("Social Features Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 搜索用戶
        try:
            response = requests.get(
                f"{self.api_v1}/users/search?q=test",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Search users")
        except Exception as e:
            self.print_result(False, f"Search users error: {str(e)}")
        
        # 2. 發送好友請求
        # 需要另一個用戶ID，這裡跳過
        
        # 3. 獲取好友列表
        try:
            response = requests.get(f"{self.api_v1}/friends", headers=headers)
            self.print_result(response.status_code == 200, "Get friends list")
        except Exception as e:
            self.print_result(False, f"Get friends error: {str(e)}")
        
        # 4. 獲取關注者
        try:
            response = requests.get(f"{self.api_v1}/followers", headers=headers)
            self.print_result(response.status_code == 200, "Get followers")
        except Exception as e:
            self.print_result(False, f"Get followers error: {str(e)}")
    
    # ========== 錯誤處理測試 ==========
    
    def test_error_handling(self):
        """測試錯誤處理"""
        self.print_section("Error Handling Tests")
        
        # 1. 無效的登入
        try:
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={"username": "invalid_user", "password": "wrong_pass"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            self.print_result(
                response.status_code == 401,
                "Invalid login properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Invalid login test error: {str(e)}")
        
        # 2. 未授權訪問
        try:
            response = requests.get(f"{self.api_v1}/users/me")
            self.print_result(
                response.status_code == 401,
                "Unauthorized access properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Unauthorized test error: {str(e)}")
        
        # 3. 無效的令牌
        headers = {"Authorization": "Bearer invalid_token_12345"}
        try:
            response = requests.get(f"{self.api_v1}/users/me", headers=headers)
            self.print_result(
                response.status_code == 401,
                "Invalid token properly rejected"
            )
        except Exception as e:
            self.print_result(False, f"Invalid token test error: {str(e)}")
        
        # 4. 不存在的資源
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                response = requests.get(
                    f"{self.api_v1}/pets/99999999",
                    headers=headers
                )
                self.print_result(
                    response.status_code == 404,
                    "Non-existent resource properly handled"
                )
            except Exception as e:
                self.print_result(False, f"404 test error: {str(e)}")
        
        # 5. 重複註冊
        if self.test_user:
            try:
                response = requests.post(
                    f"{self.api_v1}/auth/register",
                    json=self.test_user
                )
                self.print_result(
                    response.status_code == 400,
                    "Duplicate registration properly rejected"
                )
            except Exception as e:
                self.print_result(False, f"Duplicate registration test error: {str(e)}")
    
    # ========== 性能測試 ==========
    
    def test_performance(self):
        """基本性能測試"""
        self.print_section("Performance Tests")
        
        # 1. 響應時間測試
        endpoints = [
            "/health",
            "/api/v1",
            "/api/v1/products/categories"
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # 毫秒
                
                self.print_result(
                    response_time < 1000,  # 小於1秒
                    f"{endpoint} response time: {response_time:.2f}ms"
                )
            except Exception as e:
                self.print_result(False, f"Performance test error for {endpoint}: {str(e)}")
        
        # 2. 並發請求測試（簡單版）
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            concurrent_requests = 5
            
            try:
                start_time = time.time()
                for i in range(concurrent_requests):
                    requests.get(f"{self.api_v1}/posts", headers=headers)
                end_time = time.time()
                
                total_time = (end_time - start_time) * 1000
                avg_time = total_time / concurrent_requests
                
                self.print_result(
                    avg_time < 500,  # 平均小於500ms
                    f"Concurrent requests avg time: {avg_time:.2f}ms"
                )
            except Exception as e:
                self.print_result(False, f"Concurrent test error: {str(e)}")
    
    # ========== 清理測試 ==========
    
    def test_cleanup(self):
        """清理測試數據"""
        if not self.access_token:
            return
        
        self.print_section("Cleanup Tests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. 刪除測試貼文
        if self.test_post_id:
            try:
                response = requests.delete(
                    f"{self.api_v1}/posts/{self.test_post_id}",
                    headers=headers
                )
                self.print_result(
                    response.status_code in [200, 204],
                    "Delete test post"
                )
            except Exception as e:
                self.print_result(False, f"Delete post error: {str(e)}")
        
        # 2. 刪除測試寵物
        if self.test_pet_id:
            try:
                response = requests.delete(
                    f"{self.api_v1}/pets/{self.test_pet_id}",
                    headers=headers
                )
                self.print_result(
                    response.status_code in [200, 204],
                    "Delete test pet"
                )
            except Exception as e:
                self.print_result(False, f"Delete pet error: {str(e)}")
        
        # 3. 登出
        try:
            response = requests.post(
                f"{self.api_v1}/auth/logout",
                headers=headers
            )
            self.print_result(response.status_code == 200, "Logout successful")
        except Exception as e:
            self.print_result(False, f"Logout error: {str(e)}")
    
    # ========== 測試報告 ==========
    
    def generate_report(self):
        """生成測試報告"""
        self.print_section("Test Report")
        
        total = self.test_results['total']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        
        if total > 0:
            pass_rate = (passed / total) * 100
        else:
            pass_rate = 0
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Pass Rate: {pass_rate:.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for i, error in enumerate(self.test_results['errors'][:10], 1):
                print(f"   {i}. {error}")
            if len(self.test_results['errors']) > 10:
                print(f"   ... and {len(self.test_results['errors']) - 10} more")
        
        # 寫入報告文件
        report_file = f"logs/api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_time': datetime.now().isoformat(),
                'api_url': self.api_v1,
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_rate': f"{pass_rate:.1f}%"
                },
                'errors': self.test_results['errors']
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
    
    # ========== 主測試函數 ==========
    
    def run_all_tests(self):
        """運行所有測試（包含新增的測試）"""
        print("🚀 Starting Complete Pet Social Platform API Tests")
        print(f"📍 API Base URL: {self.api_v1}")
        print(f"🕐 Test Time: {datetime.now()}")
        print("="*60)
        
        # 運行測試組
        test_groups = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("Authentication Flow", self.test_authentication_flow),
            ("Token Expiration", self.test_token_expiration),
            ("Permission Boundaries", self.test_permission_boundaries),
            ("Cross-User Access", self.test_cross_user_access),
            ("Concurrent Sessions", self.test_concurrent_sessions),
            ("Rate Limiting", self.test_rate_limiting),
            ("Pet Management", self.test_pet_management),
            ("Post Management", self.test_post_management),
            ("Album Management", self.test_album_management),
            ("Merchant Flow", self.test_merchant_flow),
            ("Product Management", self.test_product_management),
            ("Medical Records", self.test_medical_records),
            ("Vaccination Records", self.test_vaccination_records),
            ("Notifications", self.test_notifications),
            ("Social Features", self.test_social_features),
            ("Admin Features", self.test_admin_features),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("Cleanup", self.test_cleanup)
        ]
        
        for group_name, test_func in test_groups:
            try:
                test_func()
            except Exception as e:
                print(f"\n❌ Critical error in {group_name}: {str(e)}")
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"Critical error in {group_name}: {str(e)}")
        
        # 生成報告
        self.generate_report()

def main():
    """主函數"""
    # 確保日誌目錄存在
    os.makedirs("logs", exist_ok=True)

    tester = CompletePetSocialAPITester()
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Pet Social Platform API Tester")
            print("\nUsage:")
            print("  python test_api_complete.py          # Run all tests")
            print("  python test_api_complete.py <group>  # Run specific test group")
            print("\nAvailable test groups:")
            print("  - connectivity")
            print("  - auth")
            print("  - token-expiration")
            print("  - permissions")
            print("  - cross-user")
            print("  - sessions")
            print("  - rate-limit")
            print("  - pet")
            print("  - post")
            print("  - album")
            print("  - merchant")
            print("  - product")
            print("  - medical")
            print("  - vaccination")
            print("  - notification")
            print("  - social")
            print("  - admin")
            print("  - error")
            print("  - logout-error")
            print("  - performance")
            return
        
        # 運行特定測試組
        test_map = {
            "connectivity": tester.test_basic_connectivity,
            "auth": tester.test_authentication_flow,
            "token-expiration": tester.test_token_expiration,
            "permissions": tester.test_permission_boundaries,
            "cross-user": tester.test_cross_user_access,
            "sessions": tester.test_concurrent_sessions,
            "rate-limit": tester.test_rate_limiting,
            "pet": tester.test_pet_management,
            "post": tester.test_post_management,
            "album": tester.test_album_management,
            "merchant": tester.test_merchant_flow,
            "product": tester.test_product_management,
            "medical": tester.test_medical_records,
            "vaccination": tester.test_vaccination_records,
            "notification": tester.test_notifications,
            "social": tester.test_social_features,
            "admin": tester.test_admin_features,
            "error": tester.test_error_handling,
            "logout-error": tester.test_logout_error_handling,
            "performance": tester.test_performance
        }
        
        test_name = sys.argv[1].lower()
        if test_name in test_map:
            # 某些測試需要先進行認證
            if test_name not in ["connectivity", "error", "auth", "admin", "rate-limit", "logout-error"]:
                tester.test_login()
            test_map[test_name]()
            tester.generate_report()
        else:
            print(f"Unknown test group: {test_name}")
            print("Run with --help to see available test groups")
    else:
        # 運行所有測試
        tester.run_all_tests()

if __name__ == "__main__":
    main()