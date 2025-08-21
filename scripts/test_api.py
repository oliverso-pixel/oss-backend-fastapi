# scripts/test_api.py
import requests
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class APITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.access_token = None
        self.refresh_token = None
        self.test_user = None
        self.test_user_id = None
        
    def print_result(self, success: bool, message: str, details: Any = None):
        """統一的結果輸出格式"""
        symbol = "✓" if success else "✗"
        print(f"{symbol} {message}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
    
    def test_health(self) -> bool:
        """測試健康檢查端點"""
        print("\n=== Testing Health Check ===")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.print_result(True, "Health check passed", response.json())
                return True
            else:
                self.print_result(False, f"Health check failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Health check error: {str(e)}")
            return False
    
    def test_root(self) -> bool:
        """測試根端點"""
        print("\n=== Testing Root Endpoints ===")
        try:
            # Test root
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.print_result(True, "Root endpoint working", response.json())
            
            # Test API v1 root
            response = requests.get(f"{self.api_v1}")
            if response.status_code == 200:
                self.print_result(True, "API v1 root working", response.json())
            
            return True
        except Exception as e:
            self.print_result(False, f"Root endpoint error: {str(e)}")
            return False
    
    def test_registration(self) -> Dict[str, Any]:
        """測試用戶註冊"""
        print("\n=== Testing User Registration ===")
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
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
                self.print_result(True, f"User registered successfully: {register_data['username']}")
                self.test_user = register_data
                self.test_user_id = user_data.get("id")
                return user_data
            else:
                self.print_result(False, f"Registration failed: {response.status_code}", response.text)
                return None
        except Exception as e:
            self.print_result(False, f"Registration error: {str(e)}")
            return None
    
    def test_login(self, username: str = None, password: str = None) -> bool:
        """測試用戶登入"""
        print("\n=== Testing User Login ===")
        
        if not username and self.test_user:
            username = self.test_user["username"]
            password = self.test_user["password"]
        
        if not username or not password:
            self.print_result(False, "No credentials provided for login")
            return False
        
        try:
            # Test with form data (OAuth2 standard)
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
                self.print_result(True, f"Login successful for user: {username}")
                print(f"  Access Token: {self.access_token[:20]}...")
                print(f"  Refresh Token: {self.refresh_token[:20]}...")
                return True
            else:
                self.print_result(False, f"Login failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Login error: {str(e)}")
            return False
    
    def test_get_current_user(self) -> bool:
        """測試獲取當前用戶信息"""
        print("\n=== Testing Get Current User (/me) ===")
        
        if not self.access_token:
            self.print_result(False, "No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{self.api_v1}/users/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                self.print_result(True, "Current user info retrieved successfully")
                print(f"  ID: {user_info.get('id')}")
                print(f"  Username: {user_info.get('username')}")
                print(f"  Email: {user_info.get('email')}")
                print(f"  Display Name: {user_info.get('display_name')}")
                print(f"  Is Active: {user_info.get('is_active')}")
                print(f"  Is Verified: {user_info.get('is_verified')}")
                return True
            else:
                self.print_result(False, f"Failed to get current user: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Get current user error: {str(e)}")
            return False
    
    def test_get_user_by_id(self) -> bool:
        """測試通過ID獲取用戶"""
        print("\n=== Testing Get User by ID ===")
        
        if not self.access_token or not self.test_user_id:
            self.print_result(False, "No access token or user ID available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{self.api_v1}/users/{self.test_user_id}", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                self.print_result(True, f"User info retrieved by ID: {self.test_user_id}")
                print(f"  Username: {user_info.get('username')}")
                print(f"  Email: {user_info.get('email')}")
                return True
            else:
                self.print_result(False, f"Failed to get user by ID: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Get user by ID error: {str(e)}")
            return False
    
    def test_update_user(self) -> bool:
        """測試更新用戶信息"""
        print("\n=== Testing Update User ===")
        
        if not self.access_token or not self.test_user_id:
            self.print_result(False, "No access token or user ID available")
            return False
        
        update_data = {
            "display_name": f"Updated Test User {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "bio": "This bio has been updated by API test",
            "phone": "+886987654321"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.put(
                f"{self.api_v1}/users/{self.test_user_id}", 
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                updated_user = response.json()
                self.print_result(True, "User updated successfully")
                print(f"  New Display Name: {updated_user.get('display_name')}")
                print(f"  New Bio: {updated_user.get('bio')}")
                print(f"  New Phone: {updated_user.get('phone')}")
                return True
            else:
                self.print_result(False, f"Failed to update user: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Update user error: {str(e)}")
            return False
    
    def test_get_users_list(self) -> bool:
        """測試獲取用戶列表"""
        print("\n=== Testing Get Users List ===")
        
        if not self.access_token:
            self.print_result(False, "No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Test default pagination
            response = requests.get(f"{self.api_v1}/users/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.print_result(True, "Users list retrieved successfully")
                print(f"  Total users: {data.get('total')}")
                print(f"  Page: {data.get('page')}/{data.get('pages')}")
                print(f"  Items per page: {data.get('per_page')}")
                print(f"  Users in this page: {len(data.get('items', []))}")
                
                # Test custom pagination
                response = requests.get(
                    f"{self.api_v1}/users/?page=1&per_page=5", 
                    headers=headers
                )
                if response.status_code == 200:
                    self.print_result(True, "Custom pagination working")
                
                return True
            else:
                self.print_result(False, f"Failed to get users list: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Get users list error: {str(e)}")
            return False
    
    def test_refresh_token(self) -> bool:
        """測試刷新令牌"""
        print("\n=== Testing Refresh Token ===")
        
        if not self.refresh_token:
            self.print_result(False, "No refresh token available")
            return False
        
        try:
            response = requests.post(
                f"{self.api_v1}/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access_token")
                self.print_result(True, "Token refreshed successfully")
                print(f"  New Access Token: {self.access_token[:20]}...")
                return True
            else:
                self.print_result(False, f"Token refresh failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Token refresh error: {str(e)}")
            return False
    
    def test_change_password(self) -> bool:
        """測試修改密碼"""
        print("\n=== Testing Change Password ===")
        
        if not self.access_token or not self.test_user:
            self.print_result(False, "No access token or test user available")
            return False
        
        change_data = {
            "old_password": self.test_user["password"],
            "new_password": "NewTestPassword123!"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.post(
                f"{self.api_v1}/auth/change-password",
                json=change_data,
                headers=headers
            )
            
            if response.status_code == 200:
                self.print_result(True, "Password changed successfully")
                # Update stored password for future tests
                self.test_user["password"] = change_data["new_password"]
                
                # Test login with new password
                if self.test_login(self.test_user["username"], change_data["new_password"]):
                    self.print_result(True, "Login with new password successful")
                
                return True
            else:
                self.print_result(False, f"Password change failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Password change error: {str(e)}")
            return False
    
    # def test_password_reset(self) -> bool:
    #     """測試密碼重設請求"""
    #     print("\n=== Testing Password Reset Request ===")
        
    #     if not self.test_user:
    #         self.print_result(False, "No test user available")
    #         return False
        
    #     try:
    #         response = requests.post(
    #             f"{self.api_v1}/auth/reset-password",
    #             json={"email": self.test_user["email"]}
    #         )
            
    #         if response.status_code == 200:
    #             self.print_result(True, "Password reset request sent")
    #             return True
    #         else:
    #             self.print_result(False, f"Password reset request failed: {response.status_code}", response.text)
    #             return False
    #     except Exception as e:
    #         self.print_result(False, f"Password reset error: {str(e)}")
    #         return False

    def test_admin_endpoints(self):
        """測試管理員端點"""
        print("\n=== Testing Admin Endpoints ===")
        
        # 首先需要以管理員身份登入
        admin_token = self.login_as_admin()
        if not admin_token:
            print("Cannot test admin endpoints without admin access")
            return
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 測試儀表板
        print("\n--- Testing Dashboard ---")
        response = requests.get(f"{self.api_v1}/admin/dashboard", headers=headers)
        if response.status_code == 200:
            self.print_result(True, "Dashboard data retrieved")
        
        # 測試系統統計
        print("\n--- Testing System Stats ---")
        response = requests.get(f"{self.api_v1}/admin/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            self.print_result(True, "System stats retrieved", stats)
        
        # 測試用戶搜索
        print("\n--- Testing User Search ---")
        response = requests.get(
            f"{self.api_v1}/admin/users?q=test", 
            headers=headers
        )
        if response.status_code == 200:
            self.print_result(True, "User search working")
        
        # 測試審計日誌
        print("\n--- Testing Audit Logs ---")
        response = requests.get(
            f"{self.api_v1}/admin/audit-logs", 
            headers=headers
        )
        if response.status_code == 200:
            self.print_result(True, "Audit logs retrieved")

    def test_login_as_admin(self) -> Optional[str]:
        """以管理員身份登入"""
        # 這裡假設有預設的管理員帳號
        response = requests.post(
            f"{self.api_v1}/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            print(f"{respones.json()}")
            return response.json().get("access_token")
        return None
    
    def test_logout(self) -> bool:
        """測試登出"""
        print("\n=== Testing Logout ===")
        
        if not self.access_token:
            self.print_result(False, "No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.post(f"{self.api_v1}/auth/logout", headers=headers)
            
            if response.status_code == 200:
                self.print_result(True, "Logout successful")
                
                # Test if token is invalid after logout
                response = requests.get(f"{self.api_v1}/users/me", headers=headers)
                if response.status_code == 401:
                    self.print_result(True, "Token properly invalidated after logout")
                
                return True
            else:
                self.print_result(False, f"Logout failed: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.print_result(False, f"Logout error: {str(e)}")
            return False
    
    def test_error_cases(self):
        """測試錯誤情況"""
        print("\n=== Testing Error Cases ===")
        
        # Test invalid login
        print("\n--- Testing Invalid Login ---")
        response = requests.post(
            f"{self.api_v1}/auth/login",
            data={"username": "nonexistent", "password": "wrongpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 401:
            self.print_result(True, "Invalid login properly rejected")
        
        # Test accessing protected endpoint without token
        print("\n--- Testing Unauthorized Access ---")
        response = requests.get(f"{self.api_v1}/users/me")
        if response.status_code == 401:
            self.print_result(True, "Unauthorized access properly rejected")
        
        # Test accessing with invalid token
        print("\n--- Testing Invalid Token ---")
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = requests.get(f"{self.api_v1}/users/me", headers=headers)
        if response.status_code == 401:
            self.print_result(True, "Invalid token properly rejected")
        
        # Test duplicate registration
        if self.test_user:
            print("\n--- Testing Duplicate Registration ---")
            response = requests.post(f"{self.api_v1}/auth/register", json=self.test_user)
            if response.status_code == 400:
                self.print_result(True, "Duplicate registration properly rejected")
    
    def run_all_tests(self):
        """運行所有測試"""
        print("=== Starting Pet Social Platform API Tests ===")
        print(f"API Base URL: {self.api_v1}")
        print(f"Test Time: {datetime.now()}")
        
        # Basic connectivity tests
        self.test_health()
        self.test_root()
        
        # Authentication flow
        user_data = self.test_registration()
        if user_data:
            self.test_login()
            
            if self.access_token:
                # User operations
                self.test_get_current_user()
                self.test_get_user_by_id()
                self.test_update_user()
                self.test_get_users_list()
                
                # Token operations
                self.test_refresh_token()
                
                # Password operations
                self.test_change_password()
                # self.test_password_reset()
                
                # Logout
                self.test_logout()
        
        # Error cases
        self.test_error_cases()
        
        print("\n=== All Tests Completed ===")

    def run_admin_tests(self):
        """"""
        print("=== Starting admin test ===")
        print(f"API Base URL: {self.api_v1}")
        print(f"Test Time: {datetime.now()}")

        self.test_login_as_admin()
        self.test_admin_endpoints()
        self.test_logout()

        print("\n Tests Completed")

def main():
    """主函數"""
    tester = APITester()
    
    # Check if specific test is requested
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if hasattr(tester, f"test_{test_name}"):
            getattr(tester, f"test_{test_name}")()
        else:
            print(f"Test '{test_name}' not found")
            print("Available tests:")
            for attr in dir(tester):
                if attr.startswith("test_"):
                    print(f"  - {attr[5:]}")
    else:
        # Run all tests
        tester.run_all_tests()

if __name__ == "__main__":
    main()