# Renderへのデプロイ手順

このドキュメントでは、プレースホルダ置換API（ファザーAPI）をRenderにデプロイする手順を説明します。

## 前提条件

- GitHubアカウント
- Renderアカウント（[render.com](https://render.com)）

## 1. GitHubリポジトリの作成

1. GitHubで新しいリポジトリを作成
2. ローカルのプロジェクトをリモートリポジトリにプッシュ

```bash
# リモートリポジトリを追加
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git

# メインブランチにプッシュ
git push -u origin main
```

## 2. Renderでのセットアップ

### Web Service の作成

1. [Render Dashboard](https://dashboard.render.com) にログイン
2. "New" → "Web Service" をクリック
3. GitHubリポジトリを選択
4. 以下の設定を行う：

#### 基本設定
- **Name**: `fuzzer-api` (または任意の名前)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### 環境変数
以下の環境変数を設定：

| Key | Value | 説明 |
|-----|-------|------|
| `ENVIRONMENT` | `production` | 本番環境フラグ |
| `DATABASE_URL` | (PostgreSQLのURL) | データベース接続URL |

### PostgreSQL データベースの作成

1. Render Dashboard で "New" → "PostgreSQL" をクリック
2. 以下の設定を行う：
   - **Name**: `fuzzer-db` (または任意の名前)
   - **Plan**: Free (開発用)
3. 作成後、"Connections" セクションで **External Database URL** をコピー
4. Web Service の環境変数 `DATABASE_URL` にペースト

## 3. デプロイの実行

1. 設定完了後、"Create Web Service" をクリック
2. Renderが自動的にビルドとデプロイを開始
3. デプロイ完了後、提供されるURLでアクセス可能

## 4. アクセス確認

デプロイ完了後、以下のエンドポイントでアクセス確認：

- **API Root**: `https://YOUR_APP_NAME.onrender.com/`
- **テストページ**: `https://YOUR_APP_NAME.onrender.com/test`
- **履歴ページ**: `https://YOUR_APP_NAME.onrender.com/history-page`
- **API ドキュメント**: `https://YOUR_APP_NAME.onrender.com/docs`

## 5. 注意事項

### データベース
- SQLiteは使用できません（ファイルシステムが永続化されないため）
- PostgreSQLを使用してください

### ファイルストレージ
- ファイルアップロード機能がある場合は、外部ストレージ（AWS S3など）の使用を検討してください

### 環境変数
本番環境では以下の環境変数を適切に設定してください：
- `DATABASE_URL`: PostgreSQL接続文字列
- `ENVIRONMENT`: `production`

### パフォーマンス
- Free プランでは制限があります
- 本格的な利用の場合は有料プランの検討をお勧めします

## 6. 更新デプロイ

コードを更新する場合：

```bash
# 変更をコミット
git add .
git commit -m "更新内容の説明"

# リモートリポジトリにプッシュ
git push origin main
```

GitHubにプッシュすると、Renderが自動的に再デプロイを実行します。

## 7. ログの確認

Render Dashboard の "Logs" セクションでアプリケーションのログを確認できます。
エラーや問題がある場合は、ここでデバッグ情報を確認してください。

## 8. カスタムドメイン（オプション）

有料プランでは、カスタムドメインの設定が可能です。
詳細は[Renderの公式ドキュメント](https://render.com/docs/custom-domains)を参照してください。 