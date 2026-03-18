package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
	"database/sql"
	"encoding/json"
	sqltrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/database/sql"

	grpctrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/google.golang.org/grpc"
	muxtrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/gorilla/mux"
	"gopkg.in/DataDog/dd-trace-go.v1/ddtrace/tracer"
	"gopkg.in/DataDog/dd-trace-go.v1/profiler"

	profilerold "cloud.google.com/go/profiler"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"github.com/lib/pq" // PostgreSQL driver
    //"golang.org/x/crypto/bcrypt"
	// "go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"google.golang.org/grpc"
)

const (
	port            = "8080"
	defaultCurrency = "USD"
	cookieMaxAge    = 60 * 60 * 48

	cookiePrefix    = "shop_"
	cookieSessionID = cookiePrefix + "session-id"
	cookieCurrency  = cookiePrefix + "currency"
)
var db *sql.DB

var (
	whitelistedCurrencies = map[string]bool{
		"USD": true,
		"EUR": true,
		"CAD": true,
		"JPY": true,
		"GBP": true,
		"TRY": true}
)

type ctxKeySessionID struct{}

type frontendServer struct {
	productCatalogSvcAddr string
	productCatalogSvcConn *grpc.ClientConn

	currencySvcAddr string
	currencySvcConn *grpc.ClientConn

	cartSvcAddr string
	cartSvcConn *grpc.ClientConn

	recommendationSvcAddr string
	recommendationSvcConn *grpc.ClientConn

	checkoutSvcAddr string
	checkoutSvcConn *grpc.ClientConn

	shippingSvcAddr string
	shippingSvcConn *grpc.ClientConn

	adSvcAddr string
	adSvcConn *grpc.ClientConn

	collectorAddr string
	collectorConn *grpc.ClientConn
}

func main() {
	// trigger skaffold build
	tracer.Start(tracer.WithRuntimeMetrics())
	defer tracer.Stop()
	ctx := context.Background()
	log := logrus.New()
	log.Level = logrus.DebugLevel
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout

	err := profiler.Start(
		profiler.WithProfileTypes(
			profiler.CPUProfile,
			profiler.HeapProfile,

			// The profiles below are disabled by
			// default to keep overhead low, but
			// can be enabled as needed.
			// profiler.BlockProfile,
			// profiler.MutexProfile,
			// profiler.GoroutineProfile,
		),
	)
	if err != nil {
		log.Fatal(err)
	}
	defer profiler.Stop()

	svc := new(frontendServer)

	if os.Getenv("ENABLE_TRACING") == "1" {
		log.Info("Tracing enabled.")
		initTracing(log, ctx, svc)
	} else {
		log.Info("Tracing disabled.")
	}

	if os.Getenv("ENABLE_PROFILER") == "1" {
		log.Info("Profiling enabled.")
		go initProfiling(log, "frontend", "1.0.0")
	} else {
		log.Info("Profiling disabled.")
	}

	srvPort := port
	if os.Getenv("PORT") != "" {
		srvPort = os.Getenv("PORT")
	}
	addr := os.Getenv("LISTEN_ADDR")
	mustMapEnv(&svc.productCatalogSvcAddr, "PRODUCT_CATALOG_SERVICE_ADDR")
	mustMapEnv(&svc.currencySvcAddr, "CURRENCY_SERVICE_ADDR")
	mustMapEnv(&svc.cartSvcAddr, "CART_SERVICE_ADDR")
	mustMapEnv(&svc.recommendationSvcAddr, "RECOMMENDATION_SERVICE_ADDR")
	mustMapEnv(&svc.checkoutSvcAddr, "CHECKOUT_SERVICE_ADDR")
	mustMapEnv(&svc.shippingSvcAddr, "SHIPPING_SERVICE_ADDR")
	mustMapEnv(&svc.adSvcAddr, "AD_SERVICE_ADDR")

	mustConnGRPC(ctx, &svc.currencySvcConn, svc.currencySvcAddr)
	mustConnGRPC(ctx, &svc.productCatalogSvcConn, svc.productCatalogSvcAddr)
	mustConnGRPC(ctx, &svc.cartSvcConn, svc.cartSvcAddr)
	mustConnGRPC(ctx, &svc.recommendationSvcConn, svc.recommendationSvcAddr)
	mustConnGRPC(ctx, &svc.shippingSvcConn, svc.shippingSvcAddr)
	mustConnGRPC(ctx, &svc.checkoutSvcConn, svc.checkoutSvcAddr)
	mustConnGRPC(ctx, &svc.adSvcConn, svc.adSvcAddr)

	// r := mux.NewRouter()
	r := muxtrace.NewRouter()
	r.HandleFunc("/", svc.homeHandler).Methods(http.MethodGet, http.MethodHead)
	r.HandleFunc("/product/{id}", svc.productHandler).Methods(http.MethodGet, http.MethodHead)
	r.HandleFunc("/cart", svc.viewCartHandler).Methods(http.MethodGet, http.MethodHead)
	r.HandleFunc("/cart", svc.addToCartHandler).Methods(http.MethodPost)
	r.HandleFunc("/cart/empty", svc.emptyCartHandler).Methods(http.MethodPost)
	r.HandleFunc("/setCurrency", svc.setCurrencyHandler).Methods(http.MethodPost)
	r.HandleFunc("/logout", svc.logoutHandler).Methods(http.MethodGet)
	r.HandleFunc("/cart/checkout", svc.placeOrderHandler).Methods(http.MethodPost)

	// New login routes
    r.HandleFunc("/login", loginHandler).Methods(http.MethodPost, http.MethodGet) // Login handler - supports both GET (page) and POST/GET (action)
    r.HandleFunc("/api/login", loginAPIHandler).Methods(http.MethodPost) // JSON API for Ajax

	r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./static/"))))
	r.HandleFunc("/robots.txt", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprint(w, "User-agent: *\nDisallow: /") })
	r.HandleFunc("/_healthz", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprint(w, "ok") })

	// Register JSON API route for product data
	r.HandleFunc("/api/product/{id}", svc.productAPIHandler).Methods(http.MethodGet)

	var handler http.Handler = r
	handler = &logHandler{log: log, next: handler} // add logging
	handler = ensureSessionID(handler)             // add session ID
	if os.Getenv("ENABLE_TRACING") == "1" {
		handler = otelhttp.NewHandler(handler, "frontend") // add OTel tracing
	}

	log.Infof("starting server on " + addr + ":" + srvPort)
	log.Fatal(http.ListenAndServe(addr+":"+srvPort, handler))
}
func initStats(log logrus.FieldLogger) {
	// TODO(arbrown) Implement OpenTelemtry stats
}

