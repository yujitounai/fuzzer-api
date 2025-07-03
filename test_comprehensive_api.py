#!/usr/bin/env python3
"""
包括的APIテスト - 新機能対応版

このテストは、新しく追加修正された機能を含む包括的なAPIテストを実行します：
- プレースホルダ置換API
- ジョブ管理機能
- 実行結果の永続化
- デバッグログ機能
"""

import requests
import json
import time
import uuid

# APIのベースURL
BASE_URL = "http://localhost:8000"

def test_comprehensive_api():
    """包括的APIテストの実行"""
    
    print("=== 包括的APIテスト - 新機能対応版 ===\n")
    
    # 1. 基本的なプレースホルダ置換APIテスト
    print("1. 基本的なプレースホルダ置換APIテスト")
    test_basic_placeholder_api()
    
    # 2. ジョブ管理機能テスト
    print("\n2. ジョブ管理機能テスト")
    test_job_management()
    
    # 3. 実行結果の永続化テスト
    print("\n3. 実行結果の永続化テスト")
    test_result_persistence()
    
    # 4. エラーケーステスト
    print("\n4. エラーケーステスト")
    test_error_cases()
    
    # 5. 統計情報テスト
    print("\n5. 統計情報テスト")
    test_statistics()
    
    print("\n=== テスト完了 ===")

