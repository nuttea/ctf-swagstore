# Swagstore Chatbot - Datadog LLM Observability

## Overview

The Swagstore chatbot is a RAG-enabled AI assistant powered by AWS Bedrock (Claude 3 + Titan Embeddings).
It runs as a separate Python API pod and is fully monitored by **Datadog LLM Observability**.

## Architecture

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
│  - Traces                                    │
│  - Metrics                                   │
│  - Full visibility into LLM calls            │
└──────────────────────────────────────────────┘
```

## Components

### 1. Chatbot API (Python)
- **File**: `src/chatbot-api/app.py`
- **Framework**: Flask + Gunicorn
- **Features**:
  - RAG retrieval (PostgreSQL pgvector)
  - Response generation via AWS Bedrock Claude 3
  - Datadog APM & LLM Observability integration

### 2. Frontend Proxy (Go)
- **File**: `src/frontend/main.go`
- **Endpoint**: `/api/chatbot/chat`
- **Role**: Proxy to Chatbot API

### 3. Chat Widget (HTML/JS)
- **File**: `src/frontend/templates/chatbot.html`
- **Features**:
  - Modern chat UI
  - Datadog RUM integration
  - Product card display

## Datadog LLM Observability Features

### Trace Information

#### 1. LLM Call Trace
```python
with LLMObs.llm(
    model_name="anthropic.claude-3-haiku-20240307-v1:0",
    model_provider="bedrock",
    name="chat_completion",
    ml_app="swagstore-chatbot"
) as llm_span:
    # Record input data
    llm_span.annotate(
        input_data=[{"role": "user", "content": user_message}],
        parameters={
            "temperature": 0.7,
            "max_tokens": 1000,
            "rag_products_count": len(similar_products)
        }
    )
    
    # Call Bedrock API
    response = bedrock_client.invoke_model(...)
    
    # Record output data and metrics
    llm_span.annotate(
        output_data=[{"role": "assistant", "content": ai_message}],
        metrics={
            "input_tokens": 150,
            "output_tokens": 200,
            "total_tokens": 350
        }
    )
```

#### 2. RAG Retrieval Trace
```python
with tracer.trace('postgres.vector_search', service='chatbot-api') as span:
    span.set_tag('vector.top_k', 5)
    span.set_tag('vector.dimensions', 1024)
    span.set_tag('vector.results_count', len(products))
    span.set_tag('vector.avg_similarity', avg_similarity)
```

#### 3. Embedding Generation Trace
```python
with tracer.trace('bedrock.embedding', service='chatbot-api') as span:
    span.set_tag('embedding.model', 'amazon.titan-embed-text-v2:0')
    span.set_tag('embedding.text_length', len(text))
    span.set_tag('embedding.dimensions', 1024)
```

### Collected Metrics

| Metric | Description |
|--------|-------------|
| `input_tokens` | Number of tokens sent to the LLM |
| `output_tokens` | Number of tokens returned by the LLM |
| `total_tokens` | Total token count (used for cost estimation) |
| `vector.avg_similarity` | Average similarity score from RAG retrieval |
| `vector.results_count` | Number of products retrieved |

### Tags

| Tag | Description |
|-----|-------------|
| `model_name` | LLM model used |
| `model_provider` | Provider (bedrock) |
| `rag.enabled` | Whether RAG is active |
| `rag.top_k` | RAG top-K setting |
| `embedding.model` | Embedding model |
| `user.username` | Username (optional) |

## Deployment

### 1. Build & Deploy
```bash
# Auto-deploy with Skaffold
skaffold dev
```

### 2. Build individually (if needed)
```bash
# Build Chatbot API image
cd src/chatbot-api
docker buildx build --platform linux/amd64 \
  -t docker.io/koheisato353/chatbot-api:v1 --push .
```

### 3. Apply Kubernetes manifest
```bash
kubectl apply -f kubernetes-manifests/chatbot-api.yaml
```

## Environment Variables

### Chatbot API Pod

#### AWS Bedrock Configuration
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

#### PostgreSQL Configuration
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

#### LLM Configuration
```yaml
- name: LLM_MODEL_ID
  value: "anthropic.claude-3-haiku-20240307-v1:0"
- name: EMBEDDING_MODEL_ID
  value: "amazon.titan-embed-text-v2:0"
- name: RAG_TOP_K
  value: "5"
