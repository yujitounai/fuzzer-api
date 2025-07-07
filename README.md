# プレースホルダ置換API

戦略に応じて入力した文字列のプレースホルダを置き換えるPython APIです。4つの攻撃戦略（Sniper、Battering ram、Pitchfork、Cluster bomb）をサポートし、リクエストと生成されたリクエストの永続化機能、および包括的な脆弱性分析機能も提供しています。

## 機能

### 攻撃戦略

#### 1. Sniper Attack
- 各ペイロードを各位置に順番に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = 位置数 × ペイロード数

#### 2. Battering Ram Attack
- 同じペイロードを全ての位置に同時に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = ペイロード数

#### 3. Pitchfork Attack
- 各位置に異なるペイロードセットを使用し、同時に配置
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 最小のペイロードセットのサイズ

#### 4. Cluster Bomb Attack
- 全てのペイロードの組み合わせをテスト
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 全ペイロードセットの積

### 脆弱性分析機能

#### 1. エラーパターン検出分析
- **機能**: レスポンス内のエラーメッセージや機密情報の検出
- **検出対象**: SQLエラー、データベースエラー、スタックトレース、システム情報等
- **設定可能項目**: カスタムパターン、大文字小文字の区別
- **出力**: 深刻度付きのエラーパターン検出結果

#### 2. ペイロード反射検出分析
- **機能**: 送信ペイロードがレスポンスに反射されているかの検出
- **対象攻撃**: XSS（Cross-Site Scripting）、HTMLインジェクション等
- **設定可能項目**: HTMLエンコーディング、URLエンコーディング、最小ペイロード長
- **出力**: エンコーディング状況と反射検出結果

#### 3. 時間遅延検出分析
- **機能**: レスポンス時間の異常遅延検出
- **対象攻撃**: SQLインジェクション（時間ベース）、DoS攻撃等
- **設定可能項目**: 遅延閾値、ベースライン計算方法、ペイロードタイプ考慮
- **出力**: 遅延量と推定される攻撃タイプ

### 永続化機能

#### データベース
- SQLite + SQLAlchemyによるリクエストと生成されたリクエストの永続化
- 自動的にリクエスト履歴を保存
- 統計情報の提供
- ジョブベースの実行結果管理

#### 履歴管理
- リクエスト履歴の表示・検索
- 詳細情報の取得
- 不要なリクエストの削除
- ジョブの実行状況監視

#### 認証システム
- JWT（JSON Web Token）ベースの認証
- ユーザー登録・ログイン機能
- セッション管理

#### Webインターフェース
- テスト用Webページ（`/test`）
- 履歴表示用Webページ（`/history-page`）
- 統計情報の可視化

## セットアップ

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

**主要な依存関係:**
- `fastapi`: Webフレームワーク
- `uvicorn`: ASGIサーバー
- `sqlalchemy`: データベースORM
- `aiohttp`: HTTPリクエスト送信（非同期）
- `pydantic`: データバリデーション
- `python-jose`: JWT認証
- `passlib`: パスワードハッシュ化

2. サーバーを起動:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

サーバーは `http://localhost:8000` で起動します。

## デプロイ

### Renderへのデプロイ

本プロジェクトはRenderに簡単にデプロイできます。詳細な手順は [`DEPLOY.md`](DEPLOY.md) を参照してください。

#### 簡単デプロイ手順

1. **GitHubリポジトリ作成**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
   git push -u origin main
   ```

2. **Render設定**
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **環境変数設定（SQLiteデプロイ）**
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: `sqlite:///./fuzzer_requests.db`
   - `PYTHON_VERSION`: `3.11.11`

4. **データベース設定**
   - **SQLite**: シンプルデプロイ（推奨）- 設定不要
   - **PostgreSQL**: 本格運用時のみ - 別途PostgreSQLサービス作成が必要

## 使用方法

### 認証

全てのAPIエンドポイントはJWT認証が必要です。まず認証を行ってからAPIを利用してください。

#### ユーザー登録
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "email": "test@example.com", 
       "password": "password123"
     }'
```

#### ログイン
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "password": "password123"
     }'
```

レスポンスから`access_token`を取得し、以降のAPIリクエストのAuthorizationヘッダーに含めてください。

### Webインターフェース

#### テストページ
- **URL**: `http://localhost:8000/test`
- **機能**: プレースホルダ置換のテスト実行

