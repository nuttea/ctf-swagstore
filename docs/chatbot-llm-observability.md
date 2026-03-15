# Swagstore Chatbot - Datadog LLM Observability

## 概要

SwagstoreチャットボットはAWS Bedrock（Claude 3 + Titan Embeddings）を利用したRAG対応のAIアシスタントです。
Python製APIとして別Podで実行され、**Datadog LLM Observability**で完全にモニタリングされます。

## アーキテクチャ

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────┐
│  Frontend   │─────▶│  Chatbot    │─────▶│  AWS Bedrock     │
│   (Go)      │      │  API (Py)   │      │  - Claude 3      │
│             │      │             │      │  - Titan Embed   │
└─────────────┘      └─────────────┘      └──────────────────┘
      │                     │                      
      │                     ▼                      
      │              ┌─────────────┐               
      │              │  PostgreSQL │               
      │              │  (pgvector) │               
      │              └─────────────┘               
      │                                            
      ▼                                            
┌──────────────────────────────────────────────┐
│          Datadog LLM Observability           │
│  - トレース                                    │
│  - メトリクス                                  │
│  - LLM呼び出しの完全可視化                     │
└──────────────────────────────────────────────┘
```

## コンポーネント

### 1. Chatbot API (Python)
- **ファイル**: `src/chatbot-api/app.py`
- **フレームワーク**: Flask + Gunicorn
- **機能**:
  - RAG検索（PostgreSQL pgvector）
  - AWS Bedrock Claude 3による応答生成
  - Datadog APM & LLM Observability統合

### 2. Frontend Proxy (Go)
- **ファイル**: `src/frontend/main.go`
- **エンドポイント**: `/api/chatbot/chat`
- **機能**: Chatbot APIへのプロキシ

### 3. Chat Widget (HTML/JS)
- **ファイル**: `src/frontend/templates/chatbot.html`
- **機能**: 
  - モダンなチャットUI
  - Datadog RUM統合
  - 商品カード表示

## Datadog LLM Observability 機能

### トレース情報

#### 1. LLM呼び出しトレース
```python
with LLMObs.llm(
    model_name="anthropic.claude-3-haiku-20240307-v1:0",
    model_provider="bedrock",
    name="chat_completion",
    ml_app="swagstore-chatbot"
) as llm_span:
    # 入力データを記録
    llm_span.annotate(
        input_data=[{"role": "user", "content": user_message}],
        parameters={
            "temperature": 0.7,
            "max_tokens": 1000,
            "rag_products_count": len(similar_products)
        }
    )
    
    # Bedrock API呼び出し
    response = bedrock_client.invoke_model(...)
    
    # 出力データとメトリクスを記録
    llm_span.annotate(
        output_data=[{"role": "assistant", "content": ai_message}],
        metrics={
            "input_tokens": 150,
            "output_tokens": 200,
            "total_tokens": 350
        }
    )
```

#### 2. RAG検索トレース
```python
with tracer.trace('postgres.vector_search', service='chatbot-api') as span:
    span.set_tag('vector.top_k', 5)
    span.set_tag('vector.dimensions', 1024)
    span.set_tag('vector.results_count', len(products))
    span.set_tag('vector.avg_similarity', avg_similarity)
```

#### 3. 埋め込み生成トレース
```python
with tracer.trace('bedrock.embedding', service='chatbot-api') as span:
    span.set_tag('embedding.model', 'amazon.titan-embed-text-v2:0')
    span.set_tag('embedding.text_length', len(text))
    span.set_tag('embedding.dimensions', 1024)
```

### 収集されるメトリクス

| メトリクス | 説明 |
|---------|------|
| `input_tokens` | LLMへの入力トークン数 |
| `output_tokens` | LLMからの出力トークン数 |
| `total_tokens` | 合計トークン数（コスト計算用） |
| `vector.avg_similarity` | RAG検索の平均類似度 |
| `vector.results_count` | 検索結果数 |

### タグ情報

| タグ | 説明 |
|-----|------|
| `model_name` | 使用したLLMモデル |
| `model_provider` | プロバイダー（bedrock） |
| `rag.enabled` | RAGの有効/無効 |
| `rag.top_k` | RAG検索のTop-K |
| `embedding.model` | 埋め込みモデル |
| `user.username` | ユーザー名（オプション） |

## デプロイ

### 1. ビルド＆デプロイ
```bash
# Skaffoldで自動デプロイ
skaffold dev
```

### 2. 個別にビルド（必要な場合）
```bash
# Chatbot APIイメージをビルド
cd src/chatbot-api
docker buildx build --platform linux/amd64 \
  -t docker.io/koheisato353/chatbot-api:v1 --push .
```

### 3. Kubernetes manifest適用
```bash
kubectl apply -f kubernetes-manifests/chatbot-api.yaml
```

## 環境変数

### Chatbot API Pod

#### AWS Bedrock設定
```yaml
- name: AWS_REGION
  value: "ap-northeast-1"
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: aws-bedrock-credentials
      key: AWS_ACCESS_KEY_ID
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: aws-bedrock-credentials
      key: AWS_SECRET_ACCESS_KEY
```

#### PostgreSQL設定
```yaml
- name: POSTGRES_HOST
  value: "postgres"
- name: POSTGRES_PORT
  value: "5432"
- name: POSTGRES_USER
  value: "postgres"
- name: POSTGRES_PASSWORD
  value: "password"