func init() {
    // Register PostgreSQL driver with Datadog DBM tracing — enables CTF challenges #60-66
    // (Database Monitoring: query samples, execution plans, lock wait events)
    sqltrace.Register("postgres", &pq.Driver{}, 
        sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
        sqltrace.WithServiceName("login-postgres"), // Explicit service name for DBM query attribution
        sqltrace.WithAnalytics(true),               // Enable Analytics for query visibility in Datadog
        // sqltrace.WithCommentInjection(true),     // SQL comment injection - not supported in current version
    )
	// Legacy global DB init (unused — each handler opens its own connection)
	// var err error
	// connStr := "host=postgres port=5432 user=postgres password=password dbname=swagstoredb sslmode=disable"
	// db, err = sqltrace.Open("postgres", connStr, sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull))
	// if err != nil {
	//	logrus.Fatal("database connection error:", err)
	//}
	// err = db.Ping()
	//if err != nil {
	//	logrus.Fatal("database ping error:", err)
	//}
}

// Login page handler
func loginPage(w http.ResponseWriter, r *http.Request) {
    // Wrap login page render in a trace span
    span, _ := tracer.StartSpanFromContext(r.Context(), "login.page")
    defer span.Finish()
    
    // Render login page template
    if err := templates.ExecuteTemplate(w, "login", map[string]interface{}{
        "session_id":        sessionID(r),
        "request_id":        r.Context().Value(ctxKeyRequestID{}),
        "user_currency":     currentCurrency(r),
        "show_currency":     true,
        "currencies":        []string{"EUR", "USD", "JPY", "GBP", "TRY", "CAD"},
        "cart_size":         0, // cart is not available on the login page
        "banner_color":      os.Getenv("BANNER_COLOR"),
        "platform_css":      plat.css,
        "platform_name":     plat.provider,
        "is_cymbal_brand":   isCymbalBrand,
    }); err != nil {
        log.Printf("Error rendering login template: %v", err)
        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
    }
}

