# 🤖 Chatbot Auto-Deployment Configuration

The RAG foundation is set up automatically when PostgreSQL is deployed.

## 🚀 Automated Execution Flow

```
1. skaffold run
   ↓
2. PostgreSQL Pod starts
   ├─ Uses pgvector/pgvector:pg15 image
   ├─ init-db.sh runs automatically
   │  ├─ Create swagstoredb
   │  ├─ Install pgvector extension  ← automatic!
   │  ├─ Create product_embeddings table  ← automatic!
   │  └─ Create HNSW index  ← automatic!
   └─ PostgreSQL Ready
   ↓
3. chatbot-embed-products Job runs (PostSync)
   ├─ Wait for PostgreSQL to be ready
   ├─ Vectorise products using AWS Bedrock Titan Embeddings
   └─ Save results to product_embeddings table
   ↓
4. RAG foundation ready! 🎉
```

## 📦 Components

### 1. PostgreSQL startup (automatic)
**File**: `kubernetes-manifests/postgres.yaml`

```yaml
configMap:
  data:
    init-db.sh: |
      # ... existing DB init ...
      
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

### 2. Product embedding generation (automatic)
**File**: `kubernetes-manifests/chatbot-setup-job.yaml`

- **Secret**: AWS Bedrock credentials
- **Job**: chatbot-embed-products (PostSync hook)
- **Image**: koheisato353/chatbot-embedder:v1

## 🎯 Deployment

### Normal deployment (fully automatic)

```bash
# This single command handles everything
skaffold run
```

**What happens**:
1. ✅ PostgreSQL starts → pgvector set up automatically
2. ✅ chatbot-embedder Job runs → product embeddings generated
3. ✅ RAG foundation ready

### Re-run individual steps

#### Re-initialise PostgreSQL
```bash
# Delete and recreate PVC
kubectl scale deployment postgres --replicas=0
kubectl delete pvc postgres-pvc
kubectl apply -f kubernetes-manifests/postgres.yaml
kubectl scale deployment postgres --replicas=1
```

#### Regenerate product embeddings only
```bash
# Delete and re-run the Job
kubectl delete job chatbot-embed-products
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 📊 Verification

### Check PostgreSQL startup logs
```bash
kubectl logs deployment/postgres -c init-db

# Expected output:
# ✅ pgvector setup completed
# CREATE EXTENSION
# CREATE TABLE
# CREATE INDEX
```

### Check product embedding Job
```bash
kubectl logs job/chatbot-embed-products

# Expected output:
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

### Verify data
```bash
kubectl exec deployment/postgres -- env PGPASSWORD=password psql -U postgres -d swagstoredb -c \
  "SELECT product_id, product_name, price_usd FROM product_embeddings ORDER BY product_id;"
```

## 🔧 Configuration

### Change AWS credentials
Edit `kubernetes-manifests/chatbot-setup-job.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-bedrock-credentials
type: Opaque
stringData:
  AWS_REGION: "ap-northeast-1"          # ← region
  AWS_ACCESS_KEY_ID: "your-access-key"  # ← access key
  AWS_SECRET_ACCESS_KEY: "your-secret"  # ← secret key
```

### Change embedding model
Edit the Job environment variables in `kubernetes-manifests/chatbot-setup-job.yaml`:

```yaml
env:
- name: BEDROCK_EMBEDDING_MODEL
  value: "amazon.titan-embed-text-v2:0"  # ← model ID
- name: EMBEDDING_DIMENSIONS
  value: "1024"  # ← dimensions (256, 512, 1024, 1536)
```

## 🐛 Troubleshooting

### pgvector extension not installed

**Cause**: PostgreSQL image is not `pgvector/pgvector:pg15`.

**Check**:
```bash
kubectl get pod -l app=postgres -o jsonpath='{.items[0].spec.containers[0].image}'
```

**Fix**:
```bash
# Verify the image in postgres.yaml
grep "image:" kubernetes-manifests/postgres.yaml
# Both entries should be pgvector/pgvector:pg15
```

### Product embedding Job fails

**Cause 1**: PostgreSQL is not yet ready.
```bash
kubectl logs job/chatbot-embed-products
# The Job will retry automatically (backoffLimit: 2)
```

**Cause 2**: Invalid AWS credentials.
```bash
kubectl logs job/chatbot-embed-products | grep -i error
# Fix: update the Secret in chatbot-setup-job.yaml
```

### Existing data

The `product_embeddings` table uses `CREATE TABLE IF NOT EXISTS`, so existing data is preserved.

To regenerate from scratch:
```bash
kubectl exec deployment/postgres -- env PGPASSWORD=password psql -U postgres -d swagstoredb -c \
  "TRUNCATE TABLE product_embeddings;"
  
kubectl delete job chatbot-embed-products
kubectl apply -f kubernetes-manifests/chatbot-setup-job.yaml
```

## 💰 Cost

### Initial deployment (9 products)
- Embedding generation: ~$0.0005

### Daily redeployment
- Monthly: ~$0.015

## 🎯 Benefits

✅ **Fully automated**: `skaffold run` handles everything
✅ **Idempotent**: safe to run multiple times
✅ **Fault-tolerant**: auto-recovers after PostgreSQL restart
✅ **Zero maintenance**: no manual steps required
✅ **CI/CD compatible**: can be integrated into pipelines

## 📝 File Structure

```
kubernetes-manifests/
├── postgres.yaml                    # ← includes pgvector auto-setup
└── chatbot-setup-job.yaml          # ← product embedding auto-generation Job

src/
└── chatbot-embedder/               # ← embedding generation tool
    ├── main.go
    ├── Dockerfile
    └── go.mod

skaffold.yaml                       # ← auto-deployment configuration
```

## 🔗 Related Documentation

- [bedrock-setup-guide.md](./bedrock-setup-guide.md) — AWS Bedrock setup
- [chatbot-deployment-guide.md](./chatbot-deployment-guide.md) — Manual deployment steps
- [chatbot-llm-observability.md](./chatbot-llm-observability.md) — LLM Observability

## ✨ Summary

When PostgreSQL is deployed, the following happen automatically:
1. ✅ pgvector extension is installed
2. ✅ product_embeddings table is created
3. ✅ Product embedding vectors are generated

**Result**: RAG foundation is fully ready after a single `skaffold run`! 🎉
