#!/bin/bash
# Zgrab2 Network Scan Script for Datadog AAP Testing

TARGET=${1:-"frontend"}
PORT=${2:-"80"}

echo "🔍 Starting Zgrab2 scan against $TARGET:$PORT"

# HTTP scan
echo "$TARGET" | zgrab2 http -p $PORT --timeout 5s --output-file /tmp/zgrab_http_results.json

echo "✅ Zgrab2 HTTP scan completed"

# TLS/HTTPS scan (if port 443)
if [ "$PORT" == "443" ]; then
    echo "$TARGET" | zgrab2 tls -p $PORT --timeout 5s --output-file /tmp/zgrab_tls_results.json
    echo "✅ Zgrab2 TLS scan completed"
fi

echo "📊 Scan results saved"






