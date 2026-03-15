"""
Swagstore Chatbot API with RAG
Datadog LLM Observability対応
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

# Flask APMパッチを適用
patch_all()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask アプリケーション
app = Flask(__name__)
CORS(app)

# 環境変数
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

# Datadog LLM Observability初期化
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

# AWS Bedrock クライアント
bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def get_db_connection():
    """PostgreSQL接続を取得"""
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
    Titan Embeddings V2で埋め込みベクトルを生成
    
    Args:
        text: 埋め込み対象のテキスト
        
    Returns:
        埋め込みベクトル（1024次元）
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
    ベクトル類似度検索で関連商品を取得（RAG Retrieval）
    
    Args:
        query_embedding: 質問の埋め込みベクトル
        top_k: 取得する商品数
        
    Returns:
        類似商品のリスト
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
    Bedrock Claude 3を呼び出してRAG応答を生成
    LLMObsデコレーターでトレース
    """
    # 入力データを記録
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
    
    # トークン数を取得
    input_tokens = result.get('usage', {}).get('input_tokens', 0)
    output_tokens = result.get('usage', {}).get('output_tokens', 0)
    total_tokens = input_tokens + output_tokens
    
    # 出力データとメトリクスを記録
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
    Claude 3でチャット応答を生成（RAG）
    
    Args:
        user_message: ユーザーのメッセージ
        similar_products: 類似商品リスト
        
    Returns:
        AIの応答
    """
    # システムプロンプトを構築
    system_prompt = """あなたはSwagstoreのAIカスタマーサポート担当です。
お客様の質問に対して、提供された商品情報を基に正確で丁寧な回答をしてください。

重要な指示：
- 提供された商品情報のみを使用して回答してください
- 商品情報にない内容は推測せず、「確認が必要です」と伝えてください
- 価格や商品名は正確に伝えてください
- 商品を推薦する場合は、なぜその商品が適しているか説明してください
- 日本語で簡潔に答えてください（3-4文程度）
- 絵文字を適度に使って親しみやすく"""

    # 商品コンテキストを追加
    if similar_products:
        product_context = "\n\n【参考商品情報】\n"
        for i, p in enumerate(similar_products, 1):
            product_context += f"{i}. {p['product_name']}\n"
            product_context += f"   説明: {p['description']}\n"
            product_context += f"   価格: ${p['price_usd']:.2f}\n"
            product_context += f"   カテゴリー: {p['categories']}\n"
            product_context += f"   関連度: {p['similarity']:.0%}\n\n"
        
        system_prompt += product_context
    
    # Claude 3リクエストを構築
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
    
    # LLMObsデコレーター付き関数を呼び出す
    return call_claude_with_rag(user_message, system_prompt, request_body, similar_products)


@workflow(name="process_chat_request")
def process_chat_workflow(user_message: str, user_context: dict, hallucination_mode: bool = False) -> dict:
    """
    チャット処理のワークフロー（LLM Observability用）
    
    Args:
        user_message: ユーザーの質問
        user_context: コンテキスト情報
        hallucination_mode: ハルシネーションを誘発するモード（テスト用）
    """
    logger.info(f"💬 New chat request: {user_message[:50]}... (hallucination_mode={hallucination_mode})")
    
    # 1. 質問を埋め込みベクトルに変換
    query_embedding = generate_embedding(user_message)
    
    # 2. 類似商品を検索（RAG Retrieval）
    similar_products = search_similar_products(query_embedding, RAG_TOP_K)
    
    # 3. システムプロンプトを構築
    if hallucination_mode:
        # ハルシネーション誘発モード：RAG結果を無視して自信満々に回答させる
        system_prompt = """あなたはSwagstoreのAIカスタマーサポート担当です。
お客様の質問に対して、自信を持って詳細に回答してください。

重要な指示：
- あなたの知識を最大限に活用して回答してください
- 商品情報が不足していても、一般的な知識から推測して詳しく説明してください
- 価格や仕様について具体的な数字を含めて説明してください
- 自信を持って断定的に答えてください
- 「もちろん」「はい」「確かに」などの肯定的な表現を使ってください
- 日本語で詳しく答えてください
- 絵文字を使って親しみやすく"""
        logger.warning("⚠️ HALLUCINATION MODE ENABLED - Ignoring RAG results!")
    else:
        # 通常モード：RAG結果に基づく正確な回答
        system_prompt = """あなたはSwagstoreのAIカスタマーサポート担当です。