#### 履歴ページ
- **URL**: `http://localhost:8000/history-page`
- **機能**: 
  - リクエスト履歴の表示・管理・統計情報
  - HTTPリクエスト実行機能（設定可能なタイムアウト、リダイレクト追跡、SSL検証、追加ヘッダー）
  - 実行結果の詳細表示（ステータスコード、レスポンス時間、エラー情報）
  - レスポンス内容の表示（ヘッダー、ボディ）

### API エンドポイント

#### 認証関連エンドポイント

##### POST /api/auth/register
ユーザー登録

**リクエスト例:**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}
```

##### POST /api/auth/login
ユーザーログイン

**リクエスト例:**
```json
{
  "username": "testuser", 
  "password": "password123"
}
```

**レスポンス例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

##### GET /api/auth/me
現在のユーザー情報取得

#### プレースホルダ置換エンドポイント

##### POST /api/replace-placeholders
プレースホルダを指定された戦略に応じて置き換え、データベースに保存します。

**リクエスト例:**
```json
{
  "template": "GET /hack/normalxss.php?cmd=<<>>&type=<<TYPE>> HTTP/1.1\nHost: target.com\nUser-Agent: Mozilla/5.0\n\n",
  "placeholders": ["cmd", "type"],
  "strategy": "cluster_bomb",
  "payload_sets": [
    {
      "name": "xss_payloads",
      "payloads": ["'\''", "<script>alert(1)</script>", "'; WAITFOR DELAY '\''00:00:03'\''--"]
    },
    {
      "name": "types",
      "payloads": ["user", "admin"]
    }
  ]
}
```

**レスポンス例:**
```json
{
  "strategy": "cluster_bomb",
  "total_requests": 9,
  "requests": [...],
  "request_id": 1
}
```

##### POST /api/mutations
変異ベースのプレースホルダ置換

**リクエスト例:**
```json
{
  "template": "GET /api/test?param=<<X>> HTTP/1.1\nHost: example.com",
  "mutations": [
    {
      "token": "<<X>>",
      "strategy": "dictionary",
      "values": [
        "test",
        {
          "value": "A",
          "repeat": 1000
        }
      ]
    }
  ]
}
```

##### POST /api/intuitive
直感的なプレースホルダ置換

#### ジョブ実行エンドポイント

##### POST /api/execute-requests
生成されたリクエストを実際にHTTPリクエストとして送信

**リクエスト例:**
```json
{
  "request_id": 1,
  "http_config": {
    "scheme": "https",
    "base_url": "example.com:443", 
    "timeout": 30,
    "follow_redirects": true,
    "verify_ssl": false,
    "sequential_execution": true,
    "request_delay": 0.5,
    "additional_headers": {
      "User-Agent": "Custom-Agent/1.0"
    }
  }
}
```

**レスポンス例:**
```json
{
  "job_id": "a3f7be34-f4fa-493f-8473-334852a93390",
  "status": "running",
  "message": "ジョブが開始されました"
}
```

##### GET /api/jobs
ジョブ一覧取得

##### GET /api/jobs/{job_id}
ジョブ状況確認

##### GET /api/jobs/{job_id}/results
ジョブ実行結果取得

#### 脆弱性分析エンドポイント

##### POST /api/jobs/{job_id}/analyze/error-patterns
エラーパターン検出分析（JSON設定）

**リクエスト例:**
```json
{
  "error_patterns": ["sql error", "database error", "stack trace"],
  "case_sensitive": false
}
```

**レスポンス例:**
```json
{
  "job_id": "a3f7be34-f4fa-493f-8473-334852a93390",
  "total_requests": 28,
  "analyzed_requests": 28,
  "error_findings_count": 3,
  "findings": [
    {
      "request_number": 5,
      "error_pattern": "sql error",
      "severity": "high",
      "description": "エラーメッセージまたは機密情報がレスポンスに含まれています: 'sql error'",
      "evidence": "パターン 'sql error' がレスポンスに含まれています",
      "payload": "'; DROP TABLE users; --",
      "response_snippet": "...SQL syntax error near 'DROP TABLE'..."
    }
  ],
  "patterns_checked": ["sql error", "database error", "stack trace"]
}
```

##### GET /api/jobs/{job_id}/analyze/error-patterns
エラーパターン検出分析（クエリパラメータ）

**使用例:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/jobs/JOB_ID/analyze/error-patterns?error_patterns=sql%20error,database%20error&case_sensitive=false"
```

##### POST /api/jobs/{job_id}/analyze/payload-reflection
ペイロード反射検出分析（JSON設定）

