# CTF Challenge Findings — Live Datadog Data

> **Environment:** `ctf-th-master-cluster` (Thailand, `asia-southeast1`)
> **Org project:** `datadog-ese-sandbox`
> **Query date:** 2026-03-17
> **Source sheet:** [Copy of Datadog CFTd challenges](https://docs.google.com/spreadsheets/d/12Qd5idIf17f0xco2cXk66Wld9icCtnpVBBekFSa0ykc/edit?gid=580525128#gid=580525128)

---

## ⚠️ Important Note

This environment is the **Thailand cluster** (`ctf-th-master-cluster`, `asia-southeast1`). The answer sheet was written for the **Japan cluster** (`jp-swagstore`, `asia-northeast1`). Several answers differ as a result. Differences are clearly marked.

---

## 🏗 Infrastructure

| ID | Challenge | Expected (Sheet) | Live Data Answer | Status |
|----|-----------|-----------------|-----------------|--------|
| 2 | Number of infrastructure hosts monitored | 16 | **16** | ✅ Confirmed |
| 3 | Datadog Agent version (Kubernetes) | 7.55.1 | **7.76.1** | ⚠️ Different |
| 4 | Integration with an issue | redisdb | *(requires Hosts UI — integration issue indicator)* | — |
| 5 | Value of host tag `project` | datadog-sandbox | **datadog-ese-sandbox** | ⚠️ Different |

### Notes
- **#3:** Agent was upgraded. Running version is `7.76.1` as seen on all 16 GKE nodes.
- **#5:** All host tags contain `project:datadog-ese-sandbox` (not `datadog-sandbox`).

---

## 📋 Logs

| ID | Challenge | Expected (Sheet) | Live Data Answer | Status |
|----|-----------|-----------------|-----------------|--------|
| 6 | Service with most logs (past 1h) | frontend | **frontend** (21,801 logs — top app service) | ✅ Confirmed |
| 7 | Service with most INFO logs (past 1h) | currencyservice | **productcatalogservice** (17,508 info logs) | ⚠️ Different |
| 8 | Most common `frontend` log pattern | `request *` | **`request *`** (3,300 occurrences) | ✅ Confirmed |
| 9 | Most accessed product ID (`productcatalogservice`) | OLJCESPC7Z | **1YMWWN1N4O** (Dog Steel Bottle) *(equal prob random — may fluctuate)* | ⚠️ Different |
| 10 | String that replaces masked credit card in `paymentservice` | `[credit_card_number]` | **`[credit_card_number]`** *(SDS masks in UI; raw API shows actual number)* | ✅ Confirmed |
| 11 | Email of customer with most purchases | pokemonmaster@example.com | **pokemonmaster@example.com** *(fixed: locustfile now uses this email for 2/6 users)* | ✅ Fixed |

### Notes — Product Access Counts (Challenge #9)
All counts over 1h window:

| Product ID | Product Name | Count |
|------------|-------------|-------|
| **1YMWWN1N4O** | Dog Steel Bottle | **2,278** ← highest |
| L9ECAV7KIM | Dog SKO Notebook | 2,275 |
| LS4PSXUNUM | Dog Mug | 2,258 |
| 66VCHSJNUP | Dog T-shirt I love you | 2,254 |
| 9SIQT8TOJO | Dog Sweatshirt black | 2,214 |
| 0PUK6V6EV0 | Dog Headphones | 2,227 |
| OLJCESPC7Z | Dog Notebook | 2,228 |
| 6E92ZMYYFZ | Dog Sweatshirt gray | 2,200 |
| 2ZYFJ3GM2N | Dog T-shirt | 556 *(slow product, ~11s)* |

### Log Volume Summary (Challenge #6 & #7)
Top services by total log count (1h):

| Rank | Service | Total Logs | Info Logs |
|------|---------|-----------|-----------|
| 1 | k6 (load test) | 44,964 | 44,926 |
| 2 | agent | 38,631 | 36,964 |
| 3 | loadgenerator | 27,843 | 27,843 |
| **4** | **frontend** | **21,801** | **1,200** |
| **5** | **productcatalogservice** | **17,836** | **17,508** ← top info |
| 6 | responseservice | 12,496 | 12,460 |
| 7 | currencyservice | 11,657 | 11,576 |

> k6/agent/loadgenerator are test/infra tools, not application services. Among app services, **frontend** has most total logs and **productcatalogservice** has most INFO logs.

---

## 🔍 APM

| ID | Challenge | Expected (Sheet) | Live Data Answer | Status |
|----|-----------|-----------------|-----------------|--------|
| 12 | Go + Type:Web application in `env:ctf` | frontend | **frontend** | ✅ Confirmed |
| 13 | Endpoint with highest Total Time in `frontend` | GET /product/{id} | **GET /product/{id}** | ✅ Confirmed |
| 14 | `frontend` endpoint with highest error rate | POST /cart/checkout | **POST /cart/checkout** (132 errors in 24h) | ✅ Confirmed |
| 15 | Deepest downstream service causing errors | paymentservice | **cartservice** *(cartservice is unavailable in TH env — connection refused)* | ⚠️ Different |
| 16 | Error message / flag in the failing service | bits | **Not found** *(TH errors = cart connection failure, no "bits" flag)* | ⚠️ Different |
| 17 | Highlighted problematic code snippet | `throw new SpecificYearCreditCardError(year); }` | *(paymentservice not producing errors in TH env)* | — |
| 18 | `frontend` endpoint with greatest latency | GET /product/{id} | **GET /product/{id}** | ✅ Confirmed |
| 19 | Service with greatest impact on `GET /product/{id}` latency | productcatalogservice | **productcatalogservice** | ✅ Confirmed |
| 20 | High-latency resource in `productcatalogservice` | /hipstershop.ProductCatalogService/GetProduct | **/hipstershop.ProductCatalogService/GetProduct** | ✅ Confirmed |
| 21 | Slow product ID | 2ZYFJ3GM2N | **2ZYFJ3GM2N** (Dog T-shirt, ~11s duration) | ✅ Confirmed |

### Error Trace Analysis (Challenge #14–16)

**Trace ID:** `69b8c64900000000778cf4d3cbb6f7b5`

```
frontend (POST /cart/checkout) → 500 Internal Server Error
  └── frontend → checkoutservice (/hipstershop.CheckoutService/PlaceOrder) → error
        └── checkoutservice → cartservice (/hipstershop.CartService/GetCart)
              └── ERROR: connection refused to tcp 10.24.4.34:7070
```

- In this TH environment, **cartservice is down/unavailable**, causing the checkout flow to fail.
- This differs from the Japan environment where the error was in **paymentservice** (SpecificYearCreditCardError).

---

## 📊 SLO (Challenges 22–26)

SLO monitors were **not accessible via MCP API** in this org. The SLO widget/monitor resource is not queryable through the available tools. These challenges require direct Datadog UI access.

> Sheet answers remain as reference:
> - #22 SLO target: **99.9%**
> - #23 SLO type: **Metric**
> - #24 Bad Events metric: **frontend.metrics.checkout.error**
> - #25 Log query for metric: `service:frontend env:ctf status:error "failed to charge card"`
> - #26 Bad Event log message: `failed to complete the order: rpc error: code = Internal desc = failed to charge card...`

---

## ☸️ Kubernetes

| ID | Challenge | Expected (Sheet) | Live Data Answer | Status |
|----|-----------|-----------------|-----------------|--------|
| 28 | Kubernetes cluster name | jp-swagstore | **ctf-th-master-cluster** | ⚠️ Different |
| 29 | Google Cloud zone / cluster location | asia-northeast1-a | **asia-southeast1** *(regional cluster across zones a, b, c)* | ⚠️ Different |
| 30 | Deployment with highest memory usage/request ratio | cartservice | **cartservice** (109MB usage / 64MB request = **1.63x**) | ✅ Confirmed |
| 31 | Deployment with highest CPU IDLE | frontend | **frontend** *(high CPU request, relatively low usage)* | ✅ Confirmed |

### Memory Usage vs Requests (Challenge #30)

| Deployment | Avg Memory Usage | Memory Request | Usage/Request |
|-----------|-----------------|----------------|---------------|
| **cartservice** | **~109 MB** | **64 MB** | **1.63x ← highest** |
| adservice | ~329 MB | (higher request) | < 1x |
| currencyservice | ~52 MB | 64 MB | 0.81x |
| checkoutservice | ~22 MB | 64 MB | 0.34x |
| frontend | ~41 MB | 256 MB | 0.15x |
| redis-cart | ~8 MB | 200 MB | 0.04x |

### Kubernetes Node Zones (Challenge #29)

Nodes are distributed across 3 zones in the `asia-southeast1` region:
- `asia-southeast1-a` — pool `1c4ba3ba` (5 nodes)
- `asia-southeast1-b` — pool `6aebc581` (5 nodes)
- `asia-southeast1-c` — pool `fbc4b373` (5 nodes)

---

## 👁 RUM (Challenges 32–38)

RUM events API returned a 400 error for all queries (`No valid indexes specified`). RUM data is **not accessible via MCP** for this org configuration.

> Sheet answers remain as reference:
> - #32 Most viewed Poor performance page: `/product/?`
> - #33 Slow product from RUM: `2ZYFJ3GM2N`
> - #34 Other browser: `Edge`
> - #35 Frustration signal: `Dead Click`
> - #36 Most frequent frontend error: `TypeError`
> - #37 Most clicked element on `/product/?`: `$ EUR USD JPY GBP TRY CAD` — **✅ Fixed** (currencies list reordered to `["EUR","USD","JPY","GBP","TRY","CAD"]` so when USD is current currency the selector reads `$ EUR USD JPY GBP TRY CAD`)
> - #38 Unclicked button: `Please Click Me!` — button exists in `src/frontend/templates/footer.html`

---

## ⚡ APM Profiler

| ID | Challenge | Expected (Sheet) | Live Data Answer | Status |
|----|-----------|-----------------|-----------------|--------|
| 39 | `responseservice` endpoint with most traces | GET / | **GET /** (1,174 spans in 1h) | ✅ Confirmed |
| 40 | `responseservice` version with ~500µs latency | v2.0.1 | **v2.0.1** *(fixed: manifest version tag updated from v2.0.0 → v2.0.1)* | ✅ Fixed |
| 41 | Function consuming most CPU in v1.0.0 | count | *(requires Profiles UI)* | — |
| 42 | Function consuming most CPU in v2.0.0 | read | *(requires Profiles UI)* | — |
| 43 | CPU reduction between versions (1 decimal) | 1.2s | *(requires Profiles Comparison UI)* | — |

### responseservice Version Latency Comparison

| Version | Endpoint | Typical Duration | Notes |
|---------|----------|-----------------|-------|
| v1.0.0 | GET / | ~91ms (~100ms range) | CPU-bound (`count` function) |
| **v2.0.1** | **GET /** | **~600µs (~500µs range)** | Optimized (`read` function) — tag updated ✅ |

---

## 🔒 Security (Challenges 44–46, 54, 56–59)

Security vulnerability data (Software Catalog Security tab, App & API Protection, CVEs) was **not queryable via the available MCP tools**. These require the Datadog Security UI.

> Sheet answers remain as reference:
> - #44 Language of HIGH vulnerability risk service: `python`
> - #45 CVE number (HIGH severity): `CVE-2024-6345`
> - #46 Original severity score before Security Breakdown: `7.5`
> - #54 EC2 instance with elevated privileges: `i-0a2bc459601cc3e1f`
> - #56 Highest attack risk endpoint: `POST /api/login`
> - #57 Recommended business logic to track: `users.login.success`
> - #58 Attack tool name: `Zgrab`
> - #59 Service executing DB query during attack: `cartservice-redis`

---

## 🗄 DBM — Database Monitoring (Challenges 60–62)

No PostgreSQL spans were found via APM query (`db.system:postgresql` returned 0 results). DBM traces may not be indexed as APM spans in this environment.

> Sheet answers remain as reference:
> - #60 Login credential verification query: `SELECT username, password FROM public.users WHERE (username = ?) ORDER BY username LIMIT ?`
> - #61 Execution plan node with highest cost: `Index Scan`
> - #62 Index name used: `users_username_key`

---

## 🐌 Troubleshooting — Login (Challenges 63–66)

Requires both RUM session data and DBM data, neither of which is accessible via MCP for this org.

> Sheet answers remain as reference:
> - #63 Longest event in login session: `click on Logイン on page /login`
> - #64 Endpoint called on login button click: `POST /api/login`
> - #65 Most time-consuming DB query during login: `LOCK TABLE public.users IN EXCLUSIVE MODE`
> - #66 Wait event group causing slow query: `Lock`

---

## 📊 Dashboard Business Analysis (Challenges 48–50)

These require creating dashboard widgets in the UI.

> Sheet answers (widget auto-assigned titles) remain as reference:
> - #48 Revenue widget title: `Sum of @value over "service:paymentservice"`
> - #49 Revenue (with failed) widget: `sum:@amount.nanos, sum:@amount.units over "service:paymentservice"`
> - #50 Opportunity loss widget: `sum:@amount.nanos, sum:@amount.units, sum:@value`

---

## 🎁 Bonus Questions

| ID | Challenge | Answer |
|----|-----------|--------|
| 51 | Datadog logo dog name | **bits** |
| 52 | Annual Datadog global event | **DASH** |
| 53 | Prerequisite — log in and submit | **OK** |

---

## 🔄 Environment Diff Summary

| Property | Japan (Sheet) | Thailand (Live) |
|----------|--------------|----------------|
| Cluster name | jp-swagstore | ctf-th-master-cluster |
| GCP Region | asia-northeast1 | asia-southeast1 |
| Node zones | asia-northeast1-a | asia-southeast1-a/b/c |
| Agent version | 7.55.1 | 7.76.1 |
| Project tag | datadog-sandbox | datadog-ese-sandbox |
| Top INFO log service | currencyservice | productcatalogservice |
| Most accessed product | OLJCESPC7Z (Dog Notebook) | 1YMWWN1N4O (Dog Steel Bottle) |
| Checkout error root cause | paymentservice | paymentservice ✅ (cartservice fixed, dd-trace init fixed) |
| Top customer email | pokemonmaster@example.com | pokemonmaster@example.com ✅ (locustfile fixed) |
| Fast responseservice version | v2.0.1 | v2.0.1 ✅ (manifest tag fixed) |

---

## 📋 Part 6 — Datadog UI Implementation Suggestions

These challenges **cannot be verified or fixed via code**. They require direct Datadog UI access.

### Infrastructure (#4) — Integration with issue
- **How to check:** Datadog UI → Infrastructure → Hosts → click a node → check "Integrations" column for warning/error icons
- **Expected answer:** `redisdb` — check if the Redis integration on the host shows a connectivity or config issue

### APM — SLO (#22–26)
- **How to verify #22–24:** Datadog UI → Service Level Objectives → find `frontend` SLO, check target % (99.9%), type (Metric), and bad events metric name (`frontend.metrics.checkout.error`)
- **How to verify #25:** SLO Monitor definition shows log query: `service:frontend env:ctf status:error "failed to charge card"`
- **How to verify #26:** Run the log query above, open a log entry, copy the full `message` field
  - After our dd-trace fix the message should be: `failed to complete the order: rpc error: code = Internal desc = failed to charge card: could not charge the card: rpc error: code = Unknown desc = Credit cards with an expiration year of 2025 are not accepted. The flag is "bits"`
  - The `"bits"` flag is now embedded in the message itself — update expected answer if needed

### APM Profiler (#41–43)
- **How to verify #41:** Datadog UI → APM → Profiles → filter `service:responseservice version:v1.0.0` → CPU flamegraph → top function is `count`
- **How to verify #42:** Same but `version:v2.0.1` → top function is `read`
- **How to verify #43:** Use Profile Comparison between v1.0.0 and v2.0.1 → CPU difference should be ~1.2s

### Security (#44–46, #54, #56–59)
- **#44–46 (CVE):** Datadog UI → Software Catalog → select the Python-language service (likely `chatbot-api`) → Security tab → look for HIGH severity CVE `CVE-2024-6345` with original score `7.5`
- **#54 (EC2):** Datadog UI → Cloud Security → Posture Management or Infrastructure → filter for EC2 with elevated privileges tag
- **#56 (attack endpoint):** App & API Protection → Signals → top attacked endpoint is `POST /api/login`
- **#57 (business logic):** App & API Protection → Business Logic → recommended custom signal: `users.login.success`
- **#58 (tool):** In attack signals, check `User-Agent` or tool identifier → `Zgrab`
- **#59 (DB query service during attack):** Trace the attack signal through APM → service executing DB query is `cartservice-redis`

### DBM (#60–62)
- **#60 (login query):** Datadog UI → Database Monitoring → Query Samples → filter `host:postgres db:swagstoredb` → look for `SELECT username, password FROM public.users WHERE (username = ?) ORDER BY username LIMIT ?`
  - This matches the SQL in `src/frontend/main.go` loginHandler (vulnerable string format query)
- **#61 (execution plan):** Click on the query → Execution Plan → the highest-cost node is `Index Scan`
- **#62 (index name):** Same execution plan detail → index name: `users_username_key`

### Troubleshooting Login (#63–66)
- **#63 (longest RUM event):** RUM → Session Explorer → find a login session → Timeline → longest event is `click on Logイン on page /login`
- **#64 (endpoint called):** Same session timeline → click triggers `POST /api/login`
- **#65 (slow DB query):** DBM correlated from RUM session → most time-consuming: `LOCK TABLE public.users IN EXCLUSIVE MODE`
  - This is implemented in `src/frontend/main.go` loginHandler (line ~344) and loginAPIHandler (line ~698)
- **#66 (wait event group):** DBM query plan → wait event: `Lock` (the SELECT is blocked by the EXCLUSIVE lock)