```

#### Datadog Configuration
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

## Usage

### 1. Open the chat widget
Click the chat icon at the bottom-right corner of the page.

### 2. Ask about products
Examples:
- "I'm looking for a laptop bag"
- "Do you have any waterproof products?"
- "Show me items under $50"

### 3. AI responds
- RAG retrieves relevant products
- Claude 3 generates a natural language response
- Results are displayed as product cards

## Verifying in Datadog

### 1. LLM Observability
```
Datadog → LLM Observability → swagstore-chatbot
```

### 2. What you can see
- **Traces**: Full detail of every LLM call
- **Input/Output**: Questions and answers
- **Token counts**: Detailed metrics for cost estimation
- **Latency**: Response times
- **Error rate**: Failed calls
- **RAG metrics**: Retrieval accuracy and performance

### 3. APM Traces
```
Datadog → APM → Services → chatbot-api
```

### 4. Custom Dashboard
```
Datadog → Dashboards → Create New Dashboard
```

Recommended metrics:
- `trace.llm.request.duration`
- `trace.llm.request.input_tokens`
- `trace.llm.request.output_tokens`
- `trace.llm.request.error_rate`
- `trace.bedrock.embedding.duration`
- `trace.postgres.vector_search.duration`

## Troubleshooting

### 1. Chatbot not responding
```bash
# Check Chatbot API pod logs
kubectl logs -l app=chatbot-api

# Check Frontend pod logs
kubectl logs -l app=frontend | grep chatbot
```

### 2. No data in Datadog LLM Observability
```bash
# Verify DD_LLMOBS_ENABLED is set
kubectl get pod -l app=chatbot-api -o yaml | grep DD_LLMOBS_ENABLED

# Verify connectivity to Datadog Agent
kubectl exec -it <chatbot-api-pod> -- curl http://$DD_AGENT_HOST:8126/info
```

### 3. RAG retrieval not working
```bash
# Check the product embeddings table in PostgreSQL
kubectl exec deployment/postgres -- \
  env PGPASSWORD=password psql -U postgres -d swagstoredb \
  -c "SELECT COUNT(*) FROM product_embeddings;"

# Expect 9 rows (one per product)
```

### 4. AWS Bedrock errors
```bash
# Verify AWS credentials secret
kubectl get secret aws-bedrock-credentials -o yaml

# Verify Claude 3 model access in AWS Console
```

## Performance Tuning

### 1. Optimize RAG retrieval
```python
# Adjust Top-K (default: 5)
RAG_TOP_K=3  # Faster but lower accuracy
RAG_TOP_K=10 # More accurate but slower
```

### 2. Tune LLM parameters
```python
# temperature: 0.0-1.0 (lower = more deterministic)
'temperature': 0.7

# max_tokens: maximum output token count
'max_tokens': 1000
```

### 3. Scale replicas
```yaml
# kubernetes-manifests/chatbot-api.yaml
spec:
  replicas: 2  # Increase or decrease based on load
```

## Cost Management

### AWS Bedrock Costs
- **Claude 3 Haiku**: $0.00025/1K input tokens, $0.00125/1K output tokens
- **Titan Embeddings V2**: $0.00002/1K tokens

### Cost Reduction Tips
1. Limit `max_tokens`
2. Leverage caching (planned for future)
3. Monitor token usage in Datadog LLM Observability

## Security

### 1. Protecting AWS Credentials
```bash
# Store as a Kubernetes Secret
kubectl create secret generic aws-bedrock-credentials \
  --from-literal=AWS_REGION=ap-northeast-1 \
  --from-literal=AWS_ACCESS_KEY_ID=AKIA... \
  --from-literal=AWS_SECRET_ACCESS_KEY=...
```

### 2. Prompt Injection Mitigation
- Clearly define instructions in the system prompt
- Restrict the model to use only provided product information
- Sanitize user input

### 3. Rate Limiting
```yaml
# Control requests per pod via resource limits
resources:
  limits:
    cpu: "500m"
    memory: "1Gi"
```

## Planned Improvements

- [ ] Caching (reuse answers for identical questions)
- [ ] Streaming responses
- [ ] Multi-language support
- [ ] Conversation history persistence
- [ ] Direct add-to-cart integration
- [ ] A/B testing (different LLM models)

## References

- [Datadog LLM Observability Documentation](https://docs.datadoghq.com/llm_observability/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
