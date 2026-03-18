# Chatbot Deployment Guide

## 🚀 Automated Setup Overview

The chatbot is automatically set up at deploy time using Kubernetes Jobs.

### Automated Deployment Flow

```
1. PreSync Job (chatbot-pgvector-setup)
   ↓
   Install pgvector extension into PostgreSQL
   ↓
2. Regular application deployment
   ↓
3. PostSync Job (chatbot-embed-products)
   ↓
   Generate embedding vectors for product data
   ↓
4. Chatbot ready!
```

## 📦 Components

### 1. **chatbot-setup-job.yaml**
- ConfigMap: SQL scripts and setup scripts
- Secret: AWS Bedrock credentials
- Job: pgvector setup (PreSync)
- Job: Product embedding generation (PostSync)

### 2. **chatbot-embedder**
- Go CLI tool
- Uses Bedrock Titan Embeddings
- Vectorizes product data and stores it in PostgreSQL

### 3. **Frontend (implemented)**
- Chat widget UI
- Bedrock Claude 3 integration
- RAG retrieval

## 🔧 Deployment Steps

### Prerequisites

1. ✅ Kubernetes cluster is running
2. ✅ PostgreSQL (postgres Pod) is running
3. ✅ AWS Bedrock access granted
4. ✅ Model access approved:
   - Claude 3 Haiku/Sonnet
   - Titan Embeddings V2

### Step 1: Configure AWS credentials

The Secret section in `kubernetes-manifests/chatbot-setup-job.yaml` is already defined:

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

### Step 2: Install pgvector extension into PostgreSQL

Verify pgvector is available in the PostgreSQL pod:

```bash
# Exec into the PostgreSQL pod
kubectl exec -it deployment/postgres -- bash

# Check if pgvector can be installed
psql -U postgres -d swagstoredb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Note**: If pgvector is not available, update the PostgreSQL image to `pgvector/pgvector:pg15`.

### Step 3: Build the embedder image

```bash
# From project root
cd src/chatbot-embedder

# Local build
docker build -t chatbot-embedder:latest .

# Or via Skaffold
cd ../..
skaffold build
```

### Step 4: Deploy chatbot Jobs

```bash
# Deploy ConfigMap, Secret, and Jobs
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

### Step 5: Check execution status

```bash
# Check pgvector setup Job
kubectl get job chatbot-pgvector-setup
kubectl logs job/chatbot-pgvector-setup

# Check product embedding generation Job
kubectl get job chatbot-embed-products
kubectl logs job/chatbot-embed-products -f

# Expected output:
# 🚀 Starting product embeddings generation...
# ✅ Bedrock client initialized
# ✅ Connected to PostgreSQL
# 📦 Found 9 products to process
# [1/9] Processing: Vintage Typewriter
#    ✅ Embedded successfully (vector dim: 1024)
# ...
# 🎉 Embedding generation completed!
```

### Step 6: Verify embedding data

```bash
kubectl exec -it deployment/postgres -- psql -U postgres -d swagstoredb

# Inside PostgreSQL
SELECT 
    product_id, 
    product_name, 
    price_usd,
    array_length(embedding, 1) as vector_dim,
    created_at
FROM product_embeddings
ORDER BY created_at DESC;
```

Expected output:
```
 product_id | product_name        | price_usd | vector_dim | created_at
------------+---------------------+-----------+------------+----------------------------
 001        | Vintage Typewriter  | 67.99     | 1024       | 2024-01-15 10:30:15.123456
 ...
```

## 🔄 Redeployment Behaviour

### Normal application redeploy
```bash
skaffold run
```
- pgvector setup Job (PreSync) will re-run
- Product embedding generation Job (PostSync) will re-run
- Existing embeddings are updated (UPSERT)

### Manually regenerate embeddings
```bash
# Delete the Job
kubectl delete job chatbot-embed-products

# Recreate it
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 🐛 Troubleshooting

### Error: "extension \"vector\" does not exist"

**Cause**: pgvector is not installed in PostgreSQL.

**Fix**:
```yaml
# Update kubernetes-manifests/postgres.yaml
spec:
  containers:
  - name: postgres
    image: pgvector/pgvector:pg15  # ← change to this
```

### Error: "AccessDeniedException"

**Cause**: Insufficient IAM permissions or model access not approved in AWS Bedrock.

**Fix**:
1. AWS Console → Bedrock → Model access
2. Request access for Claude 3 and Titan Embeddings
3. Review IAM policy

### Error: Job stuck in Pending

**Cause**: PostgreSQL is not running.

**Fix**:
```bash
# Check PostgreSQL pod status
kubectl get pods -l app=postgres

# Start PostgreSQL
kubectl apply -f kubernetes-manifests/postgres.yaml
```

### Error: "connection refused"

**Cause**: Incorrect PostgreSQL service name.

**Fix**:
```bash
# Check service name
kubectl get svc | grep postgres

# Update environment variable to match the service name
POSTGRES_HOST=postgres
```

## 📊 Monitoring

### Datadog Integration

```go
// Chatbot embedding metrics
span.SetTag("chatbot.embeddings.generated", count)
span.SetTag("chatbot.embeddings.dimensions", 1024)
span.SetTag("chatbot.provider", "bedrock")
span.SetTag("chatbot.model", "titan-embed-text-v2")
```

### CloudWatch Integration

Monitor Bedrock usage in AWS CloudWatch:
- Request count
- Latency
- Error rate
- Token usage

## 💰 Cost Estimate

### Titan Embeddings V2 Pricing
- $0.0001 / 1,000 tokens

### Embedding generation cost for 100 products
- Average 50 tokens/product × 100 products = 5,000 tokens
- Cost: ~$0.0005

### Monthly cost (if redeployed daily)
- $0.0005 × 30 days = $0.015/month

## 🎯 Next Steps

1. ✅ pgvector setup — done
2. ✅ Product embedding generation — done
3. ✅ Frontend UI implementation — done
4. ✅ Chat API endpoint implementation — done
5. ✅ RAG retrieval logic implementation — done

## 📝 Cleanup

### Delete Jobs
```bash
kubectl delete job chatbot-pgvector-setup chatbot-embed-products
```

### Drop embedding data
```bash
kubectl exec -it deployment/postgres -- psql -U postgres -d swagstoredb

# Inside PostgreSQL
DROP TABLE IF EXISTS product_embeddings;
```

### Delete Secret
```bash
kubectl delete secret aws-bedrock-credentials
```

## 🔐 Security Best Practices

1. ✅ Store AWS credentials as Kubernetes Secrets
2. ⚠️ Never hardcode credentials in production
3. ✅ Use IAM roles (recommended for EKS environments)
4. ✅ Apply least-privilege principle
5. ✅ Rotate access keys regularly

## 📚 References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Titan Embeddings V2](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Claude 3 Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html)
