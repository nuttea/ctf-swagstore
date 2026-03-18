
// Copyright 2018 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"cloud.google.com/go/profiler"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
	
	// Datadog tracing
	"gopkg.in/DataDog/dd-trace-go.v1/ddtrace/tracer"
	grpctrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/google.golang.org/grpc"
	sqltrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/database/sql"
	"github.com/lib/pq"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/productcatalogservice/genproto"
)

var (
	cat          pb.ListProductsResponse
	catalogMutex *sync.Mutex
	log          *logrus.Logger
	
	// PostgreSQL connection handle (initialized in initDB)
	db *sql.DB
	
	extraLatency time.Duration
)

func init() {
	log = logrus.New()
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout
	catalogMutex = &sync.Mutex{}
	
	log.Info("Initializing productcatalogservice with sqltrace support v22 - fixed currency_code")
	
	sqltrace.Register("postgres", &pq.Driver{}, 
		sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
		sqltrace.WithServiceName("productcatalogservice-postgres"),
		sqltrace.WithAnalytics(true),
	)
	
	initDB()
	readCatalogFile()
}

func initDB() error {
	log.Info("Starting PostgreSQL connection with sqltrace v7...")
	
	// PostgreSQL connection configuration from environment variables
	postgresHost := os.Getenv("POSTGRES_HOST")
	if postgresHost == "" {
		postgresHost = "postgres"
	}
	
	postgresPort := os.Getenv("POSTGRES_PORT")
	if postgresPort == "" {
		postgresPort = "5432"
	}
	
	postgresUser := os.Getenv("POSTGRES_USER")
	if postgresUser == "" {
		postgresUser = "postgres"
	}
	
	postgresPassword := os.Getenv("POSTGRES_PASSWORD")
	if postgresPassword == "" {
		postgresPassword = "password"
	}
	
	postgresDB := os.Getenv("POSTGRES_DB")
	if postgresDB == "" {
		postgresDB = "swagstoredb"
	}
	
	// Build PostgreSQL connection string
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		postgresHost, postgresPort, postgresUser, postgresPassword, postgresDB)
	
	log.Info("Connecting to PostgreSQL with sqltrace v7...")
	
	// Open PostgreSQL connection instrumented with Datadog DBM tracing
	var err error
	db, err = sqltrace.Open("postgres", connStr, 
		sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
		sqltrace.WithServiceName("productcatalogservice-postgres"),
		sqltrace.WithAnalytics(true),
	)
	
	if err != nil {
		log.WithError(err).Error("Failed to connect to PostgreSQL")
		return err
	}
	
	// Verify connection is alive
	if err := db.Ping(); err != nil {
		log.WithError(err).Error("Failed to ping PostgreSQL")
		return err
	}
	
	log.Info("Successfully connected to PostgreSQL with sqltrace v7")
	return nil
}

func readCatalogFile() {
	catalogMutex.Lock()
	defer catalogMutex.Unlock()
	catalogJSON, err := os.ReadFile("products.json")
	if err != nil {
		log.Warnf("could not open product catalog file: %v", err)
		return
	}
	if err := json.Unmarshal(catalogJSON, &cat); err != nil {
		log.Warnf("could not parse the catalog JSON: %v", err)
		return
	}
	log.Info("successfully parsed product catalog json")
}

func parseCatalog() []*pb.Product {
	catalogMutex.Lock()
	defer catalogMutex.Unlock()
	return cat.Products
}

func mustParseEnv(target *time.Duration, envKey string) {
	v := os.Getenv(envKey)
	if v == "" {
		return
	}
	d, err := time.ParseDuration(v)
	if err != nil {
		panic(fmt.Sprintf("failed to parse %q: %v", envKey, err))
	}
	*target = d
}

// productCatalog implements the gRPC ProductCatalogService
type productCatalog struct {
}

func (p *productCatalog) ListProducts(ctx context.Context, req *pb.Empty) (*pb.ListProductsResponse, error) {
	span, ctx := tracer.StartSpanFromContext(ctx, "productcatalogservice.ListProducts")
	defer span.Finish()

	span.SetTag("service", "productcatalogservice")
	span.SetTag("operation", "list_products")
	
	time.Sleep(extraLatency)
	
	// Fetch all products from PostgreSQL (falls back to JSON catalog on error)
	products, err := getProductsFromDB(ctx)
	if err != nil {
		log.WithError(err).Error("Failed to get products from database, falling back to JSON")
		return &pb.ListProductsResponse{Products: parseCatalog()}, nil
	}
	
	span.SetTag("product_count", len(products))
	
	return &pb.ListProductsResponse{Products: products}, nil
}