// Login action handler — serves both GET (show page) and POST (authenticate)
// CTF #63-66: This handler deliberately creates DB lock contention visible in Datadog DBM
func loginHandler(w http.ResponseWriter, r *http.Request) {
    span, ctx := tracer.StartSpanFromContext(r.Context(), "login.handler")
    defer span.Finish()
    
    // Tag span with HTTP request attributes
    span.SetTag("http.method", r.Method)
    span.SetTag("http.url", r.URL.Path)

	username := r.FormValue("username")
	password := r.FormValue("password")
	
	// Show login page on GET requests with no credentials
	if r.Method == "GET" && username == "" && password == "" {
		loginPage(w, r)
		return
	}
	
	// Tag span with submitted username (visible in Datadog APM traces)
	span.SetTag("user.username", username)

    // Create DB connection span as child of the login span
    spanConnect, ctxConnect := tracer.StartSpanFromContext(ctx, "db.connect")
    defer spanConnect.Finish()
    
    // Extended timeout allows lock contention scenario to complete (CTF #65 — LOCK wait event)
    ctxWithTimeout, cancel := context.WithTimeout(ctxConnect, 10*time.Minute)
    defer cancel()
    
    // Tag span with DB connection metadata
    spanConnect.SetTag("db.type", "postgresql")
    spanConnect.SetTag("db.host", "postgres")
    spanConnect.SetTag("db.port", "5432")
    spanConnect.SetTag("db.name", "swagstoredb")
    spanConnect.SetTag("db.instance", "swagstoredb")
    spanConnect.SetTag("db.user", "postgres")
    spanConnect.SetTag("env", "ctf")
    spanConnect.SetTag("service", "frontend")

    connStr := "host=postgres port=5432 user=postgres password=password dbname=swagstoredb sslmode=disable"
    db, err := sqltrace.Open("postgres", connStr, 
        sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
        sqltrace.WithServiceName("login-postgres"),
        sqltrace.WithAnalytics(true),
    )
    if err != nil {
       log.Println("DB Connect Error:", err)
       span.SetTag("error", true)
       span.SetTag("error.msg", err.Error())
       http.Error(w, "Database connection error", http.StatusInternalServerError)
       return
    }
    defer db.Close()

    // Second DB connection to run the blocked SELECT on a separate transaction (CTF #65)
    db2, err := sqltrace.Open("postgres", connStr, 
        sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
        sqltrace.WithServiceName("login-postgres"),
        sqltrace.WithAnalytics(true),
    )
    if err != nil {
       log.Println("DB2 Connect Error:", err)
       span.SetTag("error", true)
       span.SetTag("error.msg", err.Error())
       http.Error(w, "Database connection error", http.StatusInternalServerError)
       return
    }
    defer db2.Close()

    // CTF #65: Transaction 1 — acquire EXCLUSIVE lock and hold it to block Tx2
    spanBegin1, ctxBegin1 := tracer.StartSpanFromContext(ctxConnect, "db.begin.blocking")
    defer spanBegin1.Finish()
    
    spanBegin1.SetTag("db.type", "postgresql")
    spanBegin1.SetTag("db.instance", "swagstoredb")
    spanBegin1.SetTag("db.user", "postgres")
    spanBegin1.SetTag("db.host", "postgres")
    spanBegin1.SetTag("db.port", "5432")
    spanBegin1.SetTag("env", "ctf")
    spanBegin1.SetTag("service", "frontend")

    tx1, err := db.BeginTx(ctxWithTimeout, nil)
    if err != nil {
        log.Println("Transaction 1 Begin Error:", err)
        spanBegin1.SetTag("error", true)
        spanBegin1.SetTag("error.msg", err.Error())
        http.Error(w, "Database error", http.StatusInternalServerError)
        return
    }

    // CTF #65: Span for the EXCLUSIVE table lock (Tx1) — visible in Datadog DBM as the blocking query
    spanLock, ctxLock := tracer.StartSpanFromContext(ctxBegin1, "db.lock.table.blocking")
    defer spanLock.Finish()
    
    spanLock.SetTag("db.table", "users")
    spanLock.SetTag("lock.type", "EXCLUSIVE")
    spanLock.SetTag("db.type", "postgresql")
    spanLock.SetTag("db.instance", "swagstoredb")
    spanLock.SetTag("db.user", "postgres")
    spanLock.SetTag("db.host", "postgres")
    spanLock.SetTag("db.port", "5432")
    spanLock.SetTag("env", "ctf")
    spanLock.SetTag("service", "frontend")

    // CTF #65: Acquire EXCLUSIVE lock on users table — blocks all concurrent SELECTs (Tx2)
    log.Printf("Acquiring EXCLUSIVE lock on users table")
    _, err = tx1.ExecContext(ctxLock, "LOCK TABLE public.\"users\" IN EXCLUSIVE MODE")
    if err != nil {
       log.Println("Table Lock Error:", err)
       spanLock.SetTag("error", true)
       spanLock.SetTag("error.msg", err.Error())
       tx1.Rollback()
       http.Error(w, "Database error", http.StatusInternalServerError)
       return
    }

    // CTF #65: Transaction 2 — run the SELECT that gets blocked by Tx1's EXCLUSIVE lock
    spanBegin2, ctxBegin2 := tracer.StartSpanFromContext(ctxConnect, "db.begin.blocked")
    defer spanBegin2.Finish()
    
    spanBegin2.SetTag("db.type", "postgresql")
    spanBegin2.SetTag("db.instance", "swagstoredb")
    spanBegin2.SetTag("db.user", "postgres")
    spanBegin2.SetTag("db.host", "postgres")
    spanBegin2.SetTag("db.port", "5432")
    spanBegin2.SetTag("env", "ctf")
    spanBegin2.SetTag("service", "frontend")

    tx2, err := db2.BeginTx(ctxWithTimeout, nil)
    if err != nil {
        log.Println("Transaction 2 Begin Error:", err)
        spanBegin2.SetTag("error", true)
        spanBegin2.SetTag("error.msg", err.Error())
        tx1.Rollback()
        http.Error(w, "Database error", http.StatusInternalServerError)
        return
    }

    // CTF #60/#65: Span for the blocked SELECT query (Tx2) — visible in Datadog DBM query samples
    spanQuery, ctxQuery := tracer.StartSpanFromContext(ctxBegin2, "db.query.select.password.blocked")
    defer spanQuery.Finish()
    
    spanQuery.SetTag("db.statement", "SELECT password FROM public.\"users\" WHERE username = $1 AND EXISTS (SELECT pg_sleep(0.2), count(*) FROM public.\"users\" WHERE length(username) > 0 GROUP BY substring(username, 1, 1) HAVING count(*) >= 0 ORDER BY username LIMIT 10)")
    spanQuery.SetTag("db.operation", "select")
    spanQuery.SetTag("db.type", "postgresql")
    spanQuery.SetTag("db.instance", "swagstoredb")
    spanQuery.SetTag("db.user", "postgres")
    spanQuery.SetTag("db.host", "postgres")
    spanQuery.SetTag("db.port", "5432")
    spanQuery.SetTag("env", "ctf")
    spanQuery.SetTag("service", "frontend")
    spanQuery.SetTag("blocked_by", "EXCLUSIVE_LOCK") // Visible in DBM as the lock wait event (CTF #66)

    // Execute SELECT that will be blocked until Tx1 releases the EXCLUSIVE lock
    log.Printf("Executing SELECT query that will be blocked...")

    // results holds matched rows for the authentication check
    var results []struct {
        Username string
        Password string
    }

    // Run vulnerable SELECT in a goroutine to create a natural lock contention scenario
    done := make(chan error, 1)
    go func() {
        // CTF #56/#57: Intentional SQL injection vulnerability for security challenge simulation
        // WARNING: string-formatted query — never use this pattern in production
        slowQuery := fmt.Sprintf(`
            SELECT username, password 
            FROM public."users" 
            WHERE (username = '%s')
            ORDER BY username
            LIMIT 10`, username)
        
        log.Printf("🚨 [VULNERABLE] Executing SQL: %s", slowQuery)
        
        // Artificial delay ensures lock contention is observable in Datadog DBM (CTF #66)
        time.Sleep(1 * time.Second)
        
        // Use QueryContext for multi-row result support
        rows, err := tx2.QueryContext(ctxQuery, slowQuery)
        if err != nil {
            done <- err
            return
        }
        defer rows.Close()
        
        // Scan both username and password columns
        for rows.Next() {
            var foundUsername, foundPassword string
            if err := rows.Scan(&foundUsername, &foundPassword); err != nil {
                done <- err
                return
            }
            results = append(results, struct {
                Username string
                Password string
            }{foundUsername, foundPassword})
            
            log.Printf("🚨 [VULNERABLE] Found user: %s, password: %s", foundUsername, foundPassword)
        }
        
        done <- rows.Err()
    }()

    // Hold lock long enough for contention to be visible in Datadog DBM (#66 — Lock wait event group)
    time.Sleep(2 * time.Second)

    // CTF #65: Commit Tx1 — releases EXCLUSIVE lock, unblocking Tx2
    spanCommit1, _ := tracer.StartSpanFromContext(ctxLock, "db.commit.release_lock")
    defer spanCommit1.Finish()
    
    spanCommit1.SetTag("db.type", "postgresql")
    spanCommit1.SetTag("db.instance", "swagstoredb")
    spanCommit1.SetTag("db.user", "postgres")
    spanCommit1.SetTag("db.host", "postgres")
    spanCommit1.SetTag("db.port", "5432")
    spanCommit1.SetTag("env", "ctf")
    spanCommit1.SetTag("service", "frontend")

    err = tx1.Commit()
    if err != nil {
       log.Println("Transaction 1 Commit Error:", err)
       spanCommit1.SetTag("error", true)
       spanCommit1.SetTag("error.msg", err.Error())
    }

    // Wait for Tx2 SELECT to complete after lock is released
    err = <-done
    if err != nil {
        log.Println("DB Query Error:", err)
        spanQuery.SetTag("error", true)
        spanQuery.SetTag("error.msg", err.Error())
        tx2.Rollback()
        http.Error(w, "Incorrect username or password", http.StatusUnauthorized)
        return
    }

    // Check returned rows for a matching password
    authenticated := false
    for _, result := range results {
        log.Printf("🚨 Checking user: %s with password: %s against input password: %s", result.Username, result.Password, password)
        if result.Password == password {
            authenticated = true
            log.Printf("🚨 Authentication successful for user: %s", result.Username)
            break
        }
    }

    if !authenticated {
        log.Printf("🚨 Authentication failed - no matching password found")
        span.SetTag("auth.result", "failed")
        span.SetTag("auth.reason", "incorrect_password")
        tx2.Rollback()
        http.Error(w, "Incorrect username or password", http.StatusUnauthorized)
        return
    }

    // Commit Tx2 to finalize the successful query
    spanCommit2, _ := tracer.StartSpanFromContext(ctxQuery, "db.commit.blocked_query")
    defer spanCommit2.Finish()
    
    spanCommit2.SetTag("db.type", "postgresql")
    spanCommit2.SetTag("db.instance", "swagstoredb")
    spanCommit2.SetTag("db.user", "postgres")
    spanCommit2.SetTag("db.host", "postgres")
    spanCommit2.SetTag("db.port", "5432")
    spanCommit2.SetTag("env", "ctf")
    spanCommit2.SetTag("service", "frontend")

    err = tx2.Commit()
    if err != nil {
       log.Println("Transaction 2 Commit Error:", err)
       spanCommit2.SetTag("error", true)
       spanCommit2.SetTag("error.msg", err.Error())
       http.Error(w, "Database error", http.StatusInternalServerError)
       return
    }

    // Tag span with successful authentication result
    span.SetTag("auth.result", "success")
    span.SetTag("http.status_code", "302")

    // Redirect to home page on successful login
    http.Redirect(w, r, "/", http.StatusFound)
}