お客様の質問に対して、提供された商品情報を基に正確で丁寧な回答をしてください。

重要な指示：
- 提供された商品情報のみを使用して回答してください
- 商品情報にない内容は推測せず、「確認が必要です」と伝えてください
- 価格や商品名は正確に伝えてください
- 商品を推薦する場合は、なぜその商品が適しているか説明してください
- 日本語で簡潔に答えてください（3-4文程度）
- 絵文字を適度に使って親しみやすく"""

    # 商品コンテキストを追加
    if similar_products:
        product_context = "\n\n【参考商品情報】\n"
        for i, p in enumerate(similar_products, 1):
            product_context += f"{i}. {p['product_name']}\n"
            product_context += f"   説明: {p['description']}\n"
            product_context += f"   価格: ${p['price_usd']:.2f}\n"
            product_context += f"   カテゴリー: {p['categories']}\n"
            product_context += f"   関連度: {p['similarity']:.0%}\n\n"
        
        system_prompt += product_context
    
    # 4. Claude 3リクエストを構築
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
    
    # 5. Claude 3で応答を生成（LLM呼び出し）
    ai_response = call_claude_with_rag(user_message, system_prompt, request_body, similar_products)
    
    # 6. ハルシネーション検出のためのリファレンスドキュメントを構築
    # Datadog Managed Evaluationのハルシネーション検出に使用される
    reference_documents = []
    if similar_products:
        for p in similar_products:
            # 各商品をリファレンスドキュメントとして追加
            reference_doc = (
                f"商品名: {p['product_name']}\n"
                f"説明: {p['description']}\n"
                f"価格: ${p['price_usd']:.2f}\n"
                f"カテゴリー: {p['categories']}"
            )
            reference_documents.append(reference_doc)
    
    # LLMObsにリファレンスドキュメントを記録（ハルシネーション検出用）
    if reference_documents:
        LLMObs.annotate(
            metadata={
                "reference_documents": reference_documents,
                "retrieval_context": [p['product_name'] for p in similar_products]
            }
        )
        logger.info(f"📚 Added {len(reference_documents)} reference documents for hallucination detection")
    
    # レスポンス
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
    チャットボット応答の品質を評価（インライン版 - span_id不要）
    
    評価基準:
    1. Response Quality: 応答の長さと完全性
    2. RAG Relevance: 検索された商品の関連度
    3. Helpfulness: 応答が質問に答えているか（ヒューリスティック）
    4. Sentiment: 応答のトーン（ポジティブ/ネガティブ/ニュートラル）
    5. Failed Answer: 応答が質問に答えられていないケース
    6. Language Mismatch: 質問と応答の言語不一致
    7. Hallucination: 幻覚検出
    """
    return _evaluate_response_logic(user_message, ai_response, similar_products)


def evaluate_response(user_message: str, ai_response: str, similar_products: List[Dict[str, Any]], span_id: str, trace_id: str) -> Dict[str, Any]:
    """
    チャットボット応答の品質を評価（後でDatadogに送信する用）
    """
    evaluations = _evaluate_response_logic(user_message, ai_response, similar_products)
    logger.info(f"📊 Evaluations with span context: span_id={span_id}, trace_id={trace_id}")
    return evaluations


