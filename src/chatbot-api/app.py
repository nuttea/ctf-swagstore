"""
Swagstore Chatbot API with RAG — Datadog LLM Observability enabled
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector

# Datadog APM & LLM Observability
from ddtrace import tracer, patch_all
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import llm, workflow, task, retrieval

# Apply Flask APM patches
patch_all()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask application
app = Flask(__name__)
CORS(app)

# Environment variables
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'swagstoredb')
LLM_MODEL_ID = os.getenv('LLM_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
EMBEDDING_MODEL_ID = os.getenv('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v2:0')
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))

# Initialize Datadog LLM Observability
LLMObs.enable(
    ml_app="swagstore-chatbot",
    integrations_enabled=True,
    agentless_enabled=False,
    site=os.getenv('DD_SITE', 'datadoghq.com'),
    api_key=os.getenv('DD_API_KEY', ''),
    env=os.getenv('DD_ENV', 'ctf'),
    service=os.getenv('DD_SERVICE', 'chatbot-api')
)

logger.info("🚀 Swagstore Chatbot API starting...")
logger.info(f"📊 Configuration:")
logger.info(f"   AWS Region: {AWS_REGION}")
logger.info(f"   PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
logger.info(f"   LLM Model: {LLM_MODEL_ID}")
logger.info(f"   Embedding Model: {EMBEDDING_MODEL_ID}")
logger.info(f"   RAG Top-K: {RAG_TOP_K}")
logger.info(f"   Datadog LLM Observability: Enabled")

# AWS Bedrock client
bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def get_db_connection():
    """Open and return a PostgreSQL connection with pgvector registered."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )
    register_vector(conn)
    return conn


def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector using Bedrock Titan Embeddings V2.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (1024 dimensions)
    """
    with tracer.trace('bedrock.embedding', service='chatbot-api') as span:
        span.set_tag('embedding.model', EMBEDDING_MODEL_ID)
        span.set_tag('embedding.text_length', len(text))
        
        request_body = {
            'inputText': text,
            'dimensions': 1024,
            'normalize': True
        }
        
        response = bedrock_client.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        result = json.loads(response['body'].read())
        embedding = result['embedding']
        
        span.set_tag('embedding.dimensions', len(embedding))
        logger.info(f"✅ Generated embedding (dim: {len(embedding)})")
        
        return embedding


@retrieval(name="search_similar_products")
def search_similar_products(query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve the most similar products using pgvector cosine similarity (RAG Retrieval).

    Args:
        query_embedding: Embedding vector of the user's question
        top_k: Number of products to retrieve

    Returns:
        List of similar products with similarity scores
    """
    with tracer.trace('postgres.vector_search', service='chatbot-api') as span:
        span.set_tag('vector.top_k', top_k)
        span.set_tag('vector.dimensions', len(query_embedding))
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                product_id,
                product_name,
                description,
                price_usd,
                categories,
                picture,
                1 - (embedding <=> %s::vector) AS similarity
            FROM product_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        cursor.execute(query, (query_embedding, query_embedding, top_k))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        products = [dict(row) for row in results]
        span.set_tag('vector.results_count', len(products))
        
        if products:
            avg_similarity = sum(p['similarity'] for p in products) / len(products)
            span.set_tag('vector.avg_similarity', avg_similarity)
            logger.info(f"🔍 Found {len(products)} products (avg similarity: {avg_similarity:.2%})")
        
        # LLMObs.annotate for retrieval span
        LLMObs.annotate(
            input_data={"query_dimensions": len(query_embedding), "top_k": top_k},
            output_data=[{"product_id": p["product_id"], "product_name": p["product_name"], "similarity": float(p["similarity"])} for p in products],
            metadata={"total_results": len(products), "avg_similarity": avg_similarity if products else 0.0}
        )
        
        return products


