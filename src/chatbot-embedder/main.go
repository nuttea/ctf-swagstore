package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	_ "github.com/lib/pq"
	"github.com/pgvector/pgvector-go"
)

// Product holds metadata for a single catalog item
type Product struct {
	ID          string
	Name        string
	Description string
	PriceUSD    float64
	Categories  string
	Picture     string
}

func main() {
	log.Println("🚀 Starting product embeddings generation...")

	ctx := context.Background()

	// Load configuration from environment variables
	postgresHost := getEnv("POSTGRES_HOST", "postgres")
	postgresPort := getEnv("POSTGRES_PORT", "5432")
	postgresUser := getEnv("POSTGRES_USER", "postgres")
	postgresPassword := getEnv("POSTGRES_PASSWORD", "password")
	postgresDB := getEnv("POSTGRES_DB", "swagstoredb")
	awsRegion := getEnv("AWS_REGION", "ap-northeast-1")
	embeddingModel := getEnv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
	embeddingDimensions := getEnv("EMBEDDING_DIMENSIONS", "1024")

	log.Printf("📊 Configuration:")
	log.Printf("   PostgreSQL: %s:%s/%s", postgresHost, postgresPort, postgresDB)
	log.Printf("   AWS Region: %s", awsRegion)
	log.Printf("   Embedding Model: %s", embeddingModel)
	log.Printf("   Dimensions: %s", embeddingDimensions)

	// Initialize AWS Bedrock client
	bedrockClient, err := initBedrock(ctx, awsRegion)
	if err != nil {
		log.Fatalf("❌ Failed to initialize Bedrock: %v", err)
	}
	log.Println("✅ Bedrock client initialized")

	// Connect to PostgreSQL
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		postgresHost, postgresPort, postgresUser, postgresPassword, postgresDB)
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		log.Fatalf("❌ Failed to connect to database: %v", err)
	}
	defer db.Close()

	// Verify database connection
	if err := db.Ping(); err != nil {
		log.Fatalf("❌ Failed to ping database: %v", err)
	}
	log.Println("✅ Connected to PostgreSQL")

	// Fetch all products from the database
	products, err := fetchProducts(db)
	if err != nil {
		log.Fatalf("❌ Failed to fetch products: %v", err)
	}
	log.Printf("📦 Found %d products to process", len(products))

	// Generate and store embedding vectors for each product
	successCount := 0
	errorCount := 0

	for i, product := range products {
		log.Printf("[%d/%d] Processing: %s", i+1, len(products), product.Name)

		// Build text representation for embedding (name + description + categories + price)
		text := fmt.Sprintf("%s. %s. Category: %s. Price: $%.2f",
			product.Name, product.Description, product.Categories, product.PriceUSD)

		// Generate embedding vector via Bedrock Titan
		embedding, err := generateEmbedding(ctx, bedrockClient, text, embeddingModel, embeddingDimensions)
		if err != nil {
			log.Printf("   ⚠️  Failed to generate embedding: %v", err)
			errorCount++
			continue
		}

		// Persist embedding to the database
		err = saveEmbedding(db, product, embedding)
		if err != nil {
			log.Printf("   ⚠️  Failed to save embedding: %v", err)
			errorCount++
			continue
		}

		successCount++
		log.Printf("   ✅ Embedded successfully (vector dim: %d)", len(embedding))

		// Brief pause to respect Bedrock rate limits
		time.Sleep(200 * time.Millisecond)
	}

	log.Println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	log.Printf("🎉 Embedding generation completed!")
	log.Printf("   ✅ Success: %d products", successCount)
	log.Printf("   ❌ Errors: %d products", errorCount)
	log.Println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

	if errorCount > 0 {
		os.Exit(1)
	}
}

