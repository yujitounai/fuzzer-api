#!/usr/bin/env python3
"""
リクエスト間ウェイト機能のテスト

リクエスト間に指定した待機時間を挟んで順次実行することを確認します。
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_request_delay():
    """リクエスト間ウェイト機能のテスト"""
    print("🕐 リクエスト間ウェイト機能テスト")
    
    request_id = 133  # 既存のリクエストID（4件のリクエスト）
    
    # 1. ウェイトなし同期実行
    print("\n--- ウェイトなし同期実行 ---")
    start_time = time.time()
    
    execute_payload_no_delay = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:3000",
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "sequential_execution": True,  # 同期実行
            "request_delay": 0.0  # ウェイトなし
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_payload_no_delay)
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ ジョブ作成: {job_id}")
        
        # ジョブ完了を待機
        wait_for_job_completion(job_id)
        
        no_delay_duration = time.time() - start_time
        print(f"⏱️  ウェイトなし実行時間: {no_delay_duration:.2f}秒")
    
    time.sleep(2)  # 少し待機
    
    # 2. 2秒ウェイト同期実行
    print("\n--- 2秒ウェイト同期実行 ---")
    start_time = time.time()
    
    execute_payload_with_delay = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:3000",
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "sequential_execution": True,  # 同期実行
            "request_delay": 2.0  # 2秒ウェイト
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_payload_with_delay)
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ ジョブ作成: {job_id}")
        
        # ジョブ完了を待機
        wait_for_job_completion(job_id)
        
        with_delay_duration = time.time() - start_time
        print(f"⏱️  2秒ウェイト実行時間: {with_delay_duration:.2f}秒")
    
    print("\n=== 実行時間比較 ===")
    print(f"ウェイトなし: {no_delay_duration:.2f}秒")
    print(f"2秒ウェイト: {with_delay_duration:.2f}秒")
    
    expected_delay = 2.0 * 3  # 4件のリクエストで3回のウェイト
    actual_delay = with_delay_duration - no_delay_duration
    
    print(f"予想追加時間: {expected_delay:.1f}秒")
    print(f"実際の追加時間: {actual_delay:.1f}秒")
    
    if actual_delay >= expected_delay * 0.8:  # 80%以上の精度で確認
        print("✅ ウェイト機能が正常に動作しています")
    else:
        print("⚠️  ウェイト機能が期待通りに動作していない可能性があります")
        
    print("\n💡 サーバーのコンソールログで以下のメッセージを確認してください：")
    print("   - '同期実行: 2.0秒待機中...'（リクエスト間に表示）")

def wait_for_job_completion(job_id):
    """ジョブの完了を待機"""
    max_attempts = 20
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code == 200:
            job_status = response.json()
            status = job_status['status']
            progress = job_status['progress']['progress_percentage']
            
            print(f"  📊 進捗: {progress:.0f}% - ステータス: {status}")
            
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
        print(f"  ⏰ タイムアウト - ジョブが完了しませんでした")

if __name__ == "__main__":
    test_request_delay() 