#!/usr/bin/env bash
# deploy.sh — Skaffold deploy wrapper for ctf-swagstore
#
# Injects Datadog Code Origin env vars (DD_GIT_COMMIT_SHA, DD_GIT_REPOSITORY_URL)
# into the cluster via a "git-info" ConfigMap before running skaffold.
# All arguments are forwarded verbatim to `skaffold run`.
#
# Usage:
#   ./deploy.sh --default-repo=gcr.io/datadog-ese-sandbox --tag=latest --platform=linux/amd64
#
# Note: Skaffold v3 does not support pre-deploy hooks on DeployConfig, so this
# script acts as the hook runner.

set -euo pipefail

# ── 1. Create / update the git-info ConfigMap ──────────────────────────────
COMMIT_SHA=$(git rev-parse HEAD)
REPO_URL="https://github.com/nuttea/ctf-swagstore"

echo "▶ Updating git-info ConfigMap (SHA: ${COMMIT_SHA})"
kubectl create configmap git-info \
  --from-literal=DD_GIT_COMMIT_SHA="${COMMIT_SHA}" \
  --from-literal=DD_GIT_REPOSITORY_URL="${REPO_URL}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── 2. Run skaffold with all forwarded arguments ────────────────────────────
echo "▶ Running: skaffold run $*"
skaffold run "$@"
