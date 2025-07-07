#!/usr/bin/env python3
"""
包括的API テストスクリプト

全てのAPIエンドポイントをテストし、機能の動作確認を行います。

使用方法:
    python test_comprehensive_apis.py

機能:
    - 認証システム（ユーザー登録・ログイン）
    - 全攻撃戦略（Sniper、Battering Ram、Pitchfork、Cluster Bomb）
    - 変異機能（Mutations）
    - ジョブ実行と監視
    - 全脆弱性分析API（エラーパターン・ペイロード反射・時間遅延）
    - 履歴管理
    - エラーハンドリング
"""

import requests
import time
import json
import random
import string
from typing import Optional, Dict, Any

# 設定
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
REGISTER_URL = f"{BASE_URL}/api/auth/register"

# テスト用ユーザー情報（ランダム生成）
def generate_test_user():
    """ランダムなテストユーザーを生成"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return {
        "username": f"testuser_{random_suffix}",
        "email": f"test_{random_suffix}@example.com",
        "password": "TestPassword123!"
    }

class ComprehensiveAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.test_user = generate_test_user()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """テスト結果をログ"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details and not success:
            print(f"    詳細: {details}")
            
        if success:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {details}")
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """認証ヘッダー付きリクエスト送信"""
        if self.token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.token:
            kwargs['headers']['Authorization'] = f"Bearer {self.token}"
        
        return requests.request(method, url, **kwargs)
    
    def test_user_registration(self):
        """ユーザー登録テスト"""
        print("\n=== 1. ユーザー登録テスト ===")
        
        response = requests.post(REGISTER_URL, json=self.test_user)
        
        if response.status_code == 200:
            data = response.json()
            expected_fields = ["id", "username", "email", "is_active", "created_at", "updated_at"]
            missing_fields = [field for field in expected_fields if field not in data]
            
            if not missing_fields and data["username"] == self.test_user["username"]:
                self.log_result("ユーザー登録", True)
                return True
            else:
                self.log_result("ユーザー登録", False, f"レスポンス形式が不正: {missing_fields}")
                return False
        else:
            self.log_result("ユーザー登録", False, f"HTTP {response.status_code}: {response.text}")
            return False
    
    def test_user_login(self):
        """ユーザーログインテスト"""
        print("\n=== 2. ユーザーログインテスト ===")
        
        login_data = {
            "username": self.test_user["username"],
            "password": self.test_user["password"]
        }
        
        response = requests.post(LOGIN_URL, json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "token_type" in data and "user" in data:
                self.token = data["access_token"]
                self.log_result("ユーザーログイン", True)
                return True
            else:
                self.log_result("ユーザーログイン", False, "レスポンスにトークンが含まれていません")
                return False
        else:
            self.log_result("ユーザーログイン", False, f"HTTP {response.status_code}: {response.text}")
            return False
    
    def test_user_info(self):
        """ユーザー情報取得テスト"""
        print("\n=== 3. ユーザー情報取得テスト ===")
        
        response = self.make_request("GET", f"{self.base_url}/api/auth/me")
        
        if response.status_code == 200:
            data = response.json()
            if data["username"] == self.test_user["username"]:
                self.log_result("ユーザー情報取得", True)
                return True
            else:
                self.log_result("ユーザー情報取得", False, "ユーザー名が一致しません")
                return False
        else:
            self.log_result("ユーザー情報取得", False, f"HTTP {response.status_code}")
            return False
    
    def test_sniper_attack(self):
        """Sniper攻撃テスト"""
        print("\n=== 4. Sniper攻撃テスト ===")
        
        request_data = {
            "template": "GET /test?param=<<>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "placeholders": [],
            "strategy": "sniper",
            "payload_sets": [
                {
                    "name": "test_payloads",
                    "payloads": ["test1", "test2", "test3"]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/replace-placeholders", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["strategy"] == "sniper" and data["total_requests"] == 4:  # 3 payloads + 1 original
                self.log_result("Sniper攻撃", True)
                return data["request_id"]
            else:
                self.log_result("Sniper攻撃", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("Sniper攻撃", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_battering_ram_attack(self):
        """Battering Ram攻撃テスト"""
        print("\n=== 5. Battering Ram攻撃テスト ===")
        
        request_data = {
            "template": "GET /test?param1=<<PARAM>>&param2=<<PARAM>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "placeholders": ["PARAM"],
            "strategy": "battering_ram",
            "payload_sets": [
                {
                    "name": "ram_payloads",
                    "payloads": ["value1", "value2"]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/replace-placeholders", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["strategy"] == "battering_ram" and data["total_requests"] == 3:  # 2 payloads + 1 original
                self.log_result("Battering Ram攻撃", True)
                return data["request_id"]
            else:
                self.log_result("Battering Ram攻撃", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("Battering Ram攻撃", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_pitchfork_attack(self):
        """Pitchfork攻撃テスト"""
        print("\n=== 6. Pitchfork攻撃テスト ===")
        
        request_data = {
            "template": "GET /test?user=<<USER>>&id=<<ID>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "placeholders": ["USER", "ID"],
            "strategy": "pitchfork",
            "payload_sets": [
                {
                    "name": "users",
                    "payloads": ["admin", "guest", "user"]
                },
                {
                    "name": "ids", 
                    "payloads": ["1", "2", "3"]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/replace-placeholders", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["strategy"] == "pitchfork" and data["total_requests"] == 4:  # 3 pairs + 1 original
                self.log_result("Pitchfork攻撃", True)
                return data["request_id"]
            else:
                self.log_result("Pitchfork攻撃", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("Pitchfork攻撃", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_cluster_bomb_attack(self):
        """Cluster Bomb攻撃テスト"""
        print("\n=== 7. Cluster Bomb攻撃テスト ===")
        
        request_data = {
            "template": "GET /test?param1=<<X>>&param2=<<Y>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "placeholders": ["X", "Y"],
            "strategy": "cluster_bomb",
            "payload_sets": [
                {
                    "name": "x_values",
                    "payloads": ["a", "b"]
                },
                {
                    "name": "y_values",
                    "payloads": ["1", "2"]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/replace-placeholders", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["strategy"] == "cluster_bomb" and data["total_requests"] == 5:  # 2*2 + 1 original
                self.log_result("Cluster Bomb攻撃", True)
                return data["request_id"]
            else:
                self.log_result("Cluster Bomb攻撃", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("Cluster Bomb攻撃", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_mutations(self):
        """変異機能テスト"""
        print("\n=== 8. 変異機能テスト ===")
        
        mutation_data = {
            "template": "GET /test?param=<<X>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "mutations": [
                {
                    "token": "<<X>>",
                    "strategy": "dictionary",
                    "values": [
                        "simple",
                        {
                            "value": "A",
                            "repeat": 100
                        },
                        {
                            "value": "XYZ",
                            "repeat": 10
                        }
                    ]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/mutations", json=mutation_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["total_requests"] == 4:  # 3 mutations + 1 original
                self.log_result("変異機能", True)
                return data["request_id"]
            else:
                self.log_result("変異機能", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("変異機能", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_intuitive_api(self):
        """直感的API テスト"""
        print("\n=== 9. 直感的API テスト ===")
        
        intuitive_data = {
            "template": "GET /search?q=<<QUERY>>&type=<<TYPE>> HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n",
            "strategy": "cluster_bomb",
            "payload_sets": [
                {
                    "token": "<<QUERY>>",
                    "strategy": "dictionary",
                    "values": ["test", "admin"]
                },
                {
                    "token": "<<TYPE>>",
                    "strategy": "dictionary", 
                    "values": ["user", "system"]
                }
            ]
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/intuitive", json=intuitive_data)
        
        if response.status_code == 200:
            data = response.json()
            if data["total_requests"] == 5:  # 2*2 + 1 original
                self.log_result("直感的API", True)
                return data["request_id"]
            else:
                self.log_result("直感的API", False, f"生成リクエスト数が不正: {data.get('total_requests')}")
                return None
        else:
            self.log_result("直感的API", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def test_job_execution(self, request_id: int):
        """ジョブ実行テスト"""
        print(f"\n=== 10. ジョブ実行テスト (Request ID: {request_id}) ===")
        
        execute_data = {
            "request_id": request_id,
            "http_config": {
                "timeout": 30,
                "follow_redirects": True,
                "verify_ssl": False,
                "scheme": "http",
                "base_url": "httpbin.org",
                "sequential_execution": True,
                "request_delay": 0.1
            }
        }
        
        response = self.make_request("POST", f"{self.base_url}/api/execute-requests", json=execute_data)
        
        if response.status_code == 200:
            data = response.json()
            if "job_id" in data and data["status"] == "running":
                job_id = data["job_id"]
                self.log_result("ジョブ実行開始", True)
                
                # ジョブ完了待機
                return self.wait_for_job_completion(job_id)
            else:
                self.log_result("ジョブ実行開始", False, "ジョブIDまたは状態が不正")
                return None
        else:
            self.log_result("ジョブ実行開始", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    def wait_for_job_completion(self, job_id: str, max_wait_time: int = 60):
        """ジョブ完了待機"""
        print(f"ジョブ {job_id} の完了を待機中...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}")
            
            if response.status_code == 200:
                job_data = response.json()
                status = job_data["status"]
                
                if status == "completed":
                    self.log_result("ジョブ完了", True)
                    return job_id
                elif status == "failed":
                    self.log_result("ジョブ完了", False, f"ジョブ失敗: {job_data.get('error_message')}")
                    return None
                
                time.sleep(2)
            else:
                self.log_result("ジョブ状態確認", False, f"HTTP {response.status_code}")
                return None
        
        self.log_result("ジョブ完了", False, "タイムアウト")
        return None
    
    def test_job_management(self, job_id: str):
        """ジョブ管理テスト"""
        print(f"\n=== 11. ジョブ管理テスト ===")
        
        # ジョブ一覧取得
        response = self.make_request("GET", f"{self.base_url}/api/jobs")
        if response.status_code == 200:
            self.log_result("ジョブ一覧取得", True)
        else:
            self.log_result("ジョブ一覧取得", False, f"HTTP {response.status_code}")
        
        # ジョブ詳細取得
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}")
        if response.status_code == 200:
            self.log_result("ジョブ詳細取得", True)
        else:
            self.log_result("ジョブ詳細取得", False, f"HTTP {response.status_code}")
        
        # ジョブ結果取得
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}/results")
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                self.log_result("ジョブ結果取得", True)
            else:
                self.log_result("ジョブ結果取得", False, "結果が空")
        else:
            self.log_result("ジョブ結果取得", False, f"HTTP {response.status_code}")
        
        # ジョブ統計情報取得
        response = self.make_request("GET", f"{self.base_url}/api/jobs/statistics")
        if response.status_code == 200:
            self.log_result("ジョブ統計情報取得", True)
        else:
            self.log_result("ジョブ統計情報取得", False, f"HTTP {response.status_code}")
    
    def test_vulnerability_analysis(self, job_id: str):
        """脆弱性分析テスト"""
        print(f"\n=== 12. 脆弱性分析テスト (Job ID: {job_id}) ===")
        
        # エラーパターン分析 (POST)
        error_config = {
            "error_patterns": ["error", "exception", "404"],
            "case_sensitive": False
        }
        response = self.make_request("POST", f"{self.base_url}/api/jobs/{job_id}/analyze/error-patterns", json=error_config)
        if response.status_code == 200:
            data = response.json()
            if all(key in data for key in ["job_id", "total_requests", "analyzed_requests", "error_findings_count"]):
                self.log_result("エラーパターン分析 (POST)", True)
            else:
                self.log_result("エラーパターン分析 (POST)", False, "レスポンス形式が不正")
        else:
            self.log_result("エラーパターン分析 (POST)", False, f"HTTP {response.status_code}: {response.text}")
        
        # エラーパターン分析 (GET)
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}/analyze/error-patterns?error_patterns=error,exception&case_sensitive=false")
        if response.status_code == 200:
            self.log_result("エラーパターン分析 (GET)", True)
        else:
            self.log_result("エラーパターン分析 (GET)", False, f"HTTP {response.status_code}")
        
        # ペイロード反射分析 (POST)
        reflection_config = {
            "check_html_encoding": True,
            "check_url_encoding": True,
            "minimum_payload_length": 3
        }
        response = self.make_request("POST", f"{self.base_url}/api/jobs/{job_id}/analyze/payload-reflection", json=reflection_config)
        if response.status_code == 200:
            data = response.json()
            if all(key in data for key in ["job_id", "total_requests", "reflection_findings_count", "encoding_summary"]):
                self.log_result("ペイロード反射分析 (POST)", True)
            else:
                self.log_result("ペイロード反射分析 (POST)", False, "レスポンス形式が不正")
        else:
            self.log_result("ペイロード反射分析 (POST)", False, f"HTTP {response.status_code}: {response.text}")
        
        # ペイロード反射分析 (GET)
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}/analyze/payload-reflection?check_html_encoding=true&minimum_payload_length=2")
        if response.status_code == 200:
            self.log_result("ペイロード反射分析 (GET)", True)
        else:
            self.log_result("ペイロード反射分析 (GET)", False, f"HTTP {response.status_code}")
        
        # 時間遅延分析 (POST)
        delay_config = {
            "time_threshold": 1.0,
            "baseline_method": "first_request",
            "consider_payload_type": True
        }
        response = self.make_request("POST", f"{self.base_url}/api/jobs/{job_id}/analyze/time-delay", json=delay_config)
        if response.status_code == 200:
            data = response.json()
            if all(key in data for key in ["job_id", "total_requests", "delay_findings_count", "baseline_response_time"]):
                self.log_result("時間遅延分析 (POST)", True)
            else:
                self.log_result("時間遅延分析 (POST)", False, "レスポンス形式が不正")
        else:
            self.log_result("時間遅延分析 (POST)", False, f"HTTP {response.status_code}: {response.text}")
        
        # 時間遅延分析 (GET)
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{job_id}/analyze/time-delay?time_threshold=2.0&baseline_method=median")
        if response.status_code == 200:
            self.log_result("時間遅延分析 (GET)", True)
        else:
            self.log_result("時間遅延分析 (GET)", False, f"HTTP {response.status_code}")
    
    def test_history_management(self):
        """履歴管理テスト"""
        print("\n=== 13. 履歴管理テスト ===")
        
        # 履歴一覧取得
        response = self.make_request("GET", f"{self.base_url}/api/history")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log_result("履歴一覧取得", True)
                
                # 履歴詳細取得（最初の項目があれば）
                if len(data) > 0:
                    first_id = data[0]["id"]
                    response = self.make_request("GET", f"{self.base_url}/api/history/{first_id}")
                    if response.status_code == 200:
                        self.log_result("履歴詳細取得", True)
                    else:
                        self.log_result("履歴詳細取得", False, f"HTTP {response.status_code}")
                else:
                    self.log_result("履歴詳細取得", True, "履歴が空のためスキップ")
            else:
                self.log_result("履歴一覧取得", False, "レスポンス形式が不正")
        else:
            self.log_result("履歴一覧取得", False, f"HTTP {response.status_code}")
        
        # 統計情報取得
        response = self.make_request("GET", f"{self.base_url}/api/statistics")
        if response.status_code == 200:
            data = response.json()
            if all(key in data for key in ["total_fuzzer_requests", "total_generated_requests", "strategy_distribution"]):
                self.log_result("統計情報取得", True)
            else:
                self.log_result("統計情報取得", False, "レスポンス形式が不正")
        else:
            self.log_result("統計情報取得", False, f"HTTP {response.status_code}")
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        print("\n=== 14. エラーハンドリングテスト ===")
        
        # 認証なしでアクセス
        response = requests.get(f"{self.base_url}/api/history")
        if response.status_code == 401:
            self.log_result("認証なしアクセス", True)
        else:
            self.log_result("認証なしアクセス", False, f"期待: 401, 実際: {response.status_code}")
        
        # 存在しないジョブIDアクセス
        fake_job_id = "nonexistent-job-id"
        response = self.make_request("GET", f"{self.base_url}/api/jobs/{fake_job_id}")
        if response.status_code == 404:
            self.log_result("存在しないジョブアクセス", True)
        else:
            self.log_result("存在しないジョブアクセス", False, f"期待: 404, 実際: {response.status_code}")
        
        # 不正なペイロード送信
        invalid_data = {"invalid": "data"}
        response = self.make_request("POST", f"{self.base_url}/api/replace-placeholders", json=invalid_data)
        if response.status_code == 422:
            self.log_result("不正なペイロード", True)
        else:
            self.log_result("不正なペイロード", False, f"期待: 422, 実際: {response.status_code}")
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🚀 包括的API テスト開始")
        print(f"テストユーザー: {self.test_user['username']}")
        print("="*60)
        
        # 認証テスト
        if not self.test_user_registration():
            print("❌ ユーザー登録に失敗したため、テストを中断します")
            return
            
        if not self.test_user_login():
            print("❌ ログインに失敗したため、テストを中断します")
            return
            
        self.test_user_info()
        
        # 攻撃戦略テスト
        sniper_id = self.test_sniper_attack()
        battering_ram_id = self.test_battering_ram_attack()
        pitchfork_id = self.test_pitchfork_attack()
        cluster_bomb_id = self.test_cluster_bomb_attack()
        mutation_id = self.test_mutations()
        intuitive_id = self.test_intuitive_api()
        
        # ジョブ実行テスト（最初に成功したリクエストIDを使用）
        test_request_id = None
        for req_id in [sniper_id, battering_ram_id, pitchfork_id, cluster_bomb_id, mutation_id, intuitive_id]:
            if req_id is not None:
                test_request_id = req_id
                break
        
        if test_request_id:
            job_id = self.test_job_execution(test_request_id)
            
            if job_id:
                self.test_job_management(job_id)
                self.test_vulnerability_analysis(job_id)
        else:
            print("⚠️ リクエスト生成が全て失敗したため、ジョブ関連テストをスキップします")
        
        # その他のテスト
        self.test_history_management()
        self.test_error_handling()
        
        # 結果まとめ
        self.print_summary()
    
    def print_summary(self):
        """テスト結果サマリー表示"""
        print("\n" + "="*60)
        print("🏁 テスト結果サマリー")
        print("="*60)
        
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"総テスト数: {total_tests}")
        print(f"✅ 成功: {self.test_results['passed']}")
        print(f"❌ 失敗: {self.test_results['failed']}")
        print(f"📊 成功率: {pass_rate:.1f}%")
        
        if self.test_results["errors"]:
            print("\n❌ エラー詳細:")
            for error in self.test_results["errors"]:
                print(f"  - {error}")
        
        if pass_rate >= 90:
            print("\n🎉 素晴らしい！ほぼ全てのテストに成功しました")
        elif pass_rate >= 70:
            print("\n👍 良好です。大部分のテストに成功しました")
        else:
            print("\n⚠️ 多くのテストが失敗しています。システムを確認してください")

def main():
    """メイン関数"""
    print("包括的API テストスクリプト")
    print("サーバーが http://localhost:8000 で起動していることを確認してください\n")
    
    try:
        # 基本接続確認
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print(f"❌ サーバーに接続できません: {response.status_code}")
            return
        print("✅ サーバー接続確認完了\n")
        
        # テスト実行
        tester = ComprehensiveAPITester()
        tester.run_all_tests()
        
    except requests.exceptions.ConnectionError:
        print("❌ サーバーに接続できません。サーバーが起動していることを確認してください")
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによってテストが中断されました")
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")

if __name__ == "__main__":
    main() 