// Login API request structure
type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

// Login API response structure
type LoginResponse struct {
    Success     bool   `json:"success"`
    Message     string `json:"message"`
    RedirectUrl string `json:"redirectUrl,omitempty"`
}

// RUMTraceInfo holds RUM-APM correlation headers for end-to-end trace linking (CTF #63)
type RUMTraceInfo struct {
    TraceID  string
    SpanID   string
    HasTrace bool
}

// extractRUMTraceInfo reads Datadog RUM propagation headers for APM-RUM correlation
func extractRUMTraceInfo(r *http.Request) RUMTraceInfo {
    // Read Datadog RUM trace propagation headers
    traceID := r.Header.Get("x-datadog-trace-id")
    spanID := r.Header.Get("x-datadog-parent-id")
    
    return RUMTraceInfo{
        TraceID:  traceID,
        SpanID:   spanID,
        HasTrace: traceID != "" && spanID != "",
    }
}

// JSON API Login handler — called by the login page via AJAX, correlates RUM session with APM trace
// CTF #63-66: Same lock contention pattern as loginHandler, used by attack-simulator (#56)
func loginAPIHandler(w http.ResponseWriter, r *http.Request) {
    // Extract RUM trace headers for APM-RUM correlation (CTF #63 — longest RUM event)
    rumInfo := extractRUMTraceInfo(r)
    
    // Start APM span for the JSON login API
    span, ctx := tracer.StartSpanFromContext(r.Context(), "login.api.handler")
    defer span.Finish()
    
    // Set JSON response content type
    w.Header().Set("Content-Type", "application/json")
    
    // Tag span with HTTP request attributes
    span.SetTag("http.method", r.Method)
    span.SetTag("http.url", r.URL.Path)
    span.SetTag("request.type", "ajax")
    span.SetTag("rum.correlation", rumInfo.HasTrace)
    
    // Propagate RUM trace context into APM span for end-to-end correlation (CTF #63)
    if rumInfo.HasTrace {
        span.SetTag("rum.trace_id", rumInfo.TraceID)
        span.SetTag("rum.span_id", rumInfo.SpanID)
    }
    
    // Parse JSON request body
    var loginReq LoginRequest
    if err := json.NewDecoder(r.Body).Decode(&loginReq); err != nil {
        span.SetTag("error", true)
        span.SetTag("error.msg", "Invalid JSON request")
        
        response := LoginResponse{
            Success: false,
            Message: "Invalid request format",
        }
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(response)
        return
    }
    
    // Tag span with submitted username
    span.SetTag("user.username", loginReq.Username)
    
    // Create DB connection span as child of login.api.handler span
    spanConnect, ctxConnect := tracer.StartSpanFromContext(ctx, "db.connect")
    defer spanConnect.Finish()
    
    // Extended timeout allows lock contention scenario to complete (CTF #65)
    ctxWithTimeout, cancel := context.WithTimeout(ctxConnect, 10*time.Minute)
    defer cancel()
    
    // Tag span with DB connection metadata
    spanConnect.SetTag("db.type", "postgresql")
    spanConnect.SetTag("db.host", "postgres")
    spanConnect.SetTag("db.port", "5432")
    spanConnect.SetTag("db.name", "swagstoredb")
    spanConnect.SetTag("db.instance", "swagstoredb")
    spanConnect.SetTag("db.user", "postgres")
    spanConnect.SetTag("env", "ctf")
    spanConnect.SetTag("service", "frontend")

    connStr := "host=postgres port=5432 user=postgres password=password dbname=swagstoredb sslmode=disable"
    db, err := sqltrace.Open("postgres", connStr, 
        sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
        sqltrace.WithServiceName("login-postgres"),
        sqltrace.WithAnalytics(true),
    )
    if err != nil {
        span.SetTag("error", true)
        span.SetTag("error.msg", err.Error())
        
        response := LoginResponse{
            Success: false,
            Message: "Database connection error",
        }
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(response)
        return
    }
    defer db.Close()

    // Second DB connection for the blocked SELECT (same locking pattern as loginHandler)
    db2, err := sqltrace.Open("postgres", connStr, 
        sqltrace.WithDBMPropagation(tracer.DBMPropagationModeFull),
        sqltrace.WithServiceName("login-postgres"),
        sqltrace.WithAnalytics(true),
    )
    if err != nil {
        span.SetTag("error", true)
        span.SetTag("error.msg", err.Error())
        
        response := LoginResponse{
            Success: false,
            Message: "Database connection error",
        }
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(response)
        return
    }
    defer db2.Close()

    // CTF #65: Transaction 1 — acquire EXCLUSIVE lock and hold it to block Tx2
    spanBegin1, ctxBegin1 := tracer.StartSpanFromContext(ctxConnect, "db.begin.blocking")
    defer spanBegin1.Finish()
    
    spanBegin1.SetTag("db.type", "postgresql")
    spanBegin1.SetTag("db.instance", "swagstoredb")
    spanBegin1.SetTag("db.user", "postgres")
    spanBegin1.SetTag("db.host", "postgres")
    spanBegin1.SetTag("db.port", "5432")
    spanBegin1.SetTag("env", "ctf")
    spanBegin1.SetTag("service", "frontend")

    tx1, err := db.BeginTx(ctxWithTimeout, nil)
    if err != nil {
        spanBegin1.SetTag("error", true)
        spanBegin1.SetTag("error.msg", err.Error())
        
        response := LoginResponse{
            Success: false,
            Message: "Database error",
        }
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(response)
        return
    }

    // CTF #65: Span for the EXCLUSIVE table lock (Tx1) — visible in Datadog DBM as the blocking query
    spanLock, ctxLock := tracer.StartSpanFromContext(ctxBegin1, "db.lock.table.blocking")
    defer spanLock.Finish()
    
    spanLock.SetTag("db.table", "users")
    spanLock.SetTag("lock.type", "EXCLUSIVE")
    spanLock.SetTag("db.type", "postgresql")
    spanLock.SetTag("db.instance", "swagstoredb")
    spanLock.SetTag("db.user", "postgres")
    spanLock.SetTag("db.host", "postgres")
    spanLock.SetTag("db.port", "5432")
    spanLock.SetTag("env", "ctf")
    spanLock.SetTag("service", "frontend")

    // CTF #65: Acquire EXCLUSIVE lock on users table — blocks all concurrent SELECTs (Tx2)
    _, err = tx1.ExecContext(ctxLock, "LOCK TABLE public.\"users\" IN EXCLUSIVE MODE")
    if err != nil {
        spanLock.SetTag("error", true)
        spanLock.SetTag("error.msg", err.Error())
        tx1.Rollback()
        
        response := LoginResponse{
            Success: false,
            Message: "Database error",
        }
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(response)
        return
    }

    // CTF #65: Transaction 2 — run the SELECT blocked by Tx1's EXCLUSIVE lock
    spanBegin2, ctxBegin2 := tracer.StartSpanFromContext(ctxConnect, "db.begin.blocked")
    defer spanBegin2.Finish()
    
    spanBegin2.SetTag("db.type", "postgresql")
    spanBegin2.SetTag("db.instance", "swagstoredb")
    spanBegin2.SetTag("db.user", "postgres")
    spanBegin2.SetTag("db.host", "postgres")
    spanBegin2.SetTag("db.port", "5432")
    spanBegin2.SetTag("env", "ctf")
    spanBegin2.SetTag("service", "frontend")

    tx2, err := db2.BeginTx(ctxWithTimeout, nil)
    if err != nil {
        spanBegin2.SetTag("error", true)
        spanBegin2.SetTag("error.msg", err.Error())
        tx1.Rollback()
        
        response := LoginResponse{
            Success: false,
            Message: "Database error",
        }
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(response)
        return
    }

    // CTF #60/#65: Span for the blocked SELECT query — visible in Datadog DBM query samples
    spanQuery, ctxQuery := tracer.StartSpanFromContext(ctxBegin2, "db.query.select.password.blocked")
    defer spanQuery.Finish()
    
    spanQuery.SetTag("db.statement", "SELECT username, password FROM public.users WHERE username = ? AND EXISTS (...)")
    spanQuery.SetTag("db.operation", "select")
    spanQuery.SetTag("db.type", "postgresql")
    spanQuery.SetTag("db.instance", "swagstoredb")
    spanQuery.SetTag("db.user", "postgres")
    spanQuery.SetTag("db.host", "postgres")
    spanQuery.SetTag("db.port", "5432")
    spanQuery.SetTag("env", "ctf")
    spanQuery.SetTag("service", "frontend")
    spanQuery.SetTag("blocked_by", "EXCLUSIVE_LOCK")

    // CTF #60: Vulnerable SELECT — visible in Datadog DBM as the top login credential query
    var results []struct {
        Username string
        Password string
    }

    done := make(chan error, 1)
    go func() {
        // CTF #56/#57: Intentional SQL injection vulnerability for security challenge simulation
        // WARNING: string-formatted query — never use this pattern in production
        slowQuery := fmt.Sprintf(`
            SELECT username, password 
            FROM public."users" 
            WHERE (username = '%s')
            ORDER BY username
            LIMIT 10`, loginReq.Username)
        
        log.Printf("🚨 [VULNERABLE] Executing SQL: %s", slowQuery)
        
        // Use QueryContext for multi-row result support
        rows, err := tx2.QueryContext(ctxQuery, slowQuery)
        if err != nil {
            done <- err
            return
        }
        defer rows.Close()
        
        // Scan both username and password columns
        for rows.Next() {
            var foundUsername, foundPassword string
            if err := rows.Scan(&foundUsername, &foundPassword); err != nil {
                done <- err
                return
            }
            results = append(results, struct {
                Username string
                Password string
            }{foundUsername, foundPassword})
            
            log.Printf("🚨 [VULNERABLE] Found user: %s, password: %s", foundUsername, foundPassword)
        }
        
        done <- rows.Err()
    }()

    // Hold lock long enough for contention to be visible in Datadog DBM (CTF #66 — Lock wait event group)
    time.Sleep(2 * time.Second)

    // CTF #65: Commit Tx1 — releases EXCLUSIVE lock, unblocking Tx2
    spanCommit1, _ := tracer.StartSpanFromContext(ctxConnect, "db.commit.release_lock")
    defer spanCommit1.Finish()
    
    spanCommit1.SetTag("db.type", "postgresql")
    spanCommit1.SetTag("db.instance", "swagstoredb")
    spanCommit1.SetTag("db.user", "postgres")
    spanCommit1.SetTag("db.host", "postgres")
    spanCommit1.SetTag("db.port", "5432")
    spanCommit1.SetTag("env", "ctf")
    spanCommit1.SetTag("service", "frontend")

    err = <-done
    if err != nil {
        spanQuery.SetTag("error", true)
        spanQuery.SetTag("error.msg", err.Error())
        
        response := LoginResponse{
            Success: false,
            Message: "Incorrect username or password",
        }
        w.WriteHeader(http.StatusUnauthorized)
        json.NewEncoder(w).Encode(response)
        return
    }

    // Check returned rows for a matching password
    authenticated := false
    for _, result := range results {
        log.Printf("🚨 Checking user: %s with password: %s against input password: %s", result.Username, result.Password, loginReq.Password)
        if result.Password == loginReq.Password {
            authenticated = true
            log.Printf("🚨 Authentication successful for user: %s", result.Username)
            break
        }
    }

    if !authenticated {
        log.Printf("🚨 Authentication failed - no matching password found")
        span.SetTag("auth.result", "failed")
        span.SetTag("auth.reason", "incorrect_password")
        tx2.Rollback()
        
        response := LoginResponse{
            Success: false,
            Message: "Incorrect username or password",
        }
        w.WriteHeader(http.StatusUnauthorized)
        json.NewEncoder(w).Encode(response)
        return
    }

    // Commit Tx2 to finalize the successful query
    spanCommit2, _ := tracer.StartSpanFromContext(ctxQuery, "db.commit.blocked_query")
    defer spanCommit2.Finish()
    
    spanCommit2.SetTag("db.type", "postgresql")
    spanCommit2.SetTag("db.instance", "swagstoredb")
    spanCommit2.SetTag("db.user", "postgres")
    spanCommit2.SetTag("db.host", "postgres")
    spanCommit2.SetTag("db.port", "5432")
    spanCommit2.SetTag("env", "ctf")
    spanCommit2.SetTag("service", "frontend")

    err = tx2.Commit()
    if err != nil {
       spanCommit2.SetTag("error", true)
       spanCommit2.SetTag("error.msg", err.Error())
       
       response := LoginResponse{
           Success: false,
           Message: "Database error",
       }
       w.WriteHeader(http.StatusInternalServerError)
       json.NewEncoder(w).Encode(response)
       return
    }

    // Tag span with successful authentication result
    span.SetTag("auth.result", "success")
    span.SetTag("http.status_code", "200")

    // Return success response with redirect URL
    response := LoginResponse{
        Success:     true,
        Message:     "Login successful",
        RedirectUrl: "/",
    }
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(response)
}