// initBedrock initializes the AWS Bedrock runtime client
func initBedrock(ctx context.Context, region string) (*bedrockruntime.Client, error) {
	awsAccessKey := os.Getenv("AWS_ACCESS_KEY_ID")
	awsSecretKey := os.Getenv("AWS_SECRET_ACCESS_KEY")

	var cfg aws.Config
	var err error

	if awsAccessKey != "" && awsSecretKey != "" {
		cfg, err = config.LoadDefaultConfig(ctx,
			config.WithRegion(region),
			config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(
				awsAccessKey,
				awsSecretKey,
				"",
			)),
		)
	} else {
		cfg, err = config.LoadDefaultConfig(ctx,
			config.WithRegion(region),
		)
	}

	if err != nil {
		return nil, err
	}

	return bedrockruntime.NewFromConfig(cfg), nil
}

// fetchProducts retrieves all products from the database
func fetchProducts(db *sql.DB) ([]Product, error) {
	query := `
		SELECT 
			id, 
			name, 
			description, 
			price_usd_units + price_usd_nanos/1000000000.0 as price_usd,
			categories,
			picture
		FROM products
		ORDER BY id
	`

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var products []Product
	for rows.Next() {
		var p Product
		err := rows.Scan(&p.ID, &p.Name, &p.Description, &p.PriceUSD, &p.Categories, &p.Picture)
		if err != nil {
			log.Printf("⚠️  Failed to scan product: %v", err)
			continue
		}
		products = append(products, p)
	}

	return products, nil
}

// generateEmbedding calls Bedrock Titan Embeddings to produce a vector for the given text
func generateEmbedding(ctx context.Context, client *bedrockruntime.Client, text, modelId, dimensions string) ([]float32, error) {
	requestBody := map[string]interface{}{
		"inputText":  text,
		"dimensions": parseDimensions(dimensions),
		"normalize":  true,
	}

	jsonBody, err := json.Marshal(requestBody)
	if err != nil {
		return nil, err
	}

	input := &bedrockruntime.InvokeModelInput{
		ModelId:     aws.String(modelId),
		ContentType: aws.String("application/json"),
		Accept:      aws.String("application/json"),
		Body:        jsonBody,
	}

	timeoutCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	output, err := client.InvokeModel(timeoutCtx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to invoke bedrock: %w", err)
	}

	var response map[string]interface{}
	if err := json.Unmarshal(output.Body, &response); err != nil {
		return nil, err
	}

	embeddingInterface, ok := response["embedding"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid embedding format")
	}

	embedding := make([]float32, len(embeddingInterface))
	for i, v := range embeddingInterface {
		if f, ok := v.(float64); ok {
			embedding[i] = float32(f)
		}
	}

	return embedding, nil
}

// saveEmbedding upserts the product embedding into the product_embeddings table
func saveEmbedding(db *sql.DB, product Product, embedding []float32) error {
	vec := pgvector.NewVector(embedding)

	query := `
		INSERT INTO product_embeddings 
			(product_id, product_name, description, price_usd, categories, picture, embedding)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (product_id) 
		DO UPDATE SET 
			product_name = EXCLUDED.product_name,
			description = EXCLUDED.description,
			price_usd = EXCLUDED.price_usd,
			categories = EXCLUDED.categories,
			picture = EXCLUDED.picture,
			embedding = EXCLUDED.embedding,
			updated_at = CURRENT_TIMESTAMP
	`

	_, err := db.Exec(query,
		product.ID,
		product.Name,
		product.Description,
		product.PriceUSD,
		product.Categories,
		product.Picture,
		vec,
	)

	return err
}

// getEnv returns the value of an environment variable, or a default if unset
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// parseDimensions converts the EMBEDDING_DIMENSIONS env string to an integer
func parseDimensions(dimensions string) int {
	dims := strings.TrimSpace(dimensions)
	switch dims {
	case "256":
		return 256
	case "512":
		return 512
	case "1024":
		return 1024
	case "1536":
		return 1536
	default:
		return 1024
	}
}






