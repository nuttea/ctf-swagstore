module github.com/GoogleCloudPlatform/microservices-demo/src/frontend

go 1.23.0

toolchain go1.24.3

// toolchain go1.24.3

require (
	cloud.google.com/go/compute/metadata v0.7.0
	cloud.google.com/go/profiler v0.4.2
	github.com/golang/protobuf v1.5.4
	github.com/google/uuid v1.6.0
	github.com/gorilla/mux v1.8.1
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.9.3
	go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc v0.61.0
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.61.0
	go.opentelemetry.io/otel v1.36.0
	// go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.11.2
	go.opentelemetry.io/otel/sdk v1.36.0
	golang.org/x/net v0.40.0
	google.golang.org/grpc v1.72.1
	gopkg.in/DataDog/dd-trace-go.v1 v1.74.0
)

require (
	cloud.google.com/go v0.116.0 // indirect
	cloud.google.com/go/auth v0.11.0 // indirect
	cloud.google.com/go/auth/oauth2adapt v0.2.6 // indirect
	github.com/DataDog/appsec-internal-go v1.11.2 // indirect
	github.com/DataDog/datadog-agent/pkg/obfuscate v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/remoteconfig/state v0.64.2 // indirect
	github.com/DataDog/datadog-go/v5 v5.6.0 // indirect
	github.com/DataDog/go-tuf v1.1.0-0.5.2 // indirect
	github.com/DataDog/gostackparse v0.7.0 // indirect
	github.com/DataDog/sketches-go v1.4.7 // indirect
	github.com/Microsoft/go-winio v0.6.2 // indirect
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/dustin/go-humanize v1.0.1 // indirect
	github.com/ebitengine/purego v0.8.3 // indirect
	github.com/felixge/httpsnoop v1.0.4 // indirect
	github.com/go-logr/logr v1.4.2 // indirect
	github.com/go-logr/stdr v1.2.2 // indirect
	github.com/golang/groupcache v0.0.0-20210331224755-41bb18bfe9da // indirect
	github.com/google/pprof v0.0.0-20250403155104-27863c87afa6 // indirect
	github.com/google/s2a-go v0.1.8 // indirect
	github.com/googleapis/enterprise-certificate-proxy v0.3.4 // indirect
	github.com/googleapis/gax-go/v2 v2.14.0 // indirect
	github.com/grpc-ecosystem/grpc-gateway/v2 v2.26.3 // indirect
	github.com/outcaste-io/ristretto v0.2.3 // indirect
	github.com/philhofer/fwd v1.1.3-0.20240916144458-20a13a1f6b7c // indirect
	github.com/richardartoul/molecule v1.0.1-0.20240531184615-7ca0df43c0b3 // indirect
	github.com/secure-systems-lab/go-securesystemslib v0.9.0 // indirect
	github.com/spaolacci/murmur3 v1.1.0 // indirect
	github.com/tinylib/msgp v1.2.5 // indirect
	go.opencensus.io v0.24.0 // indirect
	go.opentelemetry.io/auto/sdk v1.1.0 // indirect
	//go.opentelemetry.io/otel/exporters/otlp/internal/retry v1.11.2 // indirect
	//go.opentelemetry.io/otel/exporters/otlp/otlpmetricgrpc v0.43.0 // indirect
	//go.opentelemetry.io/otel/exporters/otlp/otlptracegrpc v1.36.0 // indirect
	go.opentelemetry.io/otel/metric v1.36.0 // indirect
	go.opentelemetry.io/otel/trace v1.36.0 // indirect
	go.opentelemetry.io/proto/otlp v1.6.0 // indirect
	go.uber.org/atomic v1.11.0 // indirect
	golang.org/x/crypto v0.38.0 // indirect
	golang.org/x/oauth2 v0.27.0 // indirect
	golang.org/x/sync v0.14.0 // indirect
	golang.org/x/sys v0.33.0 // indirect
	golang.org/x/text v0.25.0 // indirect
	golang.org/x/time v0.11.0 // indirect
	golang.org/x/xerrors v0.0.0-20231012003039-104605ab7028 // indirect
	google.golang.org/api v0.210.0 // indirect
	google.golang.org/genproto v0.0.0-20241118233622-e639e219e697 // indirect
	google.golang.org/genproto/googleapis/api v0.0.0-20250519155744-55703ea1f237 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20250519155744-55703ea1f237 // indirect
	google.golang.org/protobuf v1.36.6 // indirect
)