func initTracing(log logrus.FieldLogger, ctx context.Context, svc *frontendServer) (*sdktrace.TracerProvider, error) {
	mustMapEnv(&svc.collectorAddr, "COLLECTOR_SERVICE_ADDR")
	mustConnGRPC(ctx, &svc.collectorConn, svc.collectorAddr)
	exporter, err := otlptracegrpc.New(
		ctx,
		otlptracegrpc.WithGRPCConn(svc.collectorConn))
	if err != nil {
		log.Warnf("warn: Failed to create trace exporter: %v", err)
	}
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithSampler(sdktrace.AlwaysSample()))
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(
		propagation.NewCompositeTextMapPropagator(
			propagation.TraceContext{}, propagation.Baggage{}))
	return tp, err
}

func initProfiling(log logrus.FieldLogger, service, version string) {
	// TODO(ahmetb) this method is duplicated in other microservices using Go
	// since they are not sharing packages.
	for i := 1; i <= 3; i++ {
		log = log.WithField("retry", i)
		if err := profilerold.Start(profilerold.Config{
			Service:        service,
			ServiceVersion: version,
			// ProjectID must be set if not running on GCP.
			// ProjectID: "my-project",
		}); err != nil {
			log.Warnf("warn: failed to start profiler: %+v", err)
		} else {
			log.Info("started Stackdriver profiler")
			return
		}
		d := time.Second * 10 * time.Duration(i)
		log.Debugf("sleeping %v to retry initializing Stackdriver profiler", d)
		time.Sleep(d)
	}
	log.Warn("warning: could not initialize Stackdriver profiler after retrying, giving up")
}

