#!/usr/bin/env python3
"""
直感的APIエンドポイント (/api/intuitive) のテスト

このテストは、placeholdersを使わずにpayload_setsのtokenから自動的にプレースホルダを抽出する
新しいAPIエンドポイントをテストします。
"""

import requests
import json
import time

# APIのベースURL
BASE_URL = "http://localhost:8000"

def test_intuitive_api():
    """直感的APIエンドポイントのテスト"""
    
    print("=== 直感的APIエンドポイント (/api/intuitive) テスト ===\n")
    
    # テストケース1: Battering Ram攻撃
    print("1. Battering Ram攻撃のテスト")
    test_battering_ram()
    
    # テストケース2: Sniper攻撃
    print("\n2. Sniper攻撃のテスト")
    test_sniper()
    
    # テストケース3: Pitchfork攻撃
    print("\n3. Pitchfork攻撃のテスト")
    test_pitchfork()
    
    # テストケース4: Cluster Bomb攻撃
    print("\n4. Cluster Bomb攻撃のテスト")
    test_cluster_bomb()
    
    # テストケース5: エラーケース
    print("\n5. エラーケースのテスト")
    test_error_cases()

def test_battering_ram():
    """Battering Ram攻撃のテスト"""
    payload = {
        "template": "username=<<username>>&password=<<password>>&email=<<email>>",
        "strategy": "battering_ram",
        "payload_sets": [
            {
                "token": "<<username>>",
                "strategy": "dictionary",
                "values": ["admin", "test", "guest", "root"]
            },
            {
                "token": "<<password>>",
                "strategy": "dictionary",
                "values": ["admin", "test", "guest", "root"]
            },
            {
                "token": "<<email>>",
                "strategy": "dictionary",
                "values": ["admin@example.com", "test@example.com", "guest@example.com", "root@example.com"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Strategy: {result['strategy']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Request ID: {result['request_id']}")
        print(f"   Generated Requests: {len(result['requests'])}")
        
        # 最初の3つのリクエストを表示
        for i, req in enumerate(result['requests'][:3]):
            print(f"   Request {i+1}: {req['request'][:100]}...")
    else:
        print(f"   Error: {response.text}")

def test_sniper():
    """Sniper攻撃のテスト"""
    payload = {
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
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Strategy: {result['strategy']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Request ID: {result['request_id']}")
        print(f"   Generated Requests: {len(result['requests'])}")
        
        # 最初の2つのリクエストを表示
        for i, req in enumerate(result['requests'][:2]):
            print(f"   Request {i+1}: {req['request'][:100]}...")
    else:
        print(f"   Error: {response.text}")

def test_pitchfork():
    """Pitchfork攻撃のテスト"""
    payload = {
        "template": "username=<<username>>&user_id=<<user_id>>&role=<<role>>",
        "strategy": "pitchfork",
        "payload_sets": [
            {
                "token": "<<username>>",
                "strategy": "dictionary",
                "values": ["admin", "test", "guest"]
            },
            {
                "token": "<<user_id>>",
                "strategy": "dictionary",
                "values": ["1", "2", "3"]
            },
            {
                "token": "<<role>>",
                "strategy": "dictionary",
                "values": ["admin", "user", "guest"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Strategy: {result['strategy']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Request ID: {result['request_id']}")
        print(f"   Generated Requests: {len(result['requests'])}")
        
        # 最初の3つのリクエストを表示
        for i, req in enumerate(result['requests'][:3]):
            print(f"   Request {i+1}: {req['request'][:100]}...")
    else:
        print(f"   Error: {response.text}")

def test_cluster_bomb():
    """Cluster Bomb攻撃のテスト"""
    payload = {
        "template": "username=<<username>>&password=<<password>>",
        "strategy": "cluster_bomb",
        "payload_sets": [
            {
                "token": "<<username>>",
                "strategy": "dictionary",
                "values": ["admin", "test"]
            },
            {
                "token": "<<password>>",
                "strategy": "dictionary",
                "values": ["admin", "test", "guest"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Strategy: {result['strategy']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Request ID: {result['request_id']}")
        print(f"   Generated Requests: {len(result['requests'])}")
        
        # 全てのリクエストを表示（Cluster Bombは組み合わせが多い）
        for i, req in enumerate(result['requests']):
            print(f"   Request {i+1}: {req['request'][:100]}...")
    else:
        print(f"   Error: {response.text}")

def test_error_cases():
    """エラーケースのテスト"""
    
    # ケース1: 無効な戦略
    print("   a) 無効な戦略")
    payload = {
        "template": "test=<<X>>",
        "strategy": "invalid_strategy",
        "payload_sets": [
            {
                "token": "<<X>>",
                "strategy": "dictionary",
                "values": ["test"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    print(f"      Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"      Expected Error: {response.text[:100]}...")
    
    # ケース2: 空のpayload_sets
    print("   b) 空のpayload_sets")
    payload = {
        "template": "test=<<X>>",
        "strategy": "sniper",
        "payload_sets": []
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    print(f"      Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"      Expected Error: {response.text[:100]}...")
    
    # ケース3: 無効なJSON
    print("   c) 無効なJSON")
    response = requests.post(f"{BASE_URL}/api/intuitive", data="invalid json", headers={"Content-Type": "application/json"})
    print(f"      Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"      Expected Error: {response.text[:100]}...")

def test_numbers_strategy():
    """numbers戦略のテスト（将来の拡張用）"""
    print("\n6. Numbers戦略のテスト（将来の拡張）")
    
    payload = {
        "template": "id=<<id>>&value=<<value>>",
        "strategy": "sniper",
        "payload_sets": [
            {
                "token": "<<id>>",
                "strategy": "numbers",
                "values": ["1", "2", "3", "4", "5"]
            },
            {
                "token": "<<value>>",
                "strategy": "dictionary",
                "values": ["test", "admin", "guest"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/intuitive", json=payload)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Strategy: {result['strategy']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Generated Requests: {len(result['requests'])}")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    try:
        test_intuitive_api()
        print("\n=== テスト完了 ===")
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。サーバーが起動しているか確認してください。")
        print("サーバー起動コマンド: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"エラー: {e}") 