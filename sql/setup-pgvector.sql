-- pgvector拡張を有効化してRAG用のテーブルを作成

-- pgvector拡張をインストール
CREATE EXTENSION IF NOT EXISTS vector;

-- 商品埋め込みテーブルを作成
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    price_usd DECIMAL(10, 2),
    categories TEXT,
    picture VARCHAR(500),
    embedding vector(1024),  -- Titan Embeddings V2 (1024次元)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id)
);

-- ベクトル検索用のインデックスを作成（HNSW - 高速検索）
CREATE INDEX IF NOT EXISTS product_embeddings_vector_idx 
ON product_embeddings USING hnsw (embedding vector_cosine_ops);

-- 商品IDでの検索用インデックス
CREATE INDEX IF NOT EXISTS product_embeddings_product_id_idx 
ON product_embeddings(product_id);

-- 更新日時の自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_product_embeddings_updated_at 
BEFORE UPDATE ON product_embeddings 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

-- 既存の商品データを確認
SELECT 
    COUNT(*) as total_products,
    MIN(price_usd_units + price_usd_nanos/1000000000.0) as min_price,
    MAX(price_usd_units + price_usd_nanos/1000000000.0) as max_price
FROM products;

-- セットアップ完了メッセージ
DO $$
BEGIN
    RAISE NOTICE 'pgvector setup completed successfully!';
    RAISE NOTICE 'Run the Go application to populate product embeddings.';
END $$;