func mustMapEnv(target *string, envKey string) {
	v := os.Getenv(envKey)
	if v == "" {
		panic(fmt.Sprintf("environment variable %q not set", envKey))
	}
	*target = v
}

func mustConnGRPC(ctx context.Context, conn **grpc.ClientConn, addr string) {
	var err error
	ctx, cancel := context.WithTimeout(ctx, time.Second*3)
	defer cancel()
	if os.Getenv("ENABLE_TRACING") == "1" {
		*conn, err = grpc.DialContext(ctx, addr,
			grpc.WithInsecure(),
			grpc.WithUnaryInterceptor(grpctrace.UnaryClientInterceptor(grpctrace.WithServiceName("frontend"))),
            grpc.WithStreamInterceptor(grpctrace.StreamClientInterceptor(grpctrace.WithServiceName("frontend"))))
			// grpc.WithUnaryInterceptor(otelgrpc.UnaryClientInterceptor()),
			// grpc.WithStreamInterceptor(otelgrpc.StreamClientInterceptor()))
	} else {
		// Create the client interceptor using the grpc trace package.
		si := grpctrace.StreamClientInterceptor(grpctrace.WithServiceName("frontend"))
		ui := grpctrace.UnaryClientInterceptor(grpctrace.WithServiceName("frontend"))
		*conn, err = grpc.DialContext(ctx, addr,
		 	grpc.WithInsecure(),
			grpc.WithUnaryInterceptor(ui),
			grpc.WithStreamInterceptor(si))
	 }
	if err != nil {
		panic(errors.Wrapf(err, "grpc: failed to connect %s", addr))
	}
}