**リクエスト例:**
```json
{
  "check_html_encoding": true,
  "check_url_encoding": true,
  "check_js_encoding": true,
  "minimum_payload_length": 3
}
```

**レスポンス例:**
```json
{
  "job_id": "a3f7be34-f4fa-493f-8473-334852a93390",
  "total_requests": 28,
  "analyzed_requests": 15,
  "reflection_findings_count": 2,
  "findings": [
    {
      "request_number": 2,
      "vulnerability_type": "Cross-Site Scripting (XSS)",
      "severity": "high",
      "description": "ペイロードがエスケープされずにレスポンスに反射されています",
      "evidence": "HTMLエンコーディングが適用されていません",
      "payload": "<script>alert('XSS')</script>",
      "response_snippet": "...search results for <script>alert('XSS')</script>...",
      "encoding_status": "not_encoded"
    }
  ],
  "encoding_summary": {
    "encoded": 5,
    "not_encoded": 2,
    "partial": 1
  }
}
```

##### GET /api/jobs/{job_id}/analyze/payload-reflection
ペイロード反射検出分析（クエリパラメータ）

**使用例:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/jobs/JOB_ID/analyze/payload-reflection?check_html_encoding=true&minimum_payload_length=5"
```

##### POST /api/jobs/{job_id}/analyze/time-delay
時間遅延検出分析（JSON設定）

**リクエスト例:**
```json
{
  "time_threshold": 2.0,
  "baseline_method": "first_request",
  "consider_payload_type": true
}
```

**レスポンス例:**
```json
{
  "job_id": "a3f7be34-f4fa-493f-8473-334852a93390",
  "total_requests": 28,
  "analyzed_requests": 28,
  "delay_findings_count": 3,
  "findings": [
    {
      "request_number": 7,
      "vulnerability_type": "SQL Injection (Time-based)",
      "severity": "high",
      "description": "時間ベースの攻撃による応答遅延が検出されました",
      "evidence": "ベースライン(0.6秒)と比較して2.4秒の遅延",
      "payload": "'; WAITFOR DELAY '00:00:03'--",
      "response_time": 3.0,
      "baseline_time": 0.6,
      "delay_amount": 2.4
    }
  ],
  "baseline_response_time": 0.615,
  "average_response_time": 1.320,
  "threshold_used": 2.0
}
```

##### GET /api/jobs/{job_id}/analyze/time-delay
時間遅延検出分析（クエリパラメータ）

**使用例:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/jobs/JOB_ID/analyze/time-delay?time_threshold=1.5&baseline_method=median"
```

#### ベースライン計算方法
- `first_request`: 最初のリクエスト（通常は"original"）の時間を基準
- `average`: 全リクエストの平均時間を基準  
- `median`: 全リクエストの中央値を基準

#### 履歴管理エンドポイント

##### GET /api/history
リクエスト履歴を取得します。

**クエリパラメータ:**
- `limit`: 取得件数（デフォルト: 50）
- `offset`: オフセット（デフォルト: 0）

##### GET /api/history/{request_id}
特定のリクエストの詳細を取得します。

##### DELETE /api/history/{request_id}
特定のリクエストを削除します。

##### GET /api/statistics
データベースの統計情報を取得します。

**レスポンス例:**
```json
{
  "total_fuzzer_requests": 10,
  "total_generated_requests": 45,
  "strategy_distribution": {
    "sniper": 5,
    "battering_ram": 2,
    "pitchfork": 2,
    "cluster_bomb": 1
  }
}
```

##### GET /
APIの基本情報を取得します。

### サンプルスクリプト

#### 基本テスト
`test_sniper.py` を実行してSniper攻撃と保存機能をテストできます:

```bash
python test_sniper.py
```

#### 全戦略テスト
`example_usage.py` を実行して各戦略をテストできます:

```bash
python example_usage.py
```

#### 分離された脆弱性分析APIテスト
`test_separated_vulnerability_apis.py` を実行して新しい分析APIをテストできます:

```bash
python test_separated_vulnerability_apis.py
```

このテストでは以下を確認できます：
- エラーパターン検出機能
- ペイロード反射検出機能
- 時間遅延検出機能
- 各APIのPOST/GETバージョン

#### 包括的APIテスト
`test_comprehensive_apis.py` を実行して全てのAPIエンドポイントをテストできます:

```bash
python test_comprehensive_apis.py
```

## データベース

### テーブル構造

