#!/usr/bin/env python3
"""
シンプルなURLエンコーディング処理のテスト
機械的にスペースを+に、#を%23に変換する処理をテスト
"""

import asyncio
import sys
sys.path.append('.')
from http_client import HTTPClient, HTTPRequestConfig

async def test_simple_url_encoding():
    """シンプルなURLエンコーディング処理をテストする"""
    
    print("=== シンプルなURLエンコーディング処理のテスト ===")
    
    # HTTPClientインスタンスを作成
    client = HTTPClient()
    
    # テストケース
    test_cases = [
        {
            "name": "期待されるケース",
            "url": "/api/search?q=hello world&category=test#section name",
            "expected": "/api/search?q=hello+world&category=test%23section+name"
        },
        {
            "name": "スペースのみ",
            "url": "/test?param=hello world",
            "expected": "/test?param=hello+world"
        },
        {
            "name": "#のみ",
            "url": "/test?param=value#section",
            "expected": "/test?param=value%23section"
        },
        {
            "name": "複雑なケース",
            "url": "/search?q=test query&type=full#result section item",
            "expected": "/search?q=test+query&type=full%23result+section+item"
        },
        {
            "name": "完全URL",
            "url": "https://example.com/api?q=hello world#section name",
            "expected": "https://example.com/api?q=hello+world%23section+name"
        }
    ]
    
    # 各テストケースを実行
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i}: {test_case['name']} ---")
        
        # HTTPリクエスト文字列を作成
        request_text = f"GET {test_case['url']} HTTP/1.1\nHost: example.com\n\n"
        
        # リクエスト解析をテスト
        try:
            parsed = client.parse_http_request(request_text)
            print(f"元のURL: {test_case['url']}")
            print(f"解析されたURL: {parsed['url']}")
            
            # 実際のHTTPリクエストでの処理をシミュレート
            request_url = parsed["url"]
            
            if request_url.startswith(('http://', 'https://')):
                # 完全なURLの場合
                from urllib.parse import urlparse
                parsed_url = urlparse(request_url)
                path = parsed_url.path
                
                query_and_fragment = ""
                if parsed_url.query:
                    query_and_fragment += "?" + parsed_url.query
                if parsed_url.fragment:
                    query_and_fragment += "#" + parsed_url.fragment
                
                if query_and_fragment:
                    encoded_query_fragment = client.encode_url_query(query_and_fragment)
                    final_url = f"https://example.com{path}{encoded_query_fragment}"
                else:
                    final_url = f"https://example.com{path}"
            else:
                # 相対パスの場合
                path = request_url
                if not path.startswith('/'):
                    path = '/' + path
                
                if '?' in path:
                    base_path, query_part = path.split('?', 1)
                    encoded_query_part = client.encode_url_query(query_part)
                    final_url = base_path + '?' + encoded_query_part
                else:
                    final_url = path
            
            print(f"処理後URL: {final_url}")
            
            # 結果の検証
            if test_case['expected'] in final_url or final_url.endswith(test_case['expected']):
                print("✅ テスト成功")
            else:
                print("❌ テスト失敗")
                print(f"期待値: {test_case['expected']}")
                print(f"実際値: {final_url}")
                
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
    
    # 単体テスト：encode_url_queryメソッドのテスト
    print("\n=== encode_url_queryメソッドの単体テスト ===")
    
    query_tests = [
        {
            "input": "q=hello world&category=test#section name",
            "expected": "q=hello+world&category=test%23section+name",
            "description": "期待されるケース"
        },
        {
            "input": "?q=hello world&category=test#section name",
            "expected": "?q=hello+world&category=test%23section+name",
            "description": "?付きケース"
        },
        {
            "input": "param=hello world",
            "expected": "param=hello+world",
            "description": "スペースのみ"
        },
        {
            "input": "param=test#value",
            "expected": "param=test%23value",
            "description": "#のみ"
        }
    ]
    
    for i, test in enumerate(query_tests, 1):
        print(f"\n--- クエリテスト {i}: {test['description']} ---")
        result = client.encode_url_query(test['input'])
        print(f"入力: {test['input']}")
        print(f"結果: {result}")
        print(f"期待値: {test['expected']}")
        
        if result == test['expected']:
            print("✅ テスト成功")
        else:
            print("❌ テスト失敗")

if __name__ == "__main__":
    asyncio.run(test_simple_url_encoding()) 