func (p *productCatalog) GetProduct(ctx context.Context, req *pb.GetProductRequest) (*pb.Product, error) {
	startTime := time.Now()
	
	// Start APM span for GetProduct
	span, ctx := tracer.StartSpanFromContext(ctx, "productcatalogservice.GetProduct")
	defer span.Finish()
	
	span.SetTag("service", "productcatalogservice")
	span.SetTag("operation", "get_product")
	span.SetTag("product_id", req.Id)
	
	time.Sleep(extraLatency)
	
	// CTF #18-21: Inject artificial 11s latency for product 2ZYFJ3GM2N to simulate a slow downstream query
	// Expected: this product shows as the slowest in APM (GET /product/{id} endpoint)
	if req.Id == "2ZYFJ3GM2N" {
		span.SetTag("artificial_delay", "11s")
		time.Sleep(11 * time.Second)
	}
	
	// Fetch product from PostgreSQL; fall back to in-memory catalog if unavailable
	product, err := getProductFromDB(ctx, req.Id)
	if err != nil {
		log.WithError(err).Warn("Failed to get product from database, falling back to JSON")
		var found *pb.Product
		for i := 0; i < len(parseCatalog()); i++ {
			if req.Id == parseCatalog()[i].Id {
				found = parseCatalog()[i]
				break
			}
		}
		if found == nil {
			span.SetTag("error", true)
			span.SetTag("error.message", "product not found")
			return nil, status.Errorf(codes.NotFound, "no product with ID %s", req.Id)
		}
		
		// Log product info with trace context (JSON catalog fallback path)
		duration := time.Since(startTime)
		traceID := fmt.Sprintf("%v", span.Context().TraceID())
		spanID := fmt.Sprintf("%v", span.Context().SpanID())
		
		log.Infof("Returning product: ID=%s, Name=%s, Duration=%s dd.trace_id=%s, dd.span_id=%s",
			found.Id, found.Name, duration, traceID, spanID)
		
		return found, nil
	}
	
	// Log product info with trace context (database path)
	duration := time.Since(startTime)
	traceID := fmt.Sprintf("%v", span.Context().TraceID())
	spanID := fmt.Sprintf("%v", span.Context().SpanID())
	
	log.Infof("Returning product: ID=%s, Name=%s, Duration=%s dd.trace_id=%s, dd.span_id=%s",
		product.Id, product.Name, duration, traceID, spanID)
	
	return product, nil
}

// getProductFromDB fetches a single product from PostgreSQL by product ID
func getProductFromDB(ctx context.Context, productID string) (*pb.Product, error) {
	if db == nil {
		return nil, errors.New("database connection not available")
	}
	
	// Start APM span for the single-product SQL query (CTF #9 — product access logs)
	span, ctx := tracer.StartSpanFromContext(ctx, "db.query.get_product")
	defer span.Finish()
	
	// Tag span with DB query metadata
	span.SetTag("db.type", "postgresql")
	span.SetTag("db.instance", "swagstoredb")
	span.SetTag("db.table", "products")
	span.SetTag("db.operation", "select")
	span.SetTag("product_id", productID)
	span.SetTag("service", "productcatalogservice")
	
	query := `
		SELECT id, name, description, picture, price_usd_units, price_usd_nanos, categories
		FROM products 
		WHERE id = $1
	`
	
	span.SetTag("db.statement", query)
	
	row := db.QueryRowContext(ctx, query, productID)
	
	var product pb.Product
	var categories []string
	var priceUnits int64
	var priceNanos int32
	
	err := row.Scan(
		&product.Id,
		&product.Name,
		&product.Description,
		&product.Picture,
		&priceUnits,
		&priceNanos,
		pq.Array(&categories),
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			span.SetTag("error", true)
			span.SetTag("error.message", "product not found")
			return nil, status.Errorf(codes.NotFound, "no product with ID %s", productID)
		}
		span.SetTag("error", true)
		span.SetTag("error.message", err.Error())
		return nil, err
	}
	
	// Populate PriceUsd with scanned values (all prices stored as USD)
	product.PriceUsd = &pb.Money{
		CurrencyCode: "USD",
		Units:        priceUnits,
		Nanos:        priceNanos,
	}
	product.Categories = categories
	
	return &product, nil
}

