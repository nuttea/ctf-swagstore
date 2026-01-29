# チャットボットデプロイガイド

## 🚀 自動セットアップの概要

このチャットボットは、Kubernetes Jobを使用してデプロイ時に自動的にセットアップされます。

### デプロイ時の自動実行フロー

```
1. PreSync Job (chatbot-pgvector-setup)
   ↓
   PostgreSQLにpgvector拡張をインストール
   ↓
2. 通常のアプリケーションデプロイ
   ↓
3. PostSync Job (chatbot-embed-products)
   ↓
   商品データの埋め込みベクトルを生成
   ↓
4. チャットボット準備完了！
```

## 📦 含まれるコンポーネント

### 1. **chatbot-setup-job.yaml**
- ConfigMap: SQLスクリプトとセットアップスクリプト
- Secret: AWS Bedrock認証情報
- Job: pgvectorセットアップ（PreSync）
- Job: 商品埋め込み生成（PostSync）

### 2. **chatbot-embedder**
- Go製CLIツール
- Bedrock Titan Embeddingsを使用
- 商品データをベクトル化してPostgreSQLに保存

### 3. **フロントエンド（実装予定）**
- チャットウィジェット UI
- Bedrock Claude 3連携
- RAG検索機能

## 🔧 デプロイ手順

### 前提条件

1. ✅ Kubernetes クラスタが稼働中
2. ✅ PostgreSQL（postgres Pod）が稼働中
3. ✅ AWS Bedrockへのアクセス権限
4. ✅ モデルアクセスが承認済み
   - Claude 3 Haiku/Sonnet
   - Titan Embeddings V2

### ステップ 1: AWS認証情報を設定

`kubernetes-manifests/chatbot-setup-job.yaml`のSecretセクションは既に設定済みです：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-bedrock-credentials
type: Opaque
stringData:
  AWS_REGION: "ap-northeast-1"
  AWS_ACCESS_KEY_ID: "YOUR_AWS_ACCESS_KEY_ID"
  AWS_SECRET_ACCESS_KEY: "YOUR_AWS_SECRET_ACCESS_KEY"
```

### ステップ 2: PostgreSQLにpgvector拡張をインストール

PostgreSQL Podでpgvectorがインストールされていることを確認：

```bash
# PostgreSQL Podに入る
kubectl exec -it deployment/postgres -- bash

# pgvectorがインストール可能か確認
psql -U postgres -d swagstoredb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**注意**: pgvectorがインストールされていない場合、PostgreSQLイメージを`pgvector/pgvector:pg15`に変更する必要があります。

### ステップ 3: embedderイメージをビルド

```bash
# プロジェクトルートで
cd src/chatbot-embedder

# ローカルビルド
docker build -t chatbot-embedder:latest .

# または skaffold経由
cd ../..
skaffold build
```

### ステップ 4: チャットボットJobをデプロイ

```bash
# ConfigMap, Secret, Jobsをデプロイ
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

### ステップ 5: 実行状況を確認

```bash
# pgvectorセットアップJobの状態確認
kubectl get job chatbot-pgvector-setup
kubectl logs job/chatbot-pgvector-setup

# 商品埋め込み生成Jobの状態確認
kubectl get job chatbot-embed-products
kubectl logs job/chatbot-embed-products -f

# 成功例:
# 🚀 Starting product embeddings generation...
# ✅ Bedrock client initialized
# ✅ Connected to PostgreSQL
# 📦 Found 9 products to process
# [1/9] Processing: Vintage Typewriter
#    ✅ Embedded successfully (vector dim: 1024)
# ...
# 🎉 Embedding generation completed!
```

### ステップ 6: 埋め込みデータを確認

```bash
kubectl exec -it deployment/postgres -- psql -U postgres -d swagstoredb

# PostgreSQL内で
SELECT 
    product_id, 
    product_name, 
    price_usd,
    array_length(embedding, 1) as vector_dim,
    created_at
