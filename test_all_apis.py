#!/usr/bin/env python3
"""
プレースホルダ置換API 全機能テストスクリプト
JWT認証付きAPIの包括的テスト
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# APIのベースURL
BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str, response_data: Any = None):
        """テスト結果をログに記録"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        })
        
        if not success:
            print(f"   詳細: {response_data}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """認証ヘッダー付きでリクエストを送信"""
        url = f"{self.base_url}{endpoint}"
        
        # 認証が必要な場合はトークンを追加
        if self.auth_token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        
        if self.auth_token:
            kwargs['headers']['Authorization'] = f'Bearer {self.auth_token}'
        
        return self.session.request(method, url, **kwargs)
    
    def test_basic_info(self):
        """基本情報APIのテスト"""
        print("\n=== 基本情報APIテスト ===")
        
        try:
            response = self.make_request('GET', '/')
            if response.status_code == 200:
                data = response.json()
                self.log_test("基本情報取得", True, f"API情報を取得しました", data)
            else:
                self.log_test("基本情報取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("基本情報取得", False, f"例外発生: {e}")
    
    def test_authentication(self):
        """認証関連APIのテスト"""
        print("\n=== 認証APIテスト ===")
        
        # ログインテスト
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        try:
            response = self.make_request('POST', '/api/auth/login', 
                                       json=login_data, 
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('access_token')
                self.log_test("ログイン", True, "認証成功、トークンを取得", 
                            {"token_type": data.get('token_type'), "user": data.get('user')})
            else:
                self.log_test("ログイン", False, f"ステータスコード: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("ログイン", False, f"例外発生: {e}")
            return False
        
        # ユーザー情報取得テスト
        try:
            response = self.make_request('GET', '/api/auth/me')
            if response.status_code == 200:
                data = response.json()
                self.log_test("ユーザー情報取得", True, "現在のユーザー情報を取得", data)
            else:
                self.log_test("ユーザー情報取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("ユーザー情報取得", False, f"例外発生: {e}")
        
        return True
    
    def test_placeholder_replacement(self):
        """プレースホルダ置換APIのテスト"""
        print("\n=== プレースホルダ置換APIテスト ===")
        
        # Sniper攻撃テスト
        sniper_data = {
            "template": "GET /hack/test.php?param=<<>> HTTP/1.1\\nHost: example.com\\nUser-Agent: Test-Agent",
            "placeholders": ["param"],
            "strategy": "sniper",
            "payload_sets": [
                {
                    "name": "xss_payloads",
                    "payloads": ["<script>alert('XSS')</script>", "<img src=x onerror=alert(1)>", "javascript:alert(1)"]
                }
            ]
        }
        
        try:
            response = self.make_request('POST', '/api/replace-placeholders', 
                                       json=sniper_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Sniper攻撃", True, f"リクエスト生成成功 (総数: {data.get('total_requests')})", 
                            {"strategy": data.get('strategy'), "request_id": data.get('request_id')})
                return data.get('request_id')
            else:
                self.log_test("Sniper攻撃", False, f"ステータスコード: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Sniper攻撃", False, f"例外発生: {e}")
        
        # Battering Ram攻撃テスト
        battering_data = {
            "template": "GET /hack/test.php?param1=<<param1>>&param2=<<param2>> HTTP/1.1\\nHost: example.com",
            "placeholders": ["param1", "param2"],
            "strategy": "battering_ram",
            "payload_sets": [
                {
                    "name": "sql_payloads",
                    "payloads": ["' OR '1'='1", "1; DROP TABLE users; --", "admin'--"]
                }
            ]
        }
        
        try:
            response = self.make_request('POST', '/api/replace-placeholders', 
                                       json=battering_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Battering Ram攻撃", True, f"リクエスト生成成功 (総数: {data.get('total_requests')})")
            else:
                self.log_test("Battering Ram攻撃", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("Battering Ram攻撃", False, f"例外発生: {e}")
        
        return None
    
    def test_mutations(self):
        """変異機能APIのテスト"""
        print("\n=== 変異機能APIテスト ===")
        
        mutations_data = {
            "template": "GET /api/test?param=<<X>> HTTP/1.1\\nHost: example.com",
            "mutations": [
                {
                    "token": "<<X>>",
                    "strategy": "dictionary",
                    "values": [
                        "<script>alert('test')</script>",
                        {
                            "value": "A",
                            "repeat": 100
                        },
                        "normal_value"
                    ]
                }
            ]
        }
        
        try:
            response = self.make_request('POST', '/api/mutations', 
                                       json=mutations_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("変異機能", True, f"変異リクエスト生成成功 (総数: {data.get('total_requests')})")
            else:
                self.log_test("変異機能", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("変異機能", False, f"例外発生: {e}")
    
    def test_statistics(self):
        """統計情報APIのテスト"""
        print("\n=== 統計情報APIテスト ===")
        
        try:
            response = self.make_request('GET', '/api/statistics')
            if response.status_code == 200:
                data = response.json()
                self.log_test("統計情報取得", True, "統計情報を取得", data)
            else:
                self.log_test("統計情報取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("統計情報取得", False, f"例外発生: {e}")
    
    def test_history(self):
        """履歴管理APIのテスト"""
        print("\n=== 履歴管理APIテスト ===")
        
        # 履歴一覧取得
        try:
            response = self.make_request('GET', '/api/history?limit=5&offset=0')
            if response.status_code == 200:
                data = response.json()
                # APIは配列を直接返すので、修正
                if isinstance(data, list):
                    self.log_test("履歴一覧取得", True, f"履歴取得成功 (件数: {len(data)})")
                    
                    # 最初の履歴の詳細を取得
                    if len(data) > 0:
                        first_id = data[0]['id']
                        detail_response = self.make_request('GET', f'/api/history/{first_id}')
                        if detail_response.status_code == 200:
                            self.log_test("履歴詳細取得", True, f"履歴ID {first_id} の詳細を取得")
                        else:
                            self.log_test("履歴詳細取得", False, f"ステータスコード: {detail_response.status_code}")
                else:
                    # 別形式の場合の処理
                    self.log_test("履歴一覧取得", True, f"履歴取得成功 (件数: {len(data.get('requests', []))})")
            else:
                self.log_test("履歴一覧取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("履歴一覧取得", False, f"例外発生: {e}")
    
    def test_job_execution(self, request_id: Optional[int] = None):
        """ジョブ実行・管理APIのテスト"""
        print("\n=== ジョブ実行・管理APIテスト ===")
        
        if not request_id:
            print("テスト用リクエストIDがないため、新しいリクエストを作成します...")
            # テスト用リクエストを作成
            test_data = {
                "template": "GET /hack/test.php?cmd=<<>> HTTP/1.1\\nHost: httpbin.org\\nUser-Agent: TestAgent",
                "placeholders": ["cmd"],
                "strategy": "sniper",
                "payload_sets": [
                    {
                        "name": "test_payloads",
                        "payloads": ["test1", "test2"]
                    }
                ]
            }
            
            try:
                response = self.make_request('POST', '/api/replace-placeholders', 
                                           json=test_data,
                                           headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    request_id = response.json().get('request_id')
                    self.log_test("テスト用リクエスト作成", True, f"リクエストID: {request_id}")
                else:
                    self.log_test("テスト用リクエスト作成", False, f"ステータスコード: {response.status_code}")
                    return
            except Exception as e:
                self.log_test("テスト用リクエスト作成", False, f"例外発生: {e}")
                return
        
        # ジョブ実行
        job_config = {
            "request_id": request_id,
            "http_config": {
                "scheme": "https",
                "base_url": "httpbin.org",
                "timeout": 10,
                "follow_redirects": True,
                "verify_ssl": True
            }
        }
        
        try:
            response = self.make_request('POST', '/api/execute-requests', 
                                       json=job_config,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get('job_id')
                self.log_test("ジョブ実行開始", True, f"ジョブID: {job_id}")
                
                # ジョブ状態監視
                self.monitor_job(job_id)
                
            else:
                self.log_test("ジョブ実行開始", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("ジョブ実行開始", False, f"例外発生: {e}")
        
        # ジョブ一覧取得
        try:
            response = self.make_request('GET', '/api/jobs')
            if response.status_code == 200:
                data = response.json()
                self.log_test("ジョブ一覧取得", True, f"ジョブ数: {data.get('total', 0)}")
            else:
                self.log_test("ジョブ一覧取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("ジョブ一覧取得", False, f"例外発生: {e}")
    
    def monitor_job(self, job_id: str, max_wait: int = 30):
        """ジョブの完了を監視"""
        print(f"ジョブ {job_id} の完了を監視中...")
        
        for i in range(max_wait):
            try:
                response = self.make_request('GET', f'/api/jobs/{job_id}')
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get('status')
                    progress = job_data.get('progress', {})
                    
                    if status == 'completed':
                        self.log_test("ジョブ完了", True, 
                                    f"成功: {progress.get('successful_requests', 0)}, "
                                    f"失敗: {progress.get('failed_requests', 0)}")
                        
                        # 結果取得テスト
                        self.test_job_results(job_id)
                        break
                    elif status == 'failed':
                        self.log_test("ジョブ完了", False, f"ジョブが失敗しました: {job_data.get('error_message')}")
                        break
                    else:
                        print(f"  進行状況: {progress.get('progress_percentage', 0):.1f}%")
                        time.sleep(1)
                else:
                    self.log_test("ジョブ状態確認", False, f"ステータスコード: {response.status_code}")
                    break
            except Exception as e:
                self.log_test("ジョブ状態確認", False, f"例外発生: {e}")
                break
        else:
            self.log_test("ジョブ監視", False, "タイムアウトしました")
    
    def test_job_results(self, job_id: str):
        """ジョブ結果取得のテスト"""
        try:
            response = self.make_request('GET', f'/api/jobs/{job_id}/results?limit=10&offset=0')
            if response.status_code == 200:
                data = response.json()
                self.log_test("ジョブ結果取得", True, f"結果数: {len(data.get('results', []))}")
                
                # 個別結果取得テスト
                if data.get('results') and len(data['results']) > 0:
                    first_result = data['results'][0]
                    result_response = self.make_request('GET', f'/api/jobs/{job_id}/results/1')
                    if result_response.status_code == 200:
                        self.log_test("個別結果取得", True, "最初の結果を取得")
                    else:
                        self.log_test("個別結果取得", False, f"ステータスコード: {result_response.status_code}")
            else:
                self.log_test("ジョブ結果取得", False, f"ステータスコード: {response.status_code}")
        except Exception as e:
            self.log_test("ジョブ結果取得", False, f"例外発生: {e}")
    
    def test_intuitive_api(self):
        """直感的APIのテスト"""
        print("\n=== 直感的APIテスト ===")
        
        # 直感的APIの正しい形式（token, strategy, valuesを使用）
        intuitive_data = {
            "template": "GET /get?param=<<param>> HTTP/1.1\\nHost: httpbin.org\\nUser-Agent: Test-Agent",
            "strategy": "sniper",
            "payload_sets": [
                {
                    "token": "<<param>>",
                    "strategy": "dictionary",
                    "values": ["test1", "test2", "test3"]
                }
            ]
        }
        
        try:
            response = self.make_request('POST', '/api/intuitive', 
                                       json=intuitive_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("直感的API", True, f"リクエスト生成成功 (総数: {data.get('total_requests')})")
            else:
                self.log_test("直感的API", False, f"ステータスコード: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("直感的API", False, f"例外発生: {e}")
    
    def print_summary(self):
        """テスト結果の要約を表示"""
        print("\n" + "="*60)
        print("テスト結果要約")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失敗したテスト:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "="*60)
    
    def run_all_tests(self):
        """全てのテストを実行"""
        print("プレースホルダ置換API 全機能テスト開始")
        print(f"テスト対象: {self.base_url}")
        
        # 基本情報テスト
        self.test_basic_info()
        
        # 認証テスト
        if not self.test_authentication():
            print("❌ 認証に失敗したため、テストを中断します")
            return
        
        # 各種機能テスト
        request_id = self.test_placeholder_replacement()
        self.test_mutations()
        self.test_intuitive_api()
        self.test_statistics()
        self.test_history()
        self.test_job_execution(request_id)
        
        # テスト結果要約
        self.print_summary()

def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"APIテストを開始します...")
    print(f"対象URL: {base_url}")
    
    tester = APITester(base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main() 