#### users
- `id`: ユーザーの一意識別子
- `username`: ユーザー名（一意）
- `email`: メールアドレス（一意）
- `hashed_password`: ハッシュ化されたパスワード
- `is_active`: アクティブフラグ
- `created_at`: ユーザー作成日時
- `updated_at`: 最終更新日時

#### fuzzer_requests
- `id`: リクエストの一意識別子
- `template`: プレースホルダを含むテンプレート文字列
- `placeholders`: プレースホルダ名のリスト（JSON形式）
- `strategy`: 攻撃戦略
- `payload_sets`: ペイロードセットのリスト（JSON形式）
- `total_requests`: 生成されたリクエストの総数
- `created_at`: リクエスト作成日時
- `updated_at`: 最終更新日時

#### generated_requests
- `id`: 生成されたリクエストの一意識別子
- `fuzzer_request_id`: 元のファザーリクエストのID
- `request_number`: リクエスト番号（順序）
- `request_content`: 生成されたリクエストの内容
- `placeholder`: 使用されたプレースホルダ名
- `payload`: 使用されたペイロード
- `position`: プレースホルダの位置（Sniper攻撃用）
- `applied_to`: 適用されたプレースホルダのリスト（JSON形式）
- `created_at`: 生成日時

#### job_results
- `id`: 結果の一意識別子
- `job_id`: ジョブのID
- `request_number`: リクエスト番号
- `request_content`: リクエスト内容
- `placeholder`: プレースホルダ名
- `payload`: ペイロード
- `position`: 位置
- `http_response`: HTTPレスポンス（JSON形式）
- `success`: 成功フラグ
- `error_message`: エラーメッセージ
- `created_at`: 結果作成日時

## 戦略の詳細

### Sniper Attack
- **用途**: 個別のパラメータで一般的な脆弱性をファジングする場合
- **例**: SQLインジェクション、XSSなどの単一パラメータ攻撃
- **プレースホルダ形式**: `<<>>`（固定形式）

### Battering Ram Attack
- **用途**: 同じ入力を複数の場所に挿入する必要がある場合
- **例**: ユーザー名をクッキーとボディパラメータの両方に挿入

### Pitchfork Attack
- **用途**: 関連するが異なる入力を複数の場所に挿入する場合
- **例**: ユーザー名とそのユーザーに対応する既知のID番号

### Cluster Bomb Attack
- **用途**: 無関係または未知の入力を複数の場所に挿入する場合
- **例**: ユーザー名とパスワードの推測

## 脆弱性分析の詳細

### エラーパターン検出
- **40+のデフォルトパターン**: SQL、データベース、スタックトレース、システム情報等
- **カスタムパターン**: 独自のエラーパターンを指定可能
- **深刻度判定**: 自動的にhigh/medium/lowを判定
- **証拠収集**: エラーが検出された箇所の前後コンテキストを取得

### ペイロード反射検出
- **HTMLエスケープチェック**: `<`, `>`, `"`, `'`のエスケープ状況確認
- **URLエンコーディングチェック**: URLエンコーディングの適用状況確認
- **JavaScriptエンコーディングチェック**: JSエスケープの適用状況確認
- **エンコーディング統計**: 全体的なエンコーディング適用状況の統計
- **XSS脆弱性検出**: 危険なペイロードの未エスケープ反射を特定

### 時間遅延検出
- **ベースライン比較**: 通常レスポンス時間との比較
- **閾値設定**: カスタマイズ可能な遅延判定閾値
- **攻撃タイプ推定**: ペイロード内容から攻撃タイプを推定
- **統計情報**: 平均・中央値・ベースライン時間の提供

## 注意事項

- Cluster Bomb Attackは、ペイロードセットが多い場合に非常に大きな数のリクエストを生成する可能性があります
- ペイロードセットの数は、Pitchfork AttackとCluster Bomb Attackではプレースホルダの数と一致する必要があります
- テンプレート内のプレースホルダは `<<placeholder_name>>` の形式で指定してください（Sniper攻撃では `<<>>`）
- データベースファイル（`fuzzer_requests.db`）は自動的に作成されます
- 履歴データは永続的に保存されるため、不要なデータは適宜削除してください
- 全てのAPIエンドポイントはJWT認証が必要です
- 脆弱性分析は実行完了したジョブに対してのみ実行可能です
- 時間遅延分析では、ネットワーク状況による誤検知の可能性があります

## セキュリティ注意事項