def test_basic_placeholder_api():
    """基本的なプレースホルダ置換APIテスト"""
    
    # テストケース1: Sniper攻撃
    print("   a) Sniper攻撃")
    sniper_payload = {
        "template": "GET /api/users?id=<<X>> HTTP/1.1\nHost: example.com\nUser-Agent: Mozilla/5.0",
        "strategy": "sniper",
        "payload_sets": [
            {
                "token": "<<X>>",
                "strategy": "dictionary",
                "values": [
                    "<script>alert('XSS')</script>",
                    "' OR 1=1 --",
                    "admin",
                    "test"
                ]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=sniper_payload)
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"      Strategy: {result['strategy']}")
        print(f"      Total Requests: {result['total_requests']}")
        print(f"      Request ID: {result['request_id']}")
        return result['request_id']
    else:
        print(f"      Error: {response.text}")
        return None

def test_job_management():
    """ジョブ管理機能テスト"""
    
    # まずリクエストを作成
    request_id = test_basic_placeholder_api()
    if not request_id:
        print("     リクエスト作成に失敗したため、ジョブ管理テストをスキップ")
        return
    
    # ジョブを作成
    print("   b) ジョブ作成")
    job_payload = {
        "request_id": request_id,
        "http_config": {
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "scheme": "http",
            "base_url": "localhost:8000"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=job_payload)
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        job_id = result['job_id']
        print(f"      Job ID: {job_id}")
        print(f"      Status: {result['status']}")
        print(f"      Message: {result['message']}")
        
        # ジョブの状態を監視
        print("   c) ジョブ状態監視")
        monitor_job_status(job_id)
        
        return job_id
    else:
        print(f"      Error: {response.text}")
        return None

def monitor_job_status(job_id):
    """ジョブの状態を監視"""
    max_attempts = 30  # 最大30回試行
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code == 200:
            result = response.json()
            status = result['status']
            progress = result['progress']
            
            print(f"      Attempt {attempt + 1}: Status={status}, Progress={progress.get('progress_percentage', 0):.1f}%")
            
            if status in ['completed', 'failed']:
                print(f"      Job completed with status: {status}")
                if result.get('results'):
                    print(f"      Results count: {len(result['results'])}")
                    # 最初の結果を表示
                    if result['results']:
                        first_result = result['results'][0]
                        print(f"      First result keys: {list(first_result.keys())}")
                        if 'http_response' in first_result:
                            http_response = first_result['http_response']
                            print(f"      HTTP Response status: {http_response.get('status_code', 'N/A')}")
                            print(f"      HTTP Response error: {http_response.get('error', 'None')}")
                else:
                    print(f"      No results found in response")
                break
            elif status == 'cancelled':
                print(f"      Job was cancelled")
                break
        else:
            print(f"      Error getting job status: {response.status_code}")
            break
        
        time.sleep(2)  # 2秒待機
        attempt += 1
    
    if attempt >= max_attempts:
        print(f"      Timeout waiting for job completion")

def test_result_persistence():
    """実行結果の永続化テスト"""
    
    print("   a) ジョブ一覧取得")
    response = requests.get(f"{BASE_URL}/api/jobs")
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"      Total Jobs: {result['total']}")
        print(f"      Jobs: {len(result['jobs'])}")
        
        # 完了したジョブを探す
        completed_jobs = [job for job in result['jobs'] if job['status'] == 'completed']
        if completed_jobs:
            print(f"      Completed Jobs: {len(completed_jobs)}")
            
            # 最初の完了ジョブの詳細を取得
            first_completed_job = completed_jobs[0]
            job_id = first_completed_job['id']
            print(f"      Testing persistence with job: {job_id}")
            
            # ジョブ詳細を取得
            detail_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
            if detail_response.status_code == 200:
                detail_result = detail_response.json()
                print(f"      Detail Status: {detail_result['status']}")
                print(f"      Detail Results Count: {len(detail_result.get('results', []))}")
                
                if detail_result.get('results'):
                    print(f"      Persistence test: SUCCESS - Results found in database")
                else:
                    print(f"      Persistence test: FAILED - No results found")
            else:
                print(f"      Error getting job detail: {detail_response.status_code}")
        else:
            print(f"      No completed jobs found for persistence test")
    else:
        print(f"      Error: {response.text}")

def test_error_cases():
    """エラーケーステスト"""
    
    # 存在しないジョブIDでテスト
    print("   a) 存在しないジョブID")
    fake_job_id = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/api/jobs/{fake_job_id}")
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 404:
        print(f"      Expected 404 error received")
    else:
        print(f"      Unexpected response: {response.status_code}")
    
    # 無効なリクエストIDでジョブ作成
    print("   b) 無効なリクエストIDでジョブ作成")
    invalid_payload = {
        "request_id": 99999,  # 存在しないリクエストID
        "http_config": {
            "timeout": 10,
            "base_url": "localhost:8000"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=invalid_payload)
    print(f"      Status Code: {response.status_code}")
    if response.status_code in [400, 404, 500]:
        print(f"      Expected error received")
    else:
        print(f"      Unexpected response: {response.status_code}")

def test_statistics():
    """統計情報テスト"""
    
    print("   a) ファザーリクエスト統計")
    response = requests.get(f"{BASE_URL}/api/statistics")
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"      Total Fuzzer Requests: {result['total_fuzzer_requests']}")
        print(f"      Total Generated Requests: {result['total_generated_requests']}")
        print(f"      Strategy Distribution: {result['strategy_distribution']}")
    else:
        print(f"      Error: {response.text}")
    
    print("   b) ジョブ統計")
    response = requests.get(f"{BASE_URL}/api/jobs/statistics")
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"      Total Jobs: {result['total_jobs']}")
        print(f"      Completed Jobs: {result.get('completed_jobs', 'N/A')}")
        print(f"      Running Jobs: {result.get('running_jobs', 'N/A')}")
        print(f"      Failed Jobs: {result.get('failed_jobs', 'N/A')}")
    else:
        print(f"      Error: {response.text}")

def test_history():
    """履歴機能テスト"""
    
    print("   a) ファザーリクエスト履歴")
    response = requests.get(f"{BASE_URL}/api/history?limit=5")
    print(f"      Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"      History Count: {len(result)}")
        if result:
            print(f"      First Request ID: {result[0]['id']}")
            print(f"      First Request Strategy: {result[0]['strategy']}")
    else:
        print(f"      Error: {response.text}")

if __name__ == "__main__":
    try:
        test_comprehensive_api()
    except KeyboardInterrupt:
        print("\nテストが中断されました")
    except Exception as e:
        print(f"\nテスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc() 