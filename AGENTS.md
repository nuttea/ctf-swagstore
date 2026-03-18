# AGENTS.md — ctf-swagstore

Microservices demo app (Online Boutique fork) instrumented with Datadog APM, RUM, AppSec, and Code Origin, deployed to GKE via Skaffold + Kustomize.

## Service Languages

| Service | Language |
|---|---|
| frontend, checkoutservice, productcatalogservice, shippingservice | Go |
| paymentservice, currencyservice | Node.js |
| emailservice, recommendationservice, attack-simulator, loadgenerator | Python |
| cartservice | .NET |
| adservice | Java |
| chatbot-api, chatbot-embedder | Python / Go |

## Deployment

**Always deploy via `./deploy.sh`** — never run `kubectl apply -k .` standalone.

```bash
./deploy.sh --default-repo=gcr.io/datadog-ese-sandbox --platform=linux/amd64
```

`deploy.sh` does three things in order:
1. Creates/updates the `git-info` ConfigMap (`DD_GIT_COMMIT_SHA`, `DD_GIT_REPOSITORY_URL`)
2. Runs `skaffold run` — builds changed images (tagged by short SHA via `gitCommit/AbbrevCommitSha`), deploys via Kustomize with proper image name substitution
3. Aliases every built image as `:latest` in `gcr.io/datadog-ese-sandbox`

Raw `kubectl apply -k .` skips Skaffold's image substitution and causes `ImagePullBackOff` (bare names like `adservice` resolve to Docker Hub, not GCR).

## Datadog Configuration

All Datadog env vars for running pods are injected via a single Kustomize patch:

```
kubernetes-manifests/patches/git-info-envvars.yaml
```

This patch targets every `Deployment` with label `tags.datadoghq.com/service` and injects:
- `DD_GIT_COMMIT_SHA` / `DD_GIT_REPOSITORY_URL` — from the `git-info` ConfigMap (Code Origin)
- `DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true`
- `DD_APPSEC_ENABLED=true`

To add a new Datadog env var to all services, add it to this patch file — not to individual manifests.

## AppSec — Go Services Require a Build Tag

Go services must be compiled with `-tags appsec` for AppSec to be active. This is already set in each Go service's `Dockerfile`:

```dockerfile
RUN ... go build -tags appsec -gcflags="${SKAFFOLD_GO_GCFLAGS}" -o /go/bin/frontend .
```

Do not remove `-tags appsec` from Go Dockerfiles.

## Key Files

| File | Purpose |
|---|---|
| `skaffold.yaml` | Build artifacts, tag policy (`gitCommit/AbbrevCommitSha`), Kustomize deploy |
| `deploy.sh` | Deployment wrapper (ConfigMap → skaffold run → :latest alias) |
| `kubernetes-manifests/kustomization.yaml` | Lists all manifests + applies the Datadog patch |
| `kubernetes-manifests/patches/git-info-envvars.yaml` | Shared Datadog env var patch |
