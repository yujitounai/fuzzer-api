import requests
import json

def test_sniper_with_multiple_placeholders():
    """同じプレースホルダが複数ある場合のSniper攻撃テスト"""
    print("=== Sniper Attack (複数プレースホルダ) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>> AND id=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["test1", "test2"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_single_placeholder():
    """単一プレースホルダのSniper攻撃テスト"""
    print("=== Sniper Attack (単一プレースホルダ) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_complex_template():
    """複雑なテンプレートのSniper攻撃テスト"""
    print("=== Sniper Attack (複雑なテンプレート) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>> AND name=<<>> AND email=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["admin", "1' OR '1'='1"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_history_api():
    """保存機能（履歴API）のテスト"""
    print("=== 履歴API（/api/history, /api/history/{id}, /api/history/{id} DELETE）テスト ===")
    # 履歴一覧取得
    res = requests.get("http://localhost:8000/api/history?limit=5")
    print(f"/api/history ステータス: {res.status_code}")
    history = res.json()
    print(f"履歴件数: {len(history)}")
    if history:
        first_id = history[0]['id']
        # 詳細取得
        detail = requests.get(f"http://localhost:8000/api/history/{first_id}")
        print(f"/api/history/{first_id} ステータス: {detail.status_code}")
        print(f"詳細: {json.dumps(detail.json(), indent=2, ensure_ascii=False)}")
        # 削除
        delete = requests.delete(f"http://localhost:8000/api/history/{first_id}")
        print(f"/api/history/{first_id} DELETE ステータス: {delete.status_code}")
        print(f"削除レスポンス: {delete.json()}")
    print()

def test_statistics_api():
    """統計情報APIのテスト"""
    print("=== 統計API（/api/statistics）テスト ===")
    res = requests.get("http://localhost:8000/api/statistics")
    print(f"/api/statistics ステータス: {res.status_code}")
    print(f"統計: {json.dumps(res.json(), indent=2, ensure_ascii=False)}")
    print()

if __name__ == "__main__":
    test_sniper_with_multiple_placeholders()
    test_sniper_single_placeholder()
    test_sniper_complex_template()
    test_history_api()
    test_statistics_api() 