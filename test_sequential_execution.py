#!/usr/bin/env python3
"""
同期実行機能のテスト

HTTPリクエストの同期実行（順次実行）と非同期実行（並列実行）をテストします。
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_sequential_execution():
    """同期実行機能のテスト"""
    print("=== 同期実行機能テスト ===")
    
    # 既存のリクエストID 133を使用（4件のリクエストを生成済み）
    request_id = 133
    print(f"使用するリクエストID: {request_id}")
    
    # リクエストの詳細を確認
    response = requests.get(f"{BASE_URL}/api/history/{request_id}")
    if response.status_code == 200:
        request_detail = response.json()
        total_requests = request_detail["total_requests"]
        print(f"生成されたリクエスト数: {total_requests}")
    else:
        print(f"リクエスト詳細の取得に失敗: {response.status_code}")
        return
    
    # 1. 並列実行テスト
    print("\n--- 並列実行テスト ---")
    parallel_start = time.time()
    
    execute_payload = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:3000",
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "sequential_execution": False  # 並列実行
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_payload)
    print(f"並列実行ジョブ作成 ステータス: {response.status_code}")
    
    if response.status_code == 200:
        job_data = response.json()
        parallel_job_id = job_data["job_id"]
        print(f"並列実行ジョブID: {parallel_job_id}")
        
        # ジョブ完了を待機
        wait_for_job_completion(parallel_job_id)
        
        parallel_end = time.time()
        parallel_duration = parallel_end - parallel_start
        print(f"並列実行時間: {parallel_duration:.2f}秒")
    
    # 少し待機
    time.sleep(2)
    
    # 2. 同期実行テスト
    print("\n--- 同期実行テスト ---")
    sequential_start = time.time()
    
    execute_payload_seq = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:3000",
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "sequential_execution": True  # 同期実行
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_payload_seq)
    print(f"同期実行ジョブ作成 ステータス: {response.status_code}")
    
    if response.status_code == 200:
        job_data = response.json()
        sequential_job_id = job_data["job_id"]
        print(f"同期実行ジョブID: {sequential_job_id}")
        
        # ジョブ完了を待機
        wait_for_job_completion(sequential_job_id)
        
        sequential_end = time.time()
        sequential_duration = sequential_end - sequential_start
        print(f"同期実行時間: {sequential_duration:.2f}秒")
    
    print("\n=== 実行時間比較 ===")
    print(f"並列実行時間: {parallel_duration:.2f}秒")
    print(f"同期実行時間: {sequential_duration:.2f}秒")
    
    if sequential_duration > parallel_duration:
        print("✅ 同期実行が並列実行より時間がかかることを確認（期待される結果）")
    else:
        print("⚠️  同期実行が並列実行と同じか短い時間で完了（予想外の結果）")

def wait_for_job_completion(job_id):
    """ジョブの完了を待機"""
    max_attempts = 30  # 最大30秒待機
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code == 200:
            job_status = response.json()
            status = job_status['status']
            progress = job_status['progress']['progress_percentage']
            
            print(f"  ジョブ {job_id[:8]}... - ステータス: {status}, 進捗: {progress:.1f}%")
            
            if status in ['completed', 'failed', 'cancelled']:
                if status == 'completed':
                    results_count = len(job_status.get('results', []))
                    print(f"  ✅ ジョブ完了 - 結果数: {results_count}")
                else:
                    print(f"  ❌ ジョブ終了 - ステータス: {status}")
                break
        
        time.sleep(1)
        attempt += 1
    
    if attempt >= max_attempts:
        print(f"  ⏰ タイムアウト - ジョブ {job_id[:8]}... が完了しませんでした")

if __name__ == "__main__":
    test_sequential_execution() 