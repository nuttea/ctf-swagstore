-- Enable pgvector extension and create tables for RAG retrieval

-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create product embeddings table
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    price_usd DECIMAL(10, 2),
    categories TEXT,
    picture VARCHAR(500),
    embedding vector(1024),  -- Titan Embeddings V2 (1024 dimensions)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id)
);

-- HNSW index for fast cosine-similarity vector search
CREATE INDEX IF NOT EXISTS product_embeddings_vector_idx 
ON product_embeddings USING hnsw (embedding vector_cosine_ops);

-- B-tree index for product_id lookups
CREATE INDEX IF NOT EXISTS product_embeddings_product_id_idx 
ON product_embeddings(product_id);

-- Trigger to auto-update updated_at on row changes
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

-- Verify existing product data
SELECT 
    COUNT(*) as total_products,
    MIN(price_usd_units + price_usd_nanos/1000000000.0) as min_price,
    MAX(price_usd_units + price_usd_nanos/1000000000.0) as max_price
FROM products;

-- Setup complete
DO $$
BEGIN
    RAISE NOTICE 'pgvector setup completed successfully!';
    RAISE NOTICE 'Run the Go application to populate product embeddings.';
END $$;
