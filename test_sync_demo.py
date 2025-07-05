#!/usr/bin/env python3
"""
同期実行の簡単なデモ - ログ確認用
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def demo_sequential_execution():
    """同期実行のデモ"""
    request_id = 133  # 既存のリクエストID（4件のリクエスト）
    
    print("🔄 同期実行テスト開始...")
    
    # 同期実行
    execute_payload = {
        "request_id": request_id,
        "http_config": {
            "scheme": "http",
            "base_url": "localhost:3000",
            "timeout": 5,
            "follow_redirects": True,
            "verify_ssl": False,
            "sequential_execution": True  # 🔑 同期実行
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-requests", json=execute_payload)
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ 同期実行ジョブ作成: {job_id}")
        
        # ジョブ完了まで待機
        time.sleep(3)
        
        # 結果確認
        job_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if job_response.status_code == 200:
            job_status = job_response.json()
            print(f"📋 ジョブステータス: {job_status['status']}")
            print(f"🎯 結果数: {len(job_status.get('results', []))}")
        
        print("\n💡 サーバーのコンソールログで以下のメッセージを確認してください：")
        print("   - '同期実行モード: 4件のリクエストを順次実行します'")
        print("   - '同期実行: リクエスト 1/4 を送信中...'")
        print("   - '同期実行: リクエスト 1 完了 - ステータス: XXX'")
        print("   - (リクエスト2、3、4も順次)")
    else:
        print(f"❌ ジョブ作成失敗: {response.status_code}")

if __name__ == "__main__":
    demo_sequential_execution() 