// getProductsFromDB fetches all products from PostgreSQL
func getProductsFromDB(ctx context.Context) ([]*pb.Product, error) {
	if db == nil {
		return nil, errors.New("database connection not available")
	}
	
	// Start APM span for the bulk product SELECT query
	span, ctx := tracer.StartSpanFromContext(ctx, "db.query.get_products")
	defer span.Finish()
	
	// Tag span with DB query metadata
	span.SetTag("db.type", "postgresql")
	span.SetTag("db.instance", "swagstoredb")
	span.SetTag("db.table", "products")
	span.SetTag("db.operation", "select")
	span.SetTag("service", "productcatalogservice")
	
	query := `
		SELECT id, name, description, picture, price_usd_units, price_usd_nanos, categories
		FROM products 
		ORDER BY name
	`
	
	span.SetTag("db.statement", query)
	
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		span.SetTag("error", true)
		span.SetTag("error.message", err.Error())
		return nil, err
	}
	defer rows.Close()
	
	var products []*pb.Product
	
	for rows.Next() {
		var product pb.Product
		var categories []string
		var priceUnits int64
		var priceNanos int32
		
		err := rows.Scan(
			&product.Id,
			&product.Name,
			&product.Description,
			&product.Picture,
			&priceUnits,
			&priceNanos,
			pq.Array(&categories),
		)
		
		if err != nil {
			span.SetTag("error", true)
			span.SetTag("error.message", err.Error())
			return nil, err
		}
		
		// Populate PriceUsd (all prices stored as USD)
		product.PriceUsd = &pb.Money{
			CurrencyCode: "USD",
			Units:        priceUnits,
			Nanos:        priceNanos,
		}
		product.Categories = categories
		products = append(products, &product)
	}
	
	if err = rows.Err(); err != nil {
		span.SetTag("error", true)
		span.SetTag("error.message", err.Error())
		return nil, err
	}
	
	span.SetTag("product_count", len(products))
	
	return products, nil
}

func (p *productCatalog) SearchProducts(ctx context.Context, req *pb.SearchProductsRequest) (*pb.SearchProductsResponse, error) {
	span, ctx := tracer.StartSpanFromContext(ctx, "productcatalogservice.SearchProducts")
	defer span.Finish()

	span.SetTag("service", "productcatalogservice")
	span.SetTag("operation", "search_products")
	span.SetTag("query", req.Query)
	
	time.Sleep(extraLatency)
	
	// Get product list
	products := parseCatalog()
	ps := []*pb.Product{}
	for _, p := range products {
		if strings.Contains(strings.ToLower(p.Name), strings.ToLower(req.Query)) ||
			strings.Contains(strings.ToLower(p.Description), strings.ToLower(req.Query)) {
			ps = append(ps, p)
		}
	}
	
	span.SetTag("result_count", len(ps))
	
	return &pb.SearchProductsResponse{Results: ps}, nil
}

func initProfiling(service, version string) {
	// Profiling initialization
	for i := 1; i <= 3; i++ {
		if err := profiler.Start(profiler.Config{
			Service:        service,
			ServiceVersion: version,
			// ProjectID must be set if not running on GCP.
			// ProjectID: "my-project",
		}); err != nil {
			log.Warnf("failed to start profiler: %+v", err)
		} else {
			log.Info("started profiler")
			break
		}
		d := time.Second * 10 * time.Duration(i)
		log.Infof("sleeping %v to retry profiling", d)
		time.Sleep(d)
	}
}

func main() {
	// Initialize Datadog APM tracing (always enabled regardless of DISABLE_TRACING env var)
	log.Info("Tracing enabled.")
	tracer.Start(
		tracer.WithService("productcatalogservice"),
	)
	defer tracer.Stop()

	if os.Getenv("DISABLE_PROFILER") == "" {
		initProfiling("productcatalogservice", "1.0.0")
	}

	mustParseEnv(&extraLatency, "EXTRA_LATENCY")

	port := "3550"
	if os.Getenv("PORT") != "" {
		port = os.Getenv("PORT")
	}

	log.Infof("starting grpc server at :%s", port)
	run(port)
	select {}
}

func run(port string) string {
	l, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		log.Fatal(err)
	}

	// Create the server interceptor using the grpc trace package.
	si := grpctrace.StreamServerInterceptor(grpctrace.WithServiceName("productcatalogservice"))
	ui := grpctrace.UnaryServerInterceptor(grpctrace.WithServiceName("productcatalogservice"))
	srv := grpc.NewServer(
		grpc.UnaryInterceptor(ui),
		grpc.StreamInterceptor(si))

	svc := &productCatalog{}
	pb.RegisterProductCatalogServiceServer(srv, svc)
	reflection.Register(srv)

	//go func() {
	//	for {
	//		log.Info("catalog contains ", len(parseCatalog()), " products")
	//		time.Sleep(10 * time.Second)
	//	}
	//}()

	// Graceful shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-c
		log.Info("shutting down...")
		srv.GracefulStop()
		if db != nil {
			db.Close()
		}
		os.Exit(0)
	}()

	return srv.Serve(l).Error()
}
