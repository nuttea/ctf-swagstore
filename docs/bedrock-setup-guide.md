# AWS Bedrock RAG Chatbot Setup Guide

## 🔑 Required Information

### 1. AWS Credentials
- **AWS Access Key ID**: `AKIAIOSFODNN7EXAMPLE` (example)
- **AWS Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (example)
- **AWS Region**: `us-east-1` or `us-west-2`, etc.

### 2. IAM Policy

The following IAM policy is required to use Bedrock:

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

### 3. Requesting Bedrock Model Access

Request access to the required models in the AWS Bedrock console:

1. AWS Management Console → Bedrock
2. Click "Model access" in the left menu
3. Select the models you need:
   - ✅ **Claude 3 Haiku** (recommended — cost-efficient)
   - ✅ **Claude 3 Sonnet** (recommended — balanced)
   - ✅ **Titan Embeddings V2** (for embedding generation)
4. Click "Request model access"

**Note**: Model access approval may take a few minutes to several hours.

## 📍 Available Regions

Main regions where Bedrock is available:
- `us-east-1` (N. Virginia) — recommended
- `us-west-2` (Oregon)
- `ap-northeast-1` (Tokyo)
- `ap-southeast-1` (Singapore)
- `eu-central-1` (Frankfurt)

## 🔧 Environment Variable Configuration

### Local Development

Create a `.env` file:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
```

### Kubernetes

Create a Secret:

```bash
kubectl create secret generic aws-bedrock-credentials \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key-id \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-access-key
```

## 💰 Pricing

### Bedrock Pricing (approximate as of November 2024)

#### LLM Models (per input/output)
- **Claude 3 Haiku**: $0.00025 / 1K tokens (input), $0.00125 / 1K tokens (output)
- **Claude 3 Sonnet**: $0.003 / 1K tokens (input), $0.015 / 1K tokens (output)
- **Claude 3 Opus**: $0.015 / 1K tokens (input), $0.075 / 1K tokens (output)

#### Embedding Models
- **Titan Embeddings V2**: $0.0001 / 1K tokens

#### Cost Examples
- Per chat request: $0.001 - $0.01 (with Haiku)
- Generate embeddings for 100 products: $0.01 - $0.05
- 1,000 chats per month: $1 - $10

**Approximately 50–70% cheaper than OpenAI**

## 🚀 Setup Steps

### 1. Create an IAM user

```bash
# Using AWS CLI
aws iam create-user --user-name bedrock-chatbot-user

# Create access key
aws iam create-access-key --user-name bedrock-chatbot-user
```

### 2. Attach IAM policy

```bash
# Create policy JSON file
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

# Create and attach the policy
aws iam put-user-policy \
  --user-name bedrock-chatbot-user \
  --policy-name BedrockInvokePolicy \
  --policy-document file://bedrock-policy.json
```

### 3. Verify model access

```bash
# List available Bedrock models
aws bedrock list-foundation-models --region us-east-1
```

## 🔍 Troubleshooting

### Error: "Access Denied"
→ Check IAM policy and verify model access has been approved.

### Error: "Model not found"
→ Check that the specified model is available in the selected region.

### Error: "ThrottlingException"
→ Too many requests — implement retry logic with backoff.

## 📚 Available Model IDs

### LLM Models
```
anthropic.claude-3-haiku-20240307-v1:0    # Fastest, cheapest
anthropic.claude-3-sonnet-20240229-v1:0   # Balanced (recommended)
anthropic.claude-3-opus-20240229-v1:0     # Highest quality
amazon.titan-text-express-v1              # AWS native
ai21.j2-ultra-v1                          # AI21 Labs
```

### Embedding Models
```
amazon.titan-embed-text-v2:0              # Latest (recommended)
amazon.titan-embed-text-v1                # Legacy
cohere.embed-english-v3                   # Cohere (English)
cohere.embed-multilingual-v3              # Cohere (multilingual)
```

## ⚙️ Recommended Configuration

### Development
- Model: Claude 3 Haiku
- Region: us-east-1
- Timeout: 30 seconds

### Production
- Model: Claude 3 Sonnet
- Region: closest available region
- Timeout: 30 seconds
- Retries: 3

## 🔐 Security Best Practices

1. ✅ Grant only the minimum required permissions to IAM users
2. ✅ Store access keys in environment variables or Kubernetes Secrets
3. ✅ Rotate access keys regularly
4. ✅ Monitor API usage with CloudTrail
5. ✅ Use VPC endpoints for production access

## 📊 Monitoring & Logging

### CloudWatch Metrics
- Request count
- Latency
- Error rate
- Token usage

### Datadog Integration
```go
span.SetTag("llm.provider", "bedrock")
span.SetTag("llm.model", modelId)
span.SetTag("llm.tokens.input", inputTokens)
span.SetTag("llm.tokens.output", outputTokens)
```

## 🎯 Next Steps

1. ✅ Obtain AWS credentials
2. ✅ Configure IAM policy
3. ✅ Request Bedrock model access
4. ✅ Set environment variables
5. ✅ Implement chatbot code
6. ✅ Set up pgvector for RAG
7. ✅ Generate product embeddings
8. ✅ Test and deploy