FROM product_embeddings
ORDER BY created_at DESC;
```

期待される出力：
```
 product_id | product_name        | price_usd | vector_dim | created_at
------------+---------------------+-----------+------------+----------------------------
 001        | Vintage Typewriter  | 67.99     | 1024       | 2024-01-15 10:30:15.123456
 ...
```

## 🔄 再デプロイ時の動作

### 通常のアプリケーション再デプロイ
```bash
skaffold run
```
- pgvectorセットアップJob（PreSync）が再実行される
- 商品埋め込み生成Job（PostSync）が再実行される
- 既存の埋め込みデータは更新される（UPSERT）

### 手動で埋め込みを再生成
```bash
# Jobを削除
kubectl delete job chatbot-embed-products

# 再作成
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 🐛 トラブルシューティング

### エラー: "extension \"vector\" does not exist"

**原因**: PostgreSQLにpgvectorがインストールされていない

**解決方法**:
```yaml
# kubernetes-manifests/postgres.yamlを修正
spec:
  containers:
  - name: postgres
    image: pgvector/pgvector:pg15  # ← 変更
```

### エラー: "AccessDeniedException"

**原因**: AWS BedrockのIAM権限が不足、またはモデルアクセスが未承認

**解決方法**:
1. AWS Console → Bedrock → Model access
2. Claude 3, Titan Embeddingsへのアクセスを申請
3. IAMポリシーを確認

### エラー: Job が Pending のまま

**原因**: PostgreSQLが起動していない

**解決方法**:
```bash
# PostgreSQLの状態確認
kubectl get pods -l app=postgres

# PostgreSQLを起動
kubectl apply -f kubernetes-manifests/postgres.yaml
```

### エラー: "connection refused"

**原因**: PostgreSQLサービス名が間違っている

**解決方法**:
```bash
# サービス名を確認
kubectl get svc | grep postgres

# 環境変数を修正（必要に応じて）
POSTGRES_HOST=postgres  # ← サービス名と一致させる
```

## 📊 モニタリング

### Datadog統合（将来実装）

```go
// チャットボットメトリクス
span.SetTag("chatbot.embeddings.generated", count)
span.SetTag("chatbot.embeddings.dimensions", 1024)
span.SetTag("chatbot.provider", "bedrock")
span.SetTag("chatbot.model", "titan-embed-text-v2")
```

### CloudWatch統合

AWS CloudWatchで Bedrock使用状況を確認：
- リクエスト数
- レイテンシー
- エラー率
- トークン使用量

## 💰 コスト見積もり

### Titan Embeddings V2 料金
- $0.0001 / 1,000 tokens

### 商品100件の埋め込み生成コスト
- 平均50 tokens/商品 × 100商品 = 5,000 tokens
- コスト: 約 $0.0005 （0.05円）

### 月次コスト（毎日再デプロイの場合）
- $0.0005 × 30日 = $0.015/月 （約1.5円）

## 🎯 次のステップ

1. ✅ pgvectorセットアップ - 完了
2. ✅ 商品埋め込み生成 - 完了
3. ⏳ フロントエンドUIの実装
4. ⏳ チャットAPIエンドポイントの実装
5. ⏳ RAG検索ロジックの実装

## 📝 クリーンアップ

### Jobsを削除
```bash
kubectl delete job chatbot-pgvector-setup chatbot-embed-products
```

### 埋め込みデータを削除
```bash
kubectl exec -it deployment/postgres -- psql -U postgres -d swagstoredb

# PostgreSQL内で
DROP TABLE IF EXISTS product_embeddings;
```

### Secretを削除
```bash
kubectl delete secret aws-bedrock-credentials
```

## 🔐 セキュリティベストプラクティス

1. ✅ AWS認証情報をSecretとして管理
2. ⚠️ 本番環境では認証情報をハードコードしない
3. ✅ IAMロールを使用（EKS環境推奨）
4. ✅ 最小権限の原則を適用
5. ✅ 定期的なアクセスキーローテーション

## 📚 参考リンク

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Titan Embeddings V2](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Claude 3 Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html)