def _evaluate_response_logic(user_message: str, ai_response: str, similar_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    チャットボット応答の品質を評価（共通ロジック）
    
    評価基準:
    1. Response Quality: 応答の長さと完全性
    2. RAG Relevance: 検索された商品の関連度
    3. Helpfulness: 応答が質問に答えているか（ヒューリスティック）
    4. Sentiment: 応答のトーン（ポジティブ/ネガティブ/ニュートラル）
    5. Failed Answer: 応答が質問に答えられていないケース
    6. Language Mismatch: 質問と応答の言語不一致
    7. Hallucination: 幻覚検出
    """
    evaluations = {}
    
    # 応答を小文字に変換（評価用）
    response_lower = ai_response.lower()
    question_lower = user_message.lower()
    
    # 1. Response Quality評価（応答の長さと構造）
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
    
    # 2. RAG Relevance評価（商品の平均類似度）
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
    
    # 3. Helpfulness評価（簡易的なキーワードマッチング）
    # 質問に関連するキーワードが応答に含まれているか
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
    
    # 4. Sentiment評価（応答のトーン）
    # ポジティブ・ネガティブキーワードベースの簡易的な感情分析
    positive_keywords = ['おすすめ', 'おすすめします', 'ぴったり', '最適', '良い', 'いい', '素敵', '人気', 'お得', '👍', '😊', '🎉', '✨']
    negative_keywords = ['申し訳', 'すみません', '残念', 'ごめん', '確認が必要', 'わかりません', '不明', 'エラー', '😢', '😞']
    
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
    
    # 5. Failed Answer評価（応答が質問に答えられていない）
    # 失敗を示すフレーズの検出
    failed_phrases = [
        '申し訳ございません',
        'わかりません',
        '確認が必要です',
        '情報がありません',
        'お答えできません',
        '不明です',
        'エラーが発生'
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
    
    # 6. Language Mismatch評価（質問と応答の言語不一致）
    # 簡易的な言語検出（日本語・英語のみ）
    def detect_language(text: str) -> str:
        """簡易的な言語検出"""
        # 日本語文字（ひらがな、カタカナ、漢字）の割合
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
    
    # 7. Hallucination評価（幻覚検出）
    # RAG関連度が低いのに自信満々な応答をしている場合
    rag_score = evaluations.get('rag_relevance', {}).get('value', 1.0)
    
    # ハルシネーションの兆候を示すフレーズ
    confident_phrases = [
        'もちろん', 'はい', '確かに', 'その通り', '間違いなく',
        'absolutely', 'definitely', 'certainly', 'of course', 'yes'
    ]
    
    # 不確実性を示すフレーズ（ハルシネーションではない）
    uncertain_phrases = [
        '確認が必要', 'わかりません', '情報がありません', 
        'お答えできません', '申し訳ございません',
        'not sure', 'unclear', 'cannot confirm'
    ]
    
    has_confident_phrase = any(phrase in response_lower for phrase in confident_phrases)
    has_uncertain_phrase = any(phrase in response_lower for phrase in uncertain_phrases)
    
    # ハルシネーションの可能性：RAG関連度が低い（<0.5）のに自信満々（confident phrases使用）
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
    評価結果をDatadog LLM ObservabilityにSubmit（REST API直接呼び出し）
    DD_API_KEYを使用してDatadog APIに送信
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
        
        # 全評価を1つのリクエストにまとめる
        metrics = []
        for eval_name, eval_data in evaluations.items():
            # metric_typeに応じてvalueを設定
            if eval_data['metric_type'] == 'categorical':
                metric_value = eval_data['label']  # categorical: 文字列
            else:
                metric_value = eval_data['score_value']  # score: 数値
            
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
    ヘルスチェックエンドポイント
    
    注意: KubernetesのProbeはtcpSocketを使用しているため、
    このエンドポイントは通常呼び出されません。
    手動確認用に残しています。
    """
    return jsonify({
        'status': 'healthy',
        'service': 'chatbot-api',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    チャットAPIエンドポイント
    
    Request:
        {
            "message": "ユーザーのメッセージ",
            "context": {
                "page": "/product/123",
                "cartSize": "2"
            },
            "hallucination_mode": false  // オプション：ハルシネーション誘発モード
        }
    
    Response:
        {
            "success": true,
            "message": "AIの応答",
            "products": [...],
            "metadata": {...}
        }
    """
    try:
        # リクエストデータを取得
        data = request.get_json()
        user_message = data.get('message', '')
        user_context = data.get('context', {})
        hallucination_mode = data.get('hallucination_mode', False)
        
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'メッセージが空です'
            }), 400
        
        # ワークフローを実行
        response_data = process_chat_workflow(user_message, user_context, hallucination_mode)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Chat error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'message': '申し訳ございません。エラーが発生しました。',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

