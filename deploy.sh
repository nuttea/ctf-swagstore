#!/usr/bin/env bash
# deploy.sh — ctf-swagstore Skaffold deploy wrapper
#
# • No --tag flag needed: skaffold.yaml uses gitCommit/AbbreviatedTags,
#   so Skaffold automatically computes <short-sha> (or <short-sha>-dirty)
#   and skips building images that already exist with that tag → change detection.
# • After `skaffold run`, every built image is also aliased as :latest in
#   the registry using `docker buildx imagetools create` (no layer download).
# • Creates/updates the "git-info" ConfigMap for Datadog Code Origin.
#
# Usage:
#   ./deploy.sh --default-repo=gcr.io/datadog-ese-sandbox --platform=linux/amd64
#   ./deploy.sh --default-repo=gcr.io/datadog-ese-sandbox --platform=linux/amd64 -m loadgenerator

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO="gcr.io/datadog-ese-sandbox"
REPO_URL="https://github.com/nuttea/ctf-swagstore"

# All images defined in skaffold.yaml (main app + loadgenerator)
IMAGES=(
  emailservice
  productcatalogservice
  recommendationservice
  shippingservice
  checkoutservice
  paymentservice
  currencyservice
  cartservice
  frontend
  adservice
  responseservice-v1
  responseservice-v2
  attack-simulator
  loadgenerator
)

# ── Compute tag — must match Skaffold's AbbreviatedTags variant ───────────────
SHORT_SHA=$(git rev-parse --short HEAD)
# Replicate Skaffold's -dirty suffix (ignoreChanges defaults to false)
if ! git diff --quiet HEAD 2>/dev/null; then
  SHORT_SHA="${SHORT_SHA}-dirty"
fi
FULL_SHA=$(git rev-parse HEAD)

echo "▶ Git SHA: ${SHORT_SHA} (full: ${FULL_SHA})"

# ── 1. Create / update the git-info ConfigMap ─────────────────────────────────
echo "▶ Updating git-info ConfigMap"
kubectl create configmap git-info \
  --from-literal=DD_GIT_COMMIT_SHA="${FULL_SHA}" \
  --from-literal=DD_GIT_REPOSITORY_URL="${REPO_URL}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── 2. skaffold run — no --tag flag, gitCommit handles change detection ────────
echo "▶ Running: skaffold run $*"
skaffold run "$@"

# ── 3. Alias every image as :latest (registry-side, no layer download) ─────────
# `docker buildx imagetools create` creates a new manifest pointing to the
# same digest — nothing is pulled or pushed by layer.
echo "▶ Aliasing images as :latest (SHA: ${SHORT_SHA})"
for img in "${IMAGES[@]}"; do
  src="${REPO}/${img}:${SHORT_SHA}"
  dst="${REPO}/${img}:latest"
  if docker buildx imagetools create -t "${dst}" "${src}" 2>/dev/null; then
    echo "  ✓ ${img}:latest → ${SHORT_SHA}"
  else
    echo "  ⚠ ${img}: not found at ${SHORT_SHA}, skipping :latest alias"
  fi
done

echo "✅ Deploy complete (SHA: ${SHORT_SHA})"
