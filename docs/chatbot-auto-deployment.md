# 🤖 チャットボット自動デプロイ構成

PostgreSQLデプロイ時に自動的にRAG基盤がセットアップされます。

## 🚀 自動実行フロー

```
1. skaffold run 実行
   ↓
2. PostgreSQL Pod起動
   ├─ pgvector/pgvector:pg15イメージ使用
   ├─ init-db.sh実行（自動）
   │  ├─ swagstoredb作成
   │  ├─ pgvector拡張インストール ← ここで自動！
   │  ├─ product_embeddingsテーブル作成 ← ここで自動！
   │  └─ HNSWインデックス作成 ← ここで自動！
   └─ PostgreSQL Ready
   ↓
3. chatbot-embed-products Job実行（PostSync）
   ├─ PostgreSQL準備完了を待機
   ├─ AWS Bedrock Titan Embeddingsで商品ベクトル化
   └─ product_embeddingsテーブルに保存
   ↓
4. RAG基盤完成！🎉
```

## 📦 含まれるコンポーネント

### 1. PostgreSQL起動時（自動）
**ファイル**: `kubernetes-manifests/postgres.yaml`

```yaml
configMap:
  data:
    init-db.sh: |
      # ... 既存のDB初期化 ...
      
      # ===== Chatbot RAG Setup =====
      CREATE EXTENSION IF NOT EXISTS vector;
      
      CREATE TABLE IF NOT EXISTS product_embeddings (
          id SERIAL PRIMARY KEY,
          product_id VARCHAR(50) NOT NULL,
          product_name VARCHAR(255) NOT NULL,
          description TEXT,
          price_usd DECIMAL(10, 2),
          categories TEXT,
          picture VARCHAR(500),
          embedding vector(1024),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(product_id)
      );
      
      CREATE INDEX product_embeddings_vector_idx 
      ON product_embeddings USING hnsw (embedding vector_cosine_ops);
      # ===== End Chatbot RAG Setup =====
```

### 2. 商品埋め込み生成（自動）
**ファイル**: `kubernetes-manifests/chatbot-setup-job.yaml`

- **Secret**: AWS Bedrock認証情報
- **Job**: chatbot-embed-products（PostSyncフック）
- **Image**: koheisato353/chatbot-embedder:v1

## 🎯 デプロイ方法

### 通常のデプロイ（全自動）

```bash
# これだけで全部自動実行！
skaffold run
```

**実行内容**:
1. ✅ PostgreSQL起動 → pgvector自動セットアップ
2. ✅ chatbot-embedder Job自動実行 → 商品埋め込み生成
3. ✅ RAG基盤完成

### 個別に再実行する場合

#### PostgreSQLの再初期化
```bash
# PVCを削除して再作成
kubectl scale deployment postgres --replicas=0
kubectl delete pvc postgres-pvc
kubectl apply -f kubernetes-manifests/postgres.yaml
kubectl scale deployment postgres --replicas=1
```

#### 商品埋め込みのみ再生成
```bash
# Jobを削除して再実行
kubectl delete job chatbot-embed-products
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 📊 実行確認

### PostgreSQL起動ログを確認
```bash
kubectl logs deployment/postgres -c init-db

# 期待される出力:
# ✅ pgvector setup completed
# CREATE EXTENSION
# CREATE TABLE
# CREATE INDEX
```

### 商品埋め込みJobを確認
```bash
kubectl logs job/chatbot-embed-products

# 期待される出力:
# 🚀 Starting product embeddings generation...
# ✅ Bedrock client initialized
# ✅ Connected to PostgreSQL
# 📦 Found 9 products to process
# [1/9] Processing: Dog Headphones
#    ✅ Embedded successfully (vector dim: 1024)
# ...
# 🎉 Embedding generation completed!
#    ✅ Success: 9 products
```

### データを確認
```bash
kubectl exec deployment/postgres -- env PGPASSWORD=password psql -U postgres -d swagstoredb -c \
  "SELECT product_id, product_name, price_usd FROM product_embeddings ORDER BY product_id;"