- 本ツールは教育・研究目的、または適切な許可を得たペネトレーションテスト用途でのみ使用してください
- 許可なく他者のシステムに対して使用することは法的問題を引き起こす可能性があります
- 実際の攻撃ペイロードを含むため、テスト環境でのみ使用することを強く推奨します
- パスワードは適切にハッシュ化されて保存されますが、強力なパスワードを使用してください

## 開発

### 依存関係
- FastAPI: Webフレームワーク
- SQLAlchemy: ORM
- Alembic: データベースマイグレーション
- Uvicorn: ASGIサーバー
- Pydantic: データバリデーション
- python-jose: JWT認証
- passlib: パスワードハッシュ化
- aiohttp: 非同期HTTPクライアント

### ファイル構成
```
fuzzer20250630/
├── main.py                           # メインAPI
├── database.py                       # データベースモデルとマネージャー
├── vulnerability_analysis.py         # 脆弱性分析エンジン
├── requirements.txt                  # 依存関係
├── test_sniper.py                   # Sniper攻撃テスト
├── example_usage.py                 # 使用例
├── test_separated_vulnerability_apis.py  # 分析APIテスト
├── test_comprehensive_apis.py       # 包括的APIテスト
├── web_test.html                    # テスト用Webページ
├── history.html                     # 履歴表示用Webページ
├── fuzzer_requests.db              # SQLiteデータベース
├── DEPLOY.md                       # デプロイガイド
└── README.md                       # このファイル
```

## ライセンス

MIT License 

### 基本的な使用例

**Sniper攻撃の例:**

```json
{
  "template": "GET /hack/normalxss.php?cmd=<<>> HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
  "placeholders": ["cmd", "host"],
  "strategy": "sniper",
  "payload_sets": [
    {
      "name": "sql_injection",
      "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
    }
  ]
}
```

### 変異機能（Mutations）

辞書的な値に加えて、長大な文字列を生成するためのrepeat機能をサポートしています。

**変異機能の使用例:**

```json
{
  "template": "GET /api/test?param=<<X>> HTTP/1.1\nHost: example.com",
  "mutations": [
    {
      "token": "<<X>>",
      "strategy": "dictionary",
      "values": [
        "<script>",
        "' OR 1=1 --",
        {
          "value": "A",
          "repeat": 1000
        },
        {
          "value": "ABC",
          "repeat": 500
        }
      ]
    }
  ]
}
```

**複数トークンの例:**

```json
{
  "template": "GET /api/test?param1=<<X>>&param2=<<Y>> HTTP/1.1\nHost: example.com",
  "mutations": [
    {
      "token": "<<X>>",
      "strategy": "dictionary",
      "values": [
        "test1",
        {
          "value": "A",
          "repeat": 100
        }
      ]
    },
    {
      "token": "<<Y>>",
      "strategy": "dictionary",
      "values": [
        "test2",
        {
          "value": "B",
          "repeat": 50
        }
      ]
    }
  ]
}
```

**エンドポイント:** `POST /api/mutations` 

### 脆弱性分析の実用例

**完全な分析ワークフロー:**

1. **リクエスト生成**
```bash
curl -X POST "http://localhost:8000/api/replace-placeholders" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "template": "GET /search?q=<<QUERY>>&type=<<TYPE>> HTTP/1.1\nHost: target.com\n\n",
       "placeholders": ["QUERY", "TYPE"],
       "strategy": "cluster_bomb",
       "payload_sets": [
         {
           "name": "attack_payloads",
           "payloads": ["'\''", "<script>alert(1)</script>", "'; WAITFOR DELAY '\''00:00:03'\''--"]
         },
         {
           "name": "types",
           "payloads": ["user", "admin"]
         }
       ]
     }'
```

2. **リクエスト実行**
```bash
curl -X POST "http://localhost:8000/api/execute-requests" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "request_id": 1,
       "http_config": {
         "scheme": "https",
         "base_url": "target.com",
         "timeout": 30,
         "sequential_execution": true,
         "request_delay": 1.0
       }
     }'
```

3. **脆弱性分析**
```bash
# エラーパターン分析
curl -X POST "http://localhost:8000/api/jobs/JOB_ID/analyze/error-patterns" \
     -H "Authorization: Bearer YOUR_TOKEN"

# ペイロード反射分析  
curl -X POST "http://localhost:8000/api/jobs/JOB_ID/analyze/payload-reflection" \
     -H "Authorization: Bearer YOUR_TOKEN"

# 時間遅延分析
curl -X POST "http://localhost:8000/api/jobs/JOB_ID/analyze/time-delay" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"time_threshold": 1.5}'
``` 