require go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.36.0

require (
	github.com/DataDog/datadog-agent/comp/core/tagger/origindetection v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/proto v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/trace v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/util/log v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/util/scrubber v0.64.2 // indirect
	github.com/DataDog/datadog-agent/pkg/version v0.64.2 // indirect
	github.com/DataDog/dd-trace-go/contrib/google.golang.org/grpc/v2 v2.0.0 // indirect
	github.com/DataDog/dd-trace-go/contrib/gorilla/mux/v2 v2.0.0 // indirect
	github.com/DataDog/dd-trace-go/contrib/net/http/v2 v2.0.0 // indirect
	github.com/DataDog/dd-trace-go/instrumentation/testutils/grpc/v2 v2.0.0 // indirect
	github.com/DataDog/dd-trace-go/v2 v2.0.0 // indirect
	github.com/DataDog/go-libddwaf/v3 v3.5.4 // indirect
	github.com/DataDog/go-runtime-metrics-internal v0.0.4-0.20250319104955-81009b9bad14 // indirect
	github.com/DataDog/go-sqllexer v0.1.3 // indirect
	github.com/DataDog/opentelemetry-mapping-go/pkg/otlp/attributes v0.26.0 // indirect
	github.com/Masterminds/semver/v3 v3.3.1 // indirect
	github.com/cenkalti/backoff/v5 v5.0.2 // indirect
	github.com/cihub/seelog v0.0.0-20170130134532-f561c5e57575 // indirect
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/eapache/queue/v2 v2.0.0-20230407133247-75960ed334e4 // indirect
	github.com/go-ole/go-ole v1.3.0 // indirect
	github.com/go-viper/mapstructure/v2 v2.2.1 // indirect
	github.com/gogo/protobuf v1.3.2 // indirect
	github.com/json-iterator/go v1.1.12 // indirect
	github.com/lufia/plan9stats v0.0.0-20250317134145-8bc96cf8fc35 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	github.com/planetscale/vtprotobuf v0.6.1-0.20240319094008-0393e58bdf10 // indirect
	github.com/pmezard/go-difflib v1.0.1-0.20181226105442-5d4384ee4fb2 // indirect
	github.com/power-devops/perfstat v0.0.0-20240221224432-82ca36839d55 // indirect
	github.com/puzpuzpuz/xsync/v3 v3.5.1 // indirect
	github.com/shirou/gopsutil/v4 v4.25.3 // indirect
	github.com/stretchr/testify v1.10.0 // indirect
	github.com/tklauser/go-sysconf v0.3.15 // indirect
	github.com/tklauser/numcpus v0.10.0 // indirect
	github.com/yusufpapurcu/wmi v1.2.4 // indirect
	go.opentelemetry.io/collector/component v1.27.0 // indirect
	go.opentelemetry.io/collector/pdata v1.27.0 // indirect
	go.opentelemetry.io/collector/pdata/pprofile v0.121.0 // indirect
	go.opentelemetry.io/collector/semconv v0.123.0 // indirect
	go.opentelemetry.io/otel/exporters/otlp/otlptrace v1.36.0 // indirect
	go.uber.org/multierr v1.11.0 // indirect
	go.uber.org/zap v1.27.0 // indirect
	golang.org/x/exp v0.0.0-20250210185358-939b2ce775ac // indirect
	golang.org/x/mod v0.24.0 // indirect
	gopkg.in/ini.v1 v1.67.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)