```

## 🔧 設定変更

### AWS認証情報を変更
`kubernetes-manifests/chatbot-setup-job.yaml`を編集：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-bedrock-credentials
type: Opaque
stringData:
  AWS_REGION: "ap-northeast-1"          # ← リージョン
  AWS_ACCESS_KEY_ID: "your-access-key"  # ← アクセスキー
  AWS_SECRET_ACCESS_KEY: "your-secret"  # ← シークレット
```

### 埋め込みモデルを変更
`kubernetes-manifests/chatbot-setup-job.yaml`のJob環境変数を編集：

```yaml
env:
- name: BEDROCK_EMBEDDING_MODEL
  value: "amazon.titan-embed-text-v2:0"  # ← モデルID
- name: EMBEDDING_DIMENSIONS
  value: "1024"  # ← 次元数（256, 512, 1024, 1536）
```

## 🐛 トラブルシューティング

### pgvector拡張がインストールされない

**原因**: PostgreSQLイメージが`pgvector/pgvector:pg15`ではない

**確認**:
```bash
kubectl get pod -l app=postgres -o jsonpath='{.items[0].spec.containers[0].image}'
```

**修正**:
```bash
# postgres.yamlを確認
grep "image:" kubernetes-manifests/postgres.yaml
# 両方とも pgvector/pgvector:pg15 であることを確認
```

### 商品埋め込みJobが失敗

**原因1**: PostgreSQLがまだ起動していない
```bash
kubectl logs job/chatbot-embed-products

# 解決: Jobが自動的にリトライします（backoffLimit: 2）
```

**原因2**: AWS認証情報が間違っている
```bash
kubectl logs job/chatbot-embed-products | grep -i error

# 解決: chatbot-setup-job.yamlのSecretを修正
```

### 既存のデータがある場合

product_embeddingsテーブルは`CREATE TABLE IF NOT EXISTS`なので、既存データは保持されます。

再生成する場合:
```bash
kubectl exec deployment/postgres -- env PGPASSWORD=password psql -U postgres -d swagstoredb -c \
  "TRUNCATE TABLE product_embeddings;"
  
kubectl delete job chatbot-embed-products
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 💰 コスト

### 初回デプロイ（9商品）
- 埋め込み生成: 約$0.0005（0.05円）

### 毎日再デプロイする場合
- 月間: 約$0.015（1.5円）

## 🎯 利点

✅ **完全自動化**: `skaffold run`だけで全て完了
✅ **冪等性**: 何度実行しても安全
✅ **障害回復**: PostgreSQL再起動時も自動再セットアップ
✅ **メンテナンス不要**: 手動操作ゼロ
✅ **CI/CD対応**: パイプラインに組み込み可能

## 📝 ファイル構成

```
kubernetes-manifests/
├── postgres.yaml                    # ← pgvector自動セットアップ組込済
└── chatbot-setup-job.yaml          # ← 商品埋め込み自動生成Job

src/
└── chatbot-embedder/               # ← 埋め込み生成ツール
    ├── main.go
    ├── Dockerfile
    └── go.mod

skaffold.yaml                       # ← 自動デプロイ設定
```

## 🔗 関連ドキュメント

- [README-CHATBOT.md](../README-CHATBOT.md) - チャットボット全体概要
- [bedrock-setup-guide.md](./bedrock-setup-guide.md) - AWS Bedrockセットアップ
- [chatbot-deployment-guide.md](./chatbot-deployment-guide.md) - 手動デプロイ手順

## ✨ まとめ

PostgreSQLデプロイ時に自動的に：
1. ✅ pgvector拡張がインストールされる
2. ✅ product_embeddingsテーブルが作成される
3. ✅ 商品の埋め込みベクトルが生成される

**結果**: `skaffold run`一発でRAG基盤が完成！🎉