// Chatbot API Proxy Handler
func chatbotProxyHandler(w http.ResponseWriter, r *http.Request) {
	span, _ := tracer.StartSpanFromContext(r.Context(), "chatbot.proxy")
	defer span.Finish()
	
	span.SetTag("http.method", r.Method)
	span.SetTag("http.url", r.URL.Path)
	
	// Get chatbot API service address
	chatbotAPIAddr := os.Getenv("CHATBOT_API_ADDR")
	if chatbotAPIAddr == "" {
		chatbotAPIAddr = "http://chatbot-api:8080"
	}
	
	// Build proxy target URL
	targetURL := chatbotAPIAddr + "/api/chat"
	
	// Create proxy HTTP request
	proxyReq, err := http.NewRequestWithContext(r.Context(), "POST", targetURL, r.Body)
	if err != nil {
		span.SetTag("error", true)
		span.SetTag("error.msg", err.Error())
		http.Error(w, "Failed to create proxy request", http.StatusInternalServerError)
		return
	}
	
	// Forward Content-Type header
	proxyReq.Header.Set("Content-Type", "application/json")
	
	// Execute proxy request
	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(proxyReq)
	if err != nil {
		span.SetTag("error", true)
		span.SetTag("error.msg", err.Error())
		http.Error(w, "Failed to proxy request", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	
	// Read proxy response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		span.SetTag("error", true)
		span.SetTag("error.msg", err.Error())
		http.Error(w, "Failed to read response body", http.StatusInternalServerError)
		return
	}
	
	// Set response Content-Type and forward upstream status code
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(body)
	
	span.SetTag("http.status_code", resp.StatusCode)
}
