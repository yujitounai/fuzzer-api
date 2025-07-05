#!/usr/bin/env python3
"""
プレースホルダ情報の修正をテストするスクリプト
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_placeholder_fix():
    print("=== プレースホルダ情報修正テスト ===")
    
    # 1. リクエストを作成
    print("1. リクエストを作成中...")
    payload = {
        "template": "GET /api/test?param=<<>> HTTP/1.1\nHost: localhost:8000\nUser-Agent: TestBot\n\n",
        "placeholders": ["param"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "test_payloads",
                "payloads": ["value1", "value2"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/replace-placeholders", json=payload)
    if response.status_code != 200:
        print(f"リクエスト作成に失敗: {response.status_code}")
        print(response.text)
        return
    
    request_data = response.json()
    request_id = request_data["request_id"]
    print(f"リクエスト作成成功: ID={request_id}, 総リクエスト数={request_data['total_requests']}")
    
    # 2. ジョブを実行
    print("2. ジョブを実行中...")
    job_payload = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:8000",
            "timeout": 10,
            "follow_redirects": False,
            "verify_ssl": False
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=job_payload)
    if response.status_code != 200:
        print(f"ジョブ実行に失敗: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"ジョブ実行開始: job_id={job_id}")
    
    # 3. ジョブ完了を待機
    print("3. ジョブ完了を待機中...")
    max_wait = 30
    for i in range(max_wait):
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code != 200:
            print(f"ジョブ状態取得に失敗: {response.status_code}")
            continue
        
        job_status = response.json()
        status = job_status.get("status", "unknown")
        print(f"ジョブ状態: {status}")
        
        if status == "completed":
            break
        elif status in ["failed", "cancelled"]:
            print(f"ジョブが{status}状態で終了しました")
            return
    else:
        print("ジョブの完了をタイムアウトしました")
        return
    
    # 4. 結果を確認
    print("4. 結果を確認中...")
    response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
    if response.status_code != 200:
        print(f"結果取得に失敗: {response.status_code}")
        print(response.text)
        return
    
    job_results = response.json()
    results = job_results.get("results", [])
    
    if not results:
        print("結果が空です")
        return
    
    print(f"結果数: {len(results)}")
    
    # 各結果のプレースホルダ情報をチェック
    for i, result in enumerate(results):
        print(f"\n--- 結果 {i+1} ---")
        print(f"プレースホルダ: {result.get('placeholder', 'N/A')}")
        print(f"ペイロード: {result.get('payload', 'N/A')}")
        print(f"位置: {result.get('position', 'N/A')}")
        
        # HTTP レスポンス情報
        http_response = result.get('http_response', {})
        print(f"ステータスコード: {http_response.get('status_code', 'N/A')}")
        print(f"エラー: {http_response.get('error', 'なし')}")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_placeholder_fix() 