@llm(model_name=LLM_MODEL_ID, model_provider="bedrock", name="chat_completion")
def call_claude_with_rag(user_message: str, system_prompt: str, request_body: dict, similar_products: List[Dict[str, Any]]) -> str:
    """
    Call Bedrock Claude 3 to generate a RAG-grounded response.
    Traced by the LLMObs decorator.
    """
    # Record input messages for LLM Observability
    LLMObs.annotate(
        input_data=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        parameters={
            "temperature": 0.7,
            "max_tokens": 1000
        },
        tags={
            "rag_products_count": str(len(similar_products))
        }
    )
    
    logger.info(f"🤖 Calling Bedrock Claude 3...")
    
    response = bedrock_client.invoke_model(
        modelId=LLM_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps(request_body)
    )
    
    result = json.loads(response['body'].read())
    ai_message = result['content'][0]['text']
    
    # Read token usage from the response
    input_tokens = result.get('usage', {}).get('input_tokens', 0)
    output_tokens = result.get('usage', {}).get('output_tokens', 0)
    total_tokens = input_tokens + output_tokens
    
    # Record output and token metrics for LLM Observability
    LLMObs.annotate(
        output_data=[{"role": "assistant", "content": ai_message}],
        metrics={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }
    )
    
    logger.info(f"✅ Generated response (length: {len(ai_message)}, tokens: {total_tokens})")
    
    return ai_message


def generate_chat_response(user_message: str, similar_products: List[Dict[str, Any]]) -> str:
    """
    Generate a RAG-grounded chat response using Claude 3.

    Args:
        user_message: User's question
        similar_products: List of similar products from vector search

    Returns:
        AI response string
    """
    # Build system prompt with grounding instructions
    system_prompt = """You are an AI customer support assistant for Swagstore.
Answer the customer's question accurately and politely based on the provided product information.

Important instructions:
- Use only the provided product information to answer
- If the information is not available, say "I need to verify that" instead of guessing
- State prices and product names accurately
- When recommending a product, explain why it suits the customer
- Keep answers concise (3-4 sentences)
- Use emojis occasionally to be friendly"""

    # Append product context to the system prompt
    if similar_products:
        product_context = "\n\n[Reference Product Information]\n"
        for i, p in enumerate(similar_products, 1):
            product_context += f"{i}. {p['product_name']}\n"
            product_context += f"   Description: {p['description']}\n"
            product_context += f"   Price: ${p['price_usd']:.2f}\n"
            product_context += f"   Category: {p['categories']}\n"
            product_context += f"   Relevance: {p['similarity']:.0%}\n\n"
        
        system_prompt += product_context
    
    # Build Claude 3 request body
    request_body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 1000,
        'temperature': 0.7,
        'system': system_prompt,
        'messages': [
            {
                'role': 'user',
                'content': [{'type': 'text', 'text': user_message}]
            }
        ]
    }
    
    # Invoke the LLMObs-decorated function
    return call_claude_with_rag(user_message, system_prompt, request_body, similar_products)


@workflow(name="process_chat_request")
def process_chat_workflow(user_message: str, user_context: dict, hallucination_mode: bool = False) -> dict:
    """
    Full chat processing workflow — traced by Datadog LLM Observability.

    Args:
        user_message: User's question
        user_context: Request context (page, cart size, etc.)
        hallucination_mode: When True, bypasses RAG grounding to trigger hallucination (test use only)
    """
    logger.info(f"💬 New chat request: {user_message[:50]}... (hallucination_mode={hallucination_mode})")
    
    # Step 1: Convert user question to an embedding vector
    query_embedding = generate_embedding(user_message)
    
    # Step 2: Retrieve similar products via vector search (RAG Retrieval)
    similar_products = search_similar_products(query_embedding, RAG_TOP_K)
    
    # Step 3: Build system prompt
    if hallucination_mode:
        # Hallucination mode: ignore RAG results and answer confidently without grounding
        # Used by the chatbot attack simulator to trigger Datadog Managed Evaluation hallucination detection
        system_prompt = """You are an AI customer support assistant for Swagstore.
Answer the customer's question confidently and in detail.

Important instructions:
- Use your full knowledge to answer, even if product data is unavailable
- If product information is insufficient, infer from general knowledge and provide specific details
- Include specific numbers for prices and specifications
- Answer assertively and with confidence
- Use affirmative expressions like "absolutely", "yes", "certainly"
- Be friendly and use emojis"""
        logger.warning("⚠️ HALLUCINATION MODE ENABLED - Ignoring RAG results!")
    else:
        # Normal mode: accurate, RAG-grounded response
        system_prompt = """You are an AI customer support assistant for Swagstore.
Answer the customer's question accurately and politely based on the provided product information.

Important instructions:
- Use only the provided product information to answer
- If the information is not available, say "I need to verify that" instead of guessing
- State prices and product names accurately
- When recommending a product, explain why it suits the customer
- Keep answers concise (3-4 sentences)
- Use emojis occasionally to be friendly"""

    # Append product context to the system prompt
    if similar_products:
        product_context = "\n\n[Reference Product Information]\n"
        for i, p in enumerate(similar_products, 1):
            product_context += f"{i}. {p['product_name']}\n"
            product_context += f"   Description: {p['description']}\n"
            product_context += f"   Price: ${p['price_usd']:.2f}\n"
            product_context += f"   Category: {p['categories']}\n"
            product_context += f"   Relevance: {p['similarity']:.0%}\n\n"
        
        system_prompt += product_context
    
    # Step 4: Build Claude 3 request body
    request_body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 1000,
        'temperature': 0.7,
        'system': system_prompt,
        'messages': [
            {
                'role': 'user',
                'content': [{'type': 'text', 'text': user_message}]
            }
        ]
    }
    
    # Step 5: Generate AI response via Claude 3 (LLM call)
    ai_response = call_claude_with_rag(user_message, system_prompt, request_body, similar_products)
    
    # Step 6: Build reference documents for hallucination detection
    # Used by Datadog Managed Evaluation to compare the response against known product facts
    reference_documents = []
    if similar_products:
        for p in similar_products:
            # Add each retrieved product as a reference document
            reference_doc = (
                f"Product: {p['product_name']}\n"
                f"Description: {p['description']}\n"
                f"Price: ${p['price_usd']:.2f}\n"
                f"Category: {p['categories']}"
            )
            reference_documents.append(reference_doc)
    
    # Submit reference documents to LLMObs for hallucination detection scoring
    if reference_documents:
        LLMObs.annotate(
            metadata={
                "reference_documents": reference_documents,
                "retrieval_context": [p['product_name'] for p in similar_products]
            }
        )
        logger.info(f"📚 Added {len(reference_documents)} reference documents for hallucination detection")
    
    # Build final response payload
    response_data = {
        'success': True,
        'message': ai_response,
        'products': similar_products,
        'metadata': {
            'model': LLM_MODEL_ID,
            'rag_enabled': True,
            'products_count': len(similar_products),
            'timestamp': datetime.utcnow().isoformat(),
            'reference_documents_count': len(reference_documents),
            'hallucination_mode': hallucination_mode
        }
    }
    
    logger.info(f"✅ Chat response generated successfully")
    
    return response_data


