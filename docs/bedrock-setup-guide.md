# AWS Bedrock RAGチャットボット セットアップガイド

## 🔑 必要な情報

### 1. AWS認証情報
- **AWS Access Key ID**: `AKIAIOSFODNN7EXAMPLE` (例)
- **AWS Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (例)
- **AWS Region**: `us-east-1` または `us-west-2` など

### 2. IAMポリシー設定

Bedrockを使用するには、以下のIAMポリシーが必要です：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
```

### 3. Bedrockモデルへのアクセス申請

AWS Bedrockコンソールで、使用したいモデルへのアクセスを申請する必要があります：

1. AWS Management Console → Bedrock
2. 左メニュー「Model access」をクリック
3. 使用したいモデルを選択：
   - ✅ **Claude 3 Haiku** (推奨 - コスト効率)
   - ✅ **Claude 3 Sonnet** (推奨 - バランス)
   - ✅ **Titan Embeddings V2** (埋め込み生成用)
4. 「Request model access」をクリック

**注意**: モデルアクセスの承認には数分〜数時間かかる場合があります。

## 📍 利用可能なリージョン

Bedrockが利用可能な主なリージョン：
- `us-east-1` (バージニア北部) - 推奨
- `us-west-2` (オレゴン)
- `ap-northeast-1` (東京)
- `ap-southeast-1` (シンガポール)
- `eu-central-1` (フランクフルト)

## 🔧 環境変数設定

### ローカル開発環境

`.env`ファイルを作成：

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
```

### Kubernetes環境

Secretを作成：

```bash
kubectl create secret generic aws-bedrock-credentials \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key-id \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-access-key
```

## 💰 料金について

### Bedrock料金 (2024年11月時点の概算)

#### LLMモデル (入力/出力あたり)
- **Claude 3 Haiku**: $0.00025 / 1K tokens (入力), $0.00125 / 1K tokens (出力)
- **Claude 3 Sonnet**: $0.003 / 1K tokens (入力), $0.015 / 1K tokens (出力)
- **Claude 3 Opus**: $0.015 / 1K tokens (入力), $0.075 / 1K tokens (出力)

#### 埋め込みモデル
- **Titan Embeddings V2**: $0.0001 / 1K tokens

#### 概算コスト例
- チャット1回あたり: $0.001 - $0.01 (Haikuの場合)
- 商品埋め込み生成 (100商品): $0.01 - $0.05
- 月間1,000チャット: $1 - $10

**OpenAIと比較して約50-70%安い**

## 🚀 セットアップ手順

### 1. AWS IAMユーザー作成

```bash
# AWS CLIを使用
aws iam create-user --user-name bedrock-chatbot-user

# アクセスキーを作成
aws iam create-access-key --user-name bedrock-chatbot-user
```

### 2. IAMポリシーをアタッチ

```bash
# ポリシーJSONファイルを作成
cat > bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# ポリシーを作成してアタッチ
aws iam put-user-policy \
  --user-name bedrock-chatbot-user \
  --policy-name BedrockInvokePolicy \
  --policy-document file://bedrock-policy.json
```

### 3. モデルアクセスを確認

```bash
# Bedrock利用可能なモデルを確認
aws bedrock list-foundation-models --region us-east-1
```

## 🔍 トラブルシューティング

### エラー: "Access Denied"
→ IAMポリシーを確認、モデルアクセスが承認されているか確認

### エラー: "Model not found"
→ 指定したリージョンでモデルが利用可能か確認

### エラー: "ThrottlingException"
→ リクエスト数が多すぎる場合、リトライロジックを実装

## 📚 使用可能なモデルID

### LLMモデル
```
anthropic.claude-3-haiku-20240307-v1:0    # 最速・最安
anthropic.claude-3-sonnet-20240229-v1:0   # バランス型（推奨）
anthropic.claude-3-opus-20240229-v1:0     # 最高品質
amazon.titan-text-express-v1              # AWS製
ai21.j2-ultra-v1                          # AI21 Labs製
```

### 埋め込みモデル
```
amazon.titan-embed-text-v2:0              # 最新版（推奨）
amazon.titan-embed-text-v1                # 旧版
cohere.embed-english-v3                   # Cohere製
cohere.embed-multilingual-v3              # 多言語対応
```

## ⚙️ 推奨設定

### 開発環境
- モデル: Claude 3 Haiku
- リージョン: us-east-1
- タイムアウト: 30秒

### 本番環境
- モデル: Claude 3 Sonnet
- リージョン: 最も近いリージョン
- タイムアウト: 30秒
- リトライ: 3回

## 🔐 セキュリティベストプラクティス

1. ✅ IAMユーザーには最小権限のみ付与
2. ✅ アクセスキーは環境変数またはSecretに保存
3. ✅ ローテーション: アクセスキーを定期的に更新
4. ✅ CloudTrailでAPI使用状況を監視
5. ✅ VPCエンドポイント経由でアクセス（本番環境）

## 📊 監視・ログ

### CloudWatch Metricsで監視
- リクエスト数
- レイテンシー
- エラー率
- トークン使用量

### Datadog統合
```go
span.SetTag("llm.provider", "bedrock")
span.SetTag("llm.model", modelId)
span.SetTag("llm.tokens.input", inputTokens)
span.SetTag("llm.tokens.output", outputTokens)
```

## 🎯 次のステップ

1. ✅ AWS認証情報を取得
2. ✅ IAMポリシーを設定
3. ✅ Bedrockモデルアクセスを申請
4. ✅ 環境変数を設定
5. ✅ チャットボットコードを実装
6. ✅ RAG用にpgvectorをセットアップ
7. ✅ 商品データの埋め込みを生成
8. ✅ テスト・デプロイ