- name: POSTGRES_DB
  value: "swagstoredb"
```

#### LLM設定
```yaml
- name: LLM_MODEL_ID
  value: "anthropic.claude-3-haiku-20240307-v1:0"
- name: EMBEDDING_MODEL_ID
  value: "amazon.titan-embed-text-v2:0"
- name: RAG_TOP_K
  value: "5"
```

#### Datadog設定
```yaml
- name: DD_AGENT_HOST
  valueFrom:
    fieldRef:
      fieldPath: status.hostIP
- name: DD_ENV
  value: "ctf"
- name: DD_SERVICE
  value: "chatbot-api"
- name: DD_VERSION
  value: "1.0.0"
- name: DD_LLMOBS_ENABLED
  value: "true"
- name: DD_LLMOBS_ML_APP
  value: "swagstore-chatbot"
```

## 使用方法

### 1. チャットウィジェットを開く
画面右下のチャットアイコンをクリック

### 2. 商品について質問
例:
- 「ノートパソコンのバッグを探しています」
- 「防水性のある商品はありますか？」
- 「$50以下の商品を教えてください」

### 3. AIが応答
- RAGで関連商品を検索
- Claude 3が自然な回答を生成
- 商品カード形式で表示

## Datadog での確認方法

### 1. LLM Observability画面
```
Datadog → LLM Observability → swagstore-chatbot
```

### 2. 確認できる情報
- **トレース**: 全てのLLM呼び出しの詳細
- **入力/出力**: 質問と回答の内容
- **トークン数**: コスト計算用の詳細メトリクス
- **レイテンシー**: 応答時間
- **エラー率**: 失敗した呼び出し
- **RAGメトリクス**: 検索精度と性能

### 3. APMトレース
```
Datadog → APM → Services → chatbot-api
```

### 4. カスタムダッシュボード
```
Datadog → Dashboards → Create New Dashboard
```

推奨メトリクス:
- `trace.llm.request.duration`
- `trace.llm.request.input_tokens`
- `trace.llm.request.output_tokens`
- `trace.llm.request.error_rate`
- `trace.bedrock.embedding.duration`
- `trace.postgres.vector_search.duration`

## トラブルシューティング

### 1. チャットボットが応答しない
```bash
# Chatbot API Podのログを確認
kubectl logs -l app=chatbot-api

# Frontend Podのログを確認
kubectl logs -l app=frontend | grep chatbot
```

### 2. Datadog LLM Observabilityにデータが表示されない
```bash
# DD_LLMOBS_ENABLEDが有効か確認
kubectl get pod -l app=chatbot-api -o yaml | grep DD_LLMOBS_ENABLED

# Datadog Agentとの接続を確認
kubectl exec -it <chatbot-api-pod> -- curl http://$DD_AGENT_HOST:8126/info
```

### 3. RAG検索が機能しない
```bash
# PostgreSQLの埋め込みテーブルを確認
kubectl exec deployment/postgres -- \
  env PGPASSWORD=password psql -U postgres -d swagstoredb \
  -c "SELECT COUNT(*) FROM product_embeddings;"

# 結果が9件（全商品数）であることを確認
```

### 4. AWS Bedrockエラー
```bash
# AWS認証情報を確認
kubectl get secret aws-bedrock-credentials -o yaml

# Claude 3モデルへのアクセス権限を確認（AWS Console）
```

## パフォーマンス最適化

### 1. RAG検索の最適化
```python
# Top-Kを調整（デフォルト: 5）
RAG_TOP_K=3  # より高速だが精度低下
RAG_TOP_K=10 # より正確だが遅い
```

### 2. LLMパラメータの調整
```python
# temperature: 0.0-1.0（低いほど決定的）
'temperature': 0.7

# max_tokens: 出力の最大トークン数
'max_tokens': 1000
```

### 3. レプリカ数の調整
```yaml
# kubernetes-manifests/chatbot-api.yaml
spec:
  replicas: 2  # 負荷に応じて増減
```

## コスト管理

### AWS Bedrockコスト
- **Claude 3 Haiku**: $0.00025/1K input tokens, $0.00125/1K output tokens
- **Titan Embeddings V2**: $0.00002/1K tokens

### コスト削減のヒント
1. `max_tokens`を制限
2. キャッシング機能の活用（将来実装予定）
3. Datadog LLM Observabilityでトークン使用量を監視

## セキュリティ

### 1. AWS認証情報の保護
```bash
# Secretとして保存
kubectl create secret generic aws-bedrock-credentials \
  --from-literal=AWS_REGION=ap-northeast-1 \
  --from-literal=AWS_ACCESS_KEY_ID=AKIA... \
  --from-literal=AWS_SECRET_ACCESS_KEY=...
```

### 2. プロンプトインジェクション対策
- システムプロンプトで指示を明確化
- 商品情報のみを使用するよう制限
- ユーザー入力のサニタイズ

### 3. レート制限
```yaml
# リソース制限でPodごとのリクエスト数を制御
resources:
  limits:
    cpu: "500m"
    memory: "1Gi"
```

## 今後の改善予定

- [ ] キャッシング機能（同じ質問の再利用）
- [ ] ストリーミング応答
- [ ] 多言語対応
- [ ] 会話履歴の保存
- [ ] カート追加の直接統合
- [ ] A/Bテスト（異なるLLMモデル）

## 参考資料

- [Datadog LLM Observability Documentation](https://docs.datadoghq.com/llm_observability/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)