def evaluate_response_inline(user_message: str, ai_response: str, similar_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate chatbot response quality (inline version — no span_id required).

    Evaluation criteria:
    1. Response Quality: response length and completeness
    2. RAG Relevance: average similarity score of retrieved products
    3. Helpfulness: keyword overlap between question and response (heuristic)
    4. Sentiment: tone of the response (positive / negative / neutral)
    5. Failed Answer: response indicates it could not answer
    6. Language Match: question and response language consistency
    7. Hallucination: confident response with low RAG relevance
    """
    return _evaluate_response_logic(user_message, ai_response, similar_products)


def evaluate_response(user_message: str, ai_response: str, similar_products: List[Dict[str, Any]], span_id: str, trace_id: str) -> Dict[str, Any]:
    """Evaluate chatbot response quality and return results for later Datadog submission."""
    evaluations = _evaluate_response_logic(user_message, ai_response, similar_products)
    logger.info(f"📊 Evaluations with span context: span_id={span_id}, trace_id={trace_id}")
    return evaluations


def _evaluate_response_logic(user_message: str, ai_response: str, similar_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Shared evaluation logic for chatbot response quality.

    Evaluation criteria:
    1. Response Quality: response length and completeness
    2. RAG Relevance: average similarity score of retrieved products
    3. Helpfulness: keyword overlap between question and response (heuristic)
    4. Sentiment: tone of the response (positive / negative / neutral)
    5. Failed Answer: response indicates it could not answer
    6. Language Match: question and response language consistency
    7. Hallucination: confident response with low RAG relevance
    """
    evaluations = {}
    
    # Normalize to lowercase for evaluation
    response_lower = ai_response.lower()
    question_lower = user_message.lower()
    
    # 1. Response Quality: score based on response length
    response_length = len(ai_response)
    if response_length < 20:
        quality_score = 0.3
        quality_label = "too_short"
    elif response_length > 500:
        quality_score = 0.7
        quality_label = "too_long"
    else:
        quality_score = 1.0
        quality_label = "good"
    
    evaluations['response_quality'] = {
        'metric_type': 'score',
        'value': quality_score,
        'label': quality_label,
        'score_value': quality_score
    }
    
    # 2. RAG Relevance: average similarity of retrieved products
    if similar_products:
        avg_similarity = sum(p['similarity'] for p in similar_products) / len(similar_products)
        
        if avg_similarity >= 0.7:
            rag_label = "highly_relevant"
            rag_score = 1.0
        elif avg_similarity >= 0.5:
            rag_label = "relevant"
            rag_score = 0.7
        else:
            rag_label = "low_relevance"
            rag_score = 0.4
        
        evaluations['rag_relevance'] = {
            'metric_type': 'score',
            'value': rag_score,
            'label': rag_label,
            'score_value': rag_score
        }
    
    # 3. Helpfulness: keyword overlap between question and response (heuristic)
    question_words = set(user_message.lower().split())
    response_words = set(ai_response.lower().split())
    overlap = len(question_words & response_words)
    overlap_ratio = overlap / max(len(question_words), 1)
    
    if overlap_ratio >= 0.3:
        helpfulness_score = 1.0
        helpfulness_label = "helpful"
    elif overlap_ratio >= 0.15:
        helpfulness_score = 0.7
        helpfulness_label = "partially_helpful"
    else:
        helpfulness_score = 0.5
        helpfulness_label = "unclear"
    
    evaluations['helpfulness'] = {
        'metric_type': 'score',
        'value': helpfulness_score,
        'label': helpfulness_label,
        'score_value': helpfulness_score
    }
    
    # 4. Sentiment: simple keyword-based positive/negative tone detection
    positive_keywords = ['recommend', 'perfect', 'great', 'excellent', 'ideal', 'popular', 'available', '👍', '😊', '🎉', '✨']
    negative_keywords = ['sorry', 'apologize', 'unfortunately', 'cannot', 'unable', 'unavailable', 'error', '😢', '😞']
    
    positive_count = sum(1 for keyword in positive_keywords if keyword in response_lower)
    negative_count = sum(1 for keyword in negative_keywords if keyword in response_lower)
    
    if positive_count > negative_count and positive_count > 0:
        sentiment_label = 'positive'
        sentiment_score = 1.0
    elif negative_count > positive_count and negative_count > 0:
        sentiment_label = 'negative'
        sentiment_score = 0.3
    else:
        sentiment_label = 'neutral'
        sentiment_score = 0.7
    
    evaluations['sentiment'] = {
        'metric_type': 'categorical',
        'value': sentiment_score,
        'label': sentiment_label,
        'score_value': sentiment_score
    }
    
    # 5. Failed Answer: detect phrases indicating the response could not answer
    failed_phrases = [
        'i need to verify',
        'i cannot confirm',
        'not sure',
        'information is not available',
        'cannot answer',
        'unclear',
        'an error occurred'
    ]
    
    is_failed = any(phrase in ai_response for phrase in failed_phrases)
    
    if is_failed:
        failed_label = 'failed'
        failed_score = 0.0
    else:
        failed_label = 'answered'
        failed_score = 1.0
    
    evaluations['failed_answer'] = {
        'metric_type': 'categorical',
        'value': failed_score,
        'label': failed_label,
        'score_value': failed_score
    }
    
    # 6. Language Match: simple Japanese/English language detection to check consistency
    def detect_language(text: str) -> str:
        """Simple language detector (Japanese vs English)."""
        # Ratio of Japanese characters (hiragana, katakana, kanji) in the text
        japanese_chars = sum(1 for char in text if '\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9fff')
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return 'unknown'
        
        japanese_ratio = japanese_chars / total_chars
        
        if japanese_ratio > 0.3:
            return 'japanese'
        else:
            return 'english'
    
    question_lang = detect_language(user_message)
    response_lang = detect_language(ai_response)
    
    if question_lang == response_lang:
        lang_match_label = 'match'
        lang_match_score = 1.0
    else:
        lang_match_label = 'mismatch'
        lang_match_score = 0.0
    
    evaluations['language_match'] = {
        'metric_type': 'categorical',
        'value': lang_match_score,
        'label': lang_match_label,
        'score_value': lang_match_score,
        'metadata': {
            'question_language': question_lang,
            'response_language': response_lang
        }
    }
    
    # 7. Hallucination: flag responses that are confident but have low RAG relevance
    rag_score = evaluations.get('rag_relevance', {}).get('value', 1.0)
    
    # Phrases that indicate high confidence in the response
    confident_phrases = [
        'absolutely', 'definitely', 'certainly', 'of course', 'yes',
        'correct', 'indeed', 'sure', 'exactly'
    ]
    
    # Phrases that indicate appropriate uncertainty (not hallucination)
    uncertain_phrases = [
        'not sure', 'unclear', 'cannot confirm',
        'i need to verify', 'information is not available',
        'cannot answer', 'apologize'
    ]
    
    has_confident_phrase = any(phrase in response_lower for phrase in confident_phrases)
    has_uncertain_phrase = any(phrase in response_lower for phrase in uncertain_phrases)
    
    # Likely hallucination: low RAG relevance (<0.5) but response uses confident language
    if rag_score < 0.5 and has_confident_phrase and not has_uncertain_phrase:
        hallucination_label = 'likely_hallucination'
        hallucination_score = 0.0
    elif rag_score < 0.5 and not has_confident_phrase:
        hallucination_label = 'uncertain_response'
        hallucination_score = 0.5
    else:
        hallucination_label = 'grounded'
        hallucination_score = 1.0
    
    evaluations['hallucination'] = {
        'metric_type': 'categorical',
        'value': hallucination_score,
        'label': hallucination_label,
        'score_value': hallucination_score
    }
    
    logger.info(f"📊 Evaluations: Quality={quality_score}, RAG={evaluations.get('rag_relevance', {}).get('value', 'N/A')}, Helpfulness={helpfulness_score}, Sentiment={sentiment_label}, Failed={failed_label}, LangMatch={lang_match_label}, Hallucination={hallucination_label}")
    
    return evaluations


def submit_evaluations_to_datadog(span_id: str, trace_id: str, evaluations: Dict[str, Any]):
    """
    Submit evaluation results to Datadog LLM Observability via direct REST API call.
    Uses DD_API_KEY for authentication.
    """
    try:
        dd_api_key = os.getenv('DD_API_KEY')
        dd_site = os.getenv('DD_SITE', 'datadoghq.com')
        
        if not dd_api_key:
            logger.warning("⚠️ DD_API_KEY not set, skipping evaluation submission")
            return
        
        # Datadog LLM Observability Evaluation Metrics API
        # https://docs.datadoghq.com/api/latest/llm-observability/#submit-evaluations
        url = f"https://api.{dd_site}/api/v2/llm-obs/v1/eval-metric"
        
        headers = {
            'DD-API-KEY': dd_api_key,
            'Content-Type': 'application/json'
        }
        
        # Batch all evaluations into a single API request
        metrics = []
        for eval_name, eval_data in evaluations.items():
            # categorical metrics use a string label; score metrics use a numeric value
            if eval_data['metric_type'] == 'categorical':
                metric_value = eval_data['label']
            else:
                metric_value = eval_data['score_value']
            
            metrics.append({
                "span_id": span_id,
                "trace_id": trace_id,
                "metric_type": eval_data['metric_type'],
                "label": eval_name,
                "metric_value": metric_value
            })
        
        payload = {
            "data": {
                "type": "evaluation_metric",
                "attributes": {
                    "metrics": metrics,
                    "ml_app": "swagstore-chatbot"
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ Successfully submitted {len(metrics)} evaluations to Datadog")
        else:
            logger.error(f"❌ Failed to submit evaluations: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Error submitting evaluations: {str(e)}", exc_info=True)


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Note: The Kubernetes probe uses tcpSocket so this endpoint is rarely called directly.
    Kept for manual verification purposes.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'chatbot-api',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat API endpoint.

    Request:
        {
            "message": "User's message",
            "context": {
                "page": "/product/123",
                "cartSize": "2"
            },
            "hallucination_mode": false  // Optional: enable hallucination test mode
        }

    Response:
        {
            "success": true,
            "message": "AI response",
            "products": [...],
            "metadata": {...}
        }
    """
    try:
        # Parse request data
        data = request.get_json()
        user_message = data.get('message', '')
        user_context = data.get('context', {})
        hallucination_mode = data.get('hallucination_mode', False)
        
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Message cannot be empty.'
            }), 400
        
        # Run the full chat workflow
        response_data = process_chat_workflow(user_message, user_context, hallucination_mode)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Chat error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'message': 'Sorry, an error occurred. Please try again.',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

