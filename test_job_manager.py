#!/usr/bin/env python3
"""
JobManagerのテスト

バックグラウンドジョブ管理システムの動作をテストします。
"""

import requests
import json
import time
import asyncio
from datetime import datetime

# APIのベースURL
BASE_URL = "http://localhost:8000"

def test_job_manager():
    """JobManagerのテスト"""
    
    print("=== JobManagerテスト ===\n")
    
    # テストケース1: ジョブ作成と実行
    print("1. ジョブ作成と実行のテスト")
    test_job_creation_and_execution()
    
    # テストケース2: ジョブ状態の取得
    print("\n2. ジョブ状態取得のテスト")
    test_job_status_retrieval()
    
    # テストケース3: ジョブ一覧の取得
    print("\n3. ジョブ一覧取得のテスト")
    test_job_list_retrieval()
    
    # テストケース4: ジョブキャンセル
    print("\n4. ジョブキャンセルのテスト")
    test_job_cancellation()
    
    # テストケース5: ジョブ統計情報
    print("\n5. ジョブ統計情報のテスト")
    test_job_statistics()
    
    # テストケース6: クリーンアップ
    print("\n6. ジョブクリーンアップのテスト")
    test_job_cleanup()

def test_job_creation_and_execution():
    """ジョブ作成と実行のテスト"""
    
    # まず、テスト用のリクエストを作成
    print("  - テスト用リクエストを作成...")
    
    # 直感的APIでリクエストを作成
    intuitive_request = {
        "template": "GET /api/test?param=<<username>> HTTP/1.1\nHost: example.com",
        "strategy": "sniper",
        "payload_sets": [
            {
                "token": "<<username>>",
                "strategy": "dictionary",
                "values": ["admin", "test", "user"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=intuitive_request)
    if response.status_code != 200:
        print(f"    ❌ リクエスト作成に失敗: {response.status_code}")
        return
    
    request_data = response.json()
    request_id = request_data["request_id"]
    print(f"    ✅ リクエスト作成成功: ID {request_id}")
    
    # ジョブを作成して実行
    print("  - ジョブを作成して実行...")
    
    execute_request = {
        "request_id": request_id,
        "http_config": {
            "timeout": 10,
            "follow_redirects": False,
            "verify_ssl": False,
            "scheme": "http",
            "base_url": "httpbin.org"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_request)
    if response.status_code != 200:
        print(f"    ❌ ジョブ作成に失敗: {response.status_code}")
        return
    
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"    ✅ ジョブ作成成功: {job_id}")
    
    # ジョブの進捗を監視
    print("  - ジョブの進捗を監視...")
    for i in range(30):  # 最大30秒待機
        time.sleep(1)
        
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code != 200:
            print(f"    ❌ ジョブ状態取得に失敗: {response.status_code}")
            return
        
        job_status = response.json()
        status = job_status["status"]
        progress = job_status["progress"]
        
        print(f"    - 状態: {status}, 進捗: {progress['completed_requests']}/{progress['total_requests']} "
              f"({progress['progress_percentage']:.1f}%)")
        
        if status in ["completed", "failed", "cancelled"]:
            print(f"    ✅ ジョブ完了: {status}")
            if job_status.get("results"):
                print(f"    - 結果数: {len(job_status['results'])}")
            break
    else:
        print("    ⚠️ ジョブがタイムアウトしました")

def test_job_status_retrieval():
    """ジョブ状態取得のテスト"""
    
    # ジョブ一覧を取得
    response = requests.get(f"{BASE_URL}/api/jobs")
    if response.status_code != 200:
        print("  ❌ ジョブ一覧取得に失敗")
        return
    
    jobs = response.json()
    if not jobs["jobs"]:
        print("  ⚠️ テスト用のジョブがありません")
        return
    
    # 最初のジョブの詳細を取得
    job_id = jobs["jobs"][0]["id"]
    response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
    
    if response.status_code == 200:
        job_status = response.json()
        print(f"  ✅ ジョブ状態取得成功: {job_status['status']}")
        print(f"  - 進捗: {job_status['progress']['completed_requests']}/{job_status['progress']['total_requests']}")
    else:
        print(f"  ❌ ジョブ状態取得に失敗: {response.status_code}")

def test_job_list_retrieval():
    """ジョブ一覧取得のテスト"""
    
    response = requests.get(f"{BASE_URL}/api/jobs")
    if response.status_code == 200:
        jobs = response.json()
        print(f"  ✅ ジョブ一覧取得成功: {jobs['total']} 個のジョブ")
        
        for job in jobs["jobs"][:3]:  # 最初の3つを表示
            print(f"  - {job['id'][:8]}...: {job['status']} ({job['name']})")
    else:
        print(f"  ❌ ジョブ一覧取得に失敗: {response.status_code}")

def test_job_cancellation():
    """ジョブキャンセルのテスト"""
    
    # 実行中のジョブを探す
    response = requests.get(f"{BASE_URL}/api/jobs")
    if response.status_code != 200:
        print("  ❌ ジョブ一覧取得に失敗")
        return
    
    jobs = response.json()
    running_job = None
    
    for job in jobs["jobs"]:
        if job["status"] == "running":
            running_job = job
            break
    
    if not running_job:
        print("  ⚠️ キャンセル可能な実行中ジョブがありません")
        return
    
    # ジョブをキャンセル
    job_id = running_job["id"]
    response = requests.delete(f"{BASE_URL}/api/jobs/{job_id}")
    
    if response.status_code == 200:
        print(f"  ✅ ジョブキャンセル成功: {job_id}")
    else:
        print(f"  ❌ ジョブキャンセルに失敗: {response.status_code}")

def test_job_statistics():
    """ジョブ統計情報のテスト"""
    
    response = requests.get(f"{BASE_URL}/api/jobs/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"  ✅ 統計情報取得成功")
        print(f"  - 総ジョブ数: {stats['total_jobs']}")
        print(f"  - 状態分布: {stats['status_distribution']}")
        print(f"  - アクティブジョブ数: {stats['active_jobs']}")
    else:
        print(f"  ❌ 統計情報取得に失敗: {response.status_code}")

def test_job_cleanup():
    """ジョブクリーンアップのテスト"""
    
    # クリーンアップ前の統計
    response = requests.get(f"{BASE_URL}/api/jobs/statistics")
    if response.status_code == 200:
        before_stats = response.json()
        print(f"  - クリーンアップ前: {before_stats['total_jobs']} 個のジョブ")
    
    # クリーンアップ実行（1時間以上古いジョブを削除）
    response = requests.post(f"{BASE_URL}/api/jobs/cleanup?max_age_hours=1")
    if response.status_code == 200:
        cleanup_result = response.json()
        print(f"  ✅ クリーンアップ成功: {cleanup_result['deleted_count']} 個削除")
    else:
        print(f"  ❌ クリーンアップに失敗: {response.status_code}")
    
    # クリーンアップ後の統計
    response = requests.get(f"{BASE_URL}/api/jobs/statistics")
    if response.status_code == 200:
        after_stats = response.json()
        print(f"  - クリーンアップ後: {after_stats['total_jobs']} 個のジョブ")

if __name__ == "__main__":
    test_job_manager() 