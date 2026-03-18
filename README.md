<p align="center">
<!-- <img src="src/frontend/static/icons/Hipster_HeroLogoCyan.svg" width="300" alt="Online Boutique" /> -->
<img src="src/frontend/static/icons/Swagstore-Logo.svg" width="300" alt="Swagstore" />
</p>

## Release 0.5.0 - multiarch (amd and arm support)
## Dec 2022

<!-- ![Continuous Integration](https://github.com/GoogleCloudPlatform/microservices-demo/workflows/Continuous%20Integration%20-%20Main/Release/badge.svg) -->

**Swagstore** is a fork of [Google Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) which in turn is a cloud-first microservices demo application.

The app consists of an 11-tier microservices application. The application is a
web-based e-commerce app where users can browse items,
add them to the cart, and purchase them.
Swagstore is a slightly modified version from the original [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo). In fact, items on the Swagstore are actually Datadog swags.
It is a ficticious ecommerce swag store, don't expect to receive swags :grinning:

**Google uses this application to demonstrate use of technologies like
Kubernetes/GKE, Istio, Stackdriver, and gRPC**. This application
works on any Kubernetes cluster, as well as Google
Kubernetes Engine. It’s **easy to deploy with little to no configuration**.

**At Datadog we use the app to experiment with APM, Tracing Libraries, Admission Controller and auto injection.
It is perfect as a playground if you want to play and instrument the microservices written in multiple languages.**

If you’re using this demo, please **★Star** this repository to show your interest!

<!-- > 👓**Note to Googlers:** Please fill out the form at
> [go/microservices-demo](http://go/microservices-demo) if you are using this
> application. -->

## Screenshots

| Home Page                                                                                                         | Checkout Screen                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [![Screenshot of store homepage](./docs/img/online-boutique-frontend-1.png)](./docs/img/online-boutique-frontend-1.png) | [![Screenshot of checkout screen](./docs/img/online-boutique-frontend-2.png)](./docs/img/online-boutique-frontend-2.png) |

<!-- ## Quickstart (GKE)

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/GoogleCloudPlatform/microservices-demo&cloudshell_workspace=.&cloudshell_tutorial=docs/cloudshell-tutorial.md)

1. **[Create a Google Cloud Platform project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project)** or use an existing project. Set the `PROJECT_ID` environment variable and ensure the Google Kubernetes Engine and Cloud Operations APIs are enabled.

```
PROJECT_ID="<your-project-id>"
gcloud services enable container.googleapis.com --project ${PROJECT_ID}
```

2. **Clone this repository.**

```
git clone https://github.com/GoogleCloudPlatform/microservices-demo.git
cd microservices-demo
```

3. **Create a GKE cluster.**

- GKE autopilot mode (see [Autopilot
overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
to learn more):

```
REGION=us-central1
gcloud container clusters create-auto onlineboutique \
    --project=${PROJECT_ID} --region=${REGION}
```

- GKE Standard mode:

```
ZONE=us-central1-b
gcloud container clusters create onlineboutique \
    --project=${PROJECT_ID} --zone=${ZONE} \
    --machine-type=e2-standard-2 --num-nodes=4
```

4. **Deploy the sample app to the cluster.**

```
kubectl apply -f ./release/kubernetes-manifests.yaml
```

5. **Wait for the Pods to be ready.**

```
kubectl get pods
```

After a few minutes, you should see:

```
NAME                                     READY   STATUS    RESTARTS   AGE
adservice-76bdd69666-ckc5j               1/1     Running   0          2m58s
cartservice-66d497c6b7-dp5jr             1/1     Running   0          2m59s
checkoutservice-666c784bd6-4jd22         1/1     Running   0          3m1s
currencyservice-5d5d496984-4jmd7         1/1     Running   0          2m59s
emailservice-667457d9d6-75jcq            1/1     Running   0          3m2s
frontend-6b8d69b9fb-wjqdg                1/1     Running   0          3m1s
loadgenerator-665b5cd444-gwqdq           1/1     Running   0          3m
paymentservice-68596d6dd6-bf6bv          1/1     Running   0          3m
productcatalogservice-557d474574-888kr   1/1     Running   0          3m
recommendationservice-69c56b74d4-7z8r5   1/1     Running   0          3m1s
redis-cart-5f59546cdd-5jnqf              1/1     Running   0          2m58s
shippingservice-6ccc89f8fd-v686r         1/1     Running   0          2m58s
```

7. **Access the web frontend in a browser** using the frontend's `EXTERNAL_IP`.

```
kubectl get service frontend-external | awk '{print $4}'
```

*Example output - do not copy*

```
EXTERNAL-IP
<your-ip>
```

**Note**- you may see `<pending>` while GCP provisions the load balancer. If this happens, wait a few minutes and re-run the command.

8. [Optional] **Clean up**:

```
gcloud container clusters delete onlineboutique \
    --project=${PROJECT_ID} --zone=${ZONE}
```

## Use Terraform to provision a GKE cluster and deploy Online Boutique

The [`/terraform` folder](terraform) contains instructions for using [Terraform](https://www.terraform.io/intro) to replicate the steps from [**Quickstart (GKE)**](#quickstart-gke) above.

## Other deployment variations

- **Istio**: [See these instructions.](docs/service-mesh.md)
- **Anthos Service Mesh**: [See these instructions](/docs/service-mesh.md)
- **non-GKE clusters (Minikube, Kind)**: see the [Development Guide](/docs/development-guide.md)

## Deploy Online Boutique variations with Kustomize

The [`/kustomize` folder](kustomize) contains instructions for customizing the deployment of Online Boutique with different variations such as:
* integrating with [Google Cloud Operations](kustomize/components/google-cloud-operations/)
* replacing the in-cluster Redis cache with [Google Cloud Memorystore (Redis)](kustomize/components/memorystore) or [Google Cloud Spanner](kustomize/components/spanner)
* etc. -->

## Architecture

**Swagstore** is composed of 11 microservices written in different
languages that talk to each other over gRPC. See the [Development Principles](/docs/development-principles.md) doc for more information.

[![Architecture of
microservices](./docs/img/architecture-diagram.png)](./docs/img/architecture-diagram.png)

Find **Protocol Buffers Descriptions** at the [`./pb` directory](./pb).

| Service                                              | Language      | Description                                                                                                                       |
| ---------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [frontend](./src/frontend)                           | Go            | Exposes an HTTP server to serve the website. Does not require signup/login and generates session IDs for all users automatically. |
| [cartservice](./src/cartservice)                     | C#            | Stores the items in the user's shopping cart in Redis and retrieves it.                                                           |
| [productcatalogservice](./src/productcatalogservice) | Go            | Provides the list of products from a JSON file and ability to search products and get individual products.                        |
| [currencyservice](./src/currencyservice)             | Node.js       | Converts one money amount to another currency. Uses real values fetched from European Central Bank. It's the highest QPS service. |
| [paymentservice](./src/paymentservice)               | Node.js       | Charges the given credit card info (mock) with the given amount and returns a transaction ID.                                     |
| [shippingservice](./src/shippingservice)             | Go            | Gives shipping cost estimates based on the shopping cart. Ships items to the given address (mock)                                 |
| [emailservice](./src/emailservice)                   | Python        | Sends users an order confirmation email (mock).                                                                                   |
| [checkoutservice](./src/checkoutservice)             | Go            | Retrieves user cart, prepares order and orchestrates the payment, shipping and the email notification.                            |
| [recommendationservice](./src/recommendationservice) | Python        | Recommends other products based on what's given in the cart.                                                                      |
| [adservice](./src/adservice)                         | Java          | Provides text ads based on given context words.                                                                                   |
| [loadgenerator](./src/loadgenerator)                 | Python/Locust | Continuously sends requests imitating realistic user shopping flows to the frontend.                                              |
| [responseservice-v1](./src/responseservice/responseservice-v1) | Go   | CTF challenge service demonstrating Datadog Continuous Profiler. Runs a CPU-heavy bubble sort (O(n²)) on each request.          |
| [responseservice-v2](./src/responseservice/responseservice-v2) | Go   | Optimised version of responseservice using stdlib sort (O(n log n)). Used to compare profiling data against v1.                 |

## responseservice — Datadog Continuous Profiler CTF Challenge

`responseservice` is a pair of Go HTTP services (`v1` and `v2`) designed as a **CTF (Capture the Flag) challenge** to demonstrate [Datadog Continuous Profiler](https://docs.datadoghq.com/profiler/).

Both versions listen on port `8080` and respond `"Hello World!"` to every request. On each request they also execute a CPU-intensive computation: they read a binary dataset (`./data/input.txt` containing `0`s and `1`s), sort it, and count the number of `1`s.

### The performance regression to find

| Version | Sort algorithm | Complexity |
| ------- | -------------- | ---------- |
| **v1**  | Manual bubble sort (nested loops) | O(n²) |
| **v2**  | `sort.Ints()` from Go stdlib | O(n log n) |

v1 deliberately uses an inefficient bubble sort, causing high CPU usage that is clearly visible in Datadog Profiler flame graphs. The CTF challenge is to:

1. Deploy both versions to Kubernetes simultaneously.
2. Use **Datadog Continuous Profiler** to observe elevated CPU in `responseservice` `v1.0.0` vs `v2.0.0`.
3. Drill into the flame graph to identify `count()` → bubble sort as the root cause.

Both services are instrumented with `dd-trace-go` APM tracing and CPU/Heap profiling, and emit Unified Service Tagging labels (`DD_ENV`, `DD_SERVICE`, `DD_VERSION`) so traces and profiles are automatically correlated in Datadog.

### Building & deploying responseservice

```bash
# Mac Apple Silicon (arm64)
skaffold build --default-repo=gcr.io/datadog-ese-sandbox --platform=linux/arm64

# x86 / Intel / AMD64
skaffold build --default-repo=gcr.io/datadog-ese-sandbox --platform=linux/amd64

# Deploy manifests
kubectl apply -f kubernetes-manifests/responseservice/
```

## Features

- **[Kubernetes](https://kubernetes.io)/[GKE](https://cloud.google.com/kubernetes-engine/):**
  The app is designed to run on Kubernetes (both locally on "Docker for
  Desktop", as well as on the cloud with GKE).
- **[gRPC](https://grpc.io):** Microservices use a high volume of gRPC calls to
  communicate to each other.
- **[Istio](https://istio.io):** Application works on Istio service mesh.
- **[Cloud Operations (Stackdriver)](https://cloud.google.com/products/operations):** Many services
  are instrumented with **Profiling**, **Tracing** and **Debugging**. In
  addition to these, using Istio enables features like Request/Response
  **Metrics** and **Context Graph** out of the box. When it is running out of
  Google Cloud, this code path remains inactive.
- **[Skaffold](https://skaffold.dev):** Application
  is deployed to Kubernetes with a single command using Skaffold.
- **Synthetic Load Generation:** The application demo comes with a background
  job that creates realistic usage patterns on the website using
  [Locust](https://locust.io/) load generator.
  
  
## Skaffold Build & Push

Use `skaffold build` to build all container images and push them to your registry. Three flags control the most common options:

| Flag | Description |
| ---- | ----------- |
| `--default-repo` | Registry prefix prepended to every image name |
| `--tag` | Image tag applied to all built images (overrides `tagPolicy` in `skaffold.yaml`) |
| `--platform` | Target CPU architecture for the built image |

### Mac Apple Silicon (arm64)

```bash
skaffold build \
  --default-repo=gcr.io/datadog-ese-sandbox \
  --tag=latest \
  --platform=linux/arm64
```

### x86 / Intel / AMD64

```bash
skaffold build \
  --default-repo=gcr.io/datadog-ese-sandbox \
  --tag=latest \
  --platform=linux/amd64
```

### Build a specific image only

```bash
skaffold build \
  --default-repo=gcr.io/datadog-ese-sandbox \
  --tag=latest \
  --platform=linux/amd64 \
  --build-image=responseservice-v1
```

### Force rebuild (skip image cache)

By default Skaffold caches images and skips rebuilding if the source hasn't changed (`Found. Tagging` / `Found Remotely`). Add `--cache-artifacts=false` to bypass the cache and always build fresh:

```bash
# Force rebuild all images
skaffold build \
  --default-repo=gcr.io/datadog-ese-sandbox \
  --tag=latest \
  --platform=linux/amd64 \
  --cache-artifacts=false
```

```bash
# Force rebuild a single image (e.g. loadgenerator)
skaffold build \
  --default-repo=gcr.io/datadog-ese-sandbox \
  --tag=latest \
  --platform=linux/amd64 \
  --build-image=loadgenerator \
  --cache-artifacts=false
```

After a force rebuild you may need to restart the running pods to pull the new image:

```bash
kubectl rollout restart deployment/<service-name>
```

> **Tip:** Authenticate Docker to GCR before pushing:
> ```bash
> gcloud auth configure-docker gcr.io
> ```

---

## Deploy Swagstore Demo app

Do you have a running K8s cluster? If not either use Docker Desktop or Minikube or Kind or your K8s cluster or your GKE

Don't forget to install Git, Skaffold 2.0+ and kubectl. Check the prerequisites section above.

Launch a local Kubernetes cluster with one of the following tools:

## Option 1 - Local Cluster 

1. Launch a local Kubernetes cluster with one of the following tools:

    - To launch **Minikube** (tested with Ubuntu Linux). Please, ensure that the
       local Kubernetes cluster has at least:
        - 4 CPUs
        - 4.0 GiB memory
        - 32 GB disk space

      ```shell
      minikube start --cpus=4 --memory 4096 --disk-size 32g
      ```

    - To launch **Docker for Desktop** (tested with Mac/Windows). Go to Preferences:
        - choose “Enable Kubernetes”,
        - set CPUs to at least 3, and Memory to at least 6.0 GiB
        - on the "Disk" tab, set at least 32 GB disk space

    - To launch a **Kind** cluster:

      ```shell
      kind create cluster
      ```

2. Run `kubectl get nodes` to verify you're connected to the respective control plane.

3. Run `skaffold run` (first time will be slow, it can take ~20 minutes).
   This will build and deploy the application. If you need to rebuild the images
   automatically as you refactor the code, run `skaffold dev` command.
   
   
	**Change the platform and default-repo to match your machine and registry.**

	Mac Apple Silicon (M1/M2/M3 — arm64):

	  `skaffold run --default-repo=gcr.io/datadog-ese-sandbox --tag=latest --platform=linux/arm64`

	x86 / Intel Mac / AMD64:

	  `skaffold run --default-repo=gcr.io/datadog-ese-sandbox --tag=latest --platform=linux/amd64`

   > **Note:** The above commands deploy the main app only. The `loadgenerator` is a separate Skaffold config and must be deployed explicitly (it starts with `replicas: 0` — scale up when ready):
   >
   > ```bash
   > skaffold run -m loadgenerator --default-repo gcr.io/datadog-ese-sandbox --platform=linux/amd64
   > ```
   >
   > Then scale up to start generating traffic:
   > ```bash
   > kubectl scale deployment loadgenerator --replicas=1
   > ```
   >
   > To stop traffic generation without deleting the deployment:
   > ```bash
   > kubectl scale deployment loadgenerator --replicas=0
   > ```

4. Run `kubectl get pods` to verify the Pods are ready and running.

5. Docker Desktop should automatically provide the frontend at http://localhost:80
6. Minikube requires you to run a command to access the frontend service:
`minikube service frontend-external`
7. Kind does not provision an IP address for the service. You must run a port-forwarding process to access the frontend at http://localhost:8080:
`kubectl port-forward deployment/frontend 8080:8080` to forward a port to the frontend service.
9. Navigate to either http://localhost:80 or http://localhost:8080 to access the web frontend.


## Cleanup

If you've deployed the application with `skaffold run` command, you can run
`skaffold delete` to clean up the deployed resources.

  
## Option 2: Google Kubernetes Engine (GKE)

> 💡 Recommended if you're using Google Cloud Platform and want to try it on
> a realistic cluster. **Note**: If your cluster has Workload Identity enabled, 
> [see these instructions](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity#enable)

1.  Create a Google Kubernetes Engine cluster and make sure `kubectl` is pointing
    to the cluster.

    ```sh
    gcloud services enable container.googleapis.com
    ```

    ```sh
    gcloud container clusters create demo --enable-autoupgrade \
        --enable-autoscaling --min-nodes=3 --max-nodes=10 --num-nodes=5 --zone=us-central1-a
    ```

    ```
    kubectl get nodes
    ```

2.  Enable Google Container Registry (GCR) on your GCP project and configure the
    `docker` CLI to authenticate to GCR:

    ```sh
    gcloud services enable containerregistry.googleapis.com
    ```

    ```sh
    gcloud auth configure-docker -q
    ```

3.  In the root of this repository, run `skaffold run --default-repo=gcr.io/[PROJECT_ID]`,
    where [PROJECT_ID] is your GCP project ID.

    This command:

    - builds the container images
    - pushes them to GCR
    - applies the `./kubernetes-manifests` deploying the application to
      Kubernetes.

    **Troubleshooting:** If you get "No space left on device" error on Google
    Cloud Shell, you can build the images on Google Cloud Build: [Enable the
    Cloud Build
    API](https://console.cloud.google.com/flows/enableapi?apiid=cloudbuild.googleapis.com),
    then run `skaffold run -p gcb --default-repo=gcr.io/[PROJECT_ID]` instead.

4.  Find the IP address of your application, then visit the application on your
    browser to confirm installation.

        kubectl get service frontend-external

## Local Development

If you would like to contribute features or fixes to this app, see the [Development Guide](/docs/development-guide.md) on how to build this demo locally.

## Demos featuring Online Boutique

- [Seamlessly encrypt traffic from any apps in your Mesh to Memorystore (redis)](https://medium.com/google-cloud/64b71969318d)
- [From edge to mesh: Exposing service mesh applications through GKE Ingress](https://cloud.google.com/architecture/exposing-service-mesh-apps-through-gke-ingress)
- [Take the first step toward SRE with Cloud Operations Sandbox](https://cloud.google.com/blog/products/operations/on-the-road-to-sre-with-cloud-operations-sandbox)
- [Deploying the Online Boutique sample application on Anthos Service Mesh](https://cloud.google.com/service-mesh/docs/onlineboutique-install-kpt)
- [Anthos Service Mesh Workshop: Lab Guide](https://codelabs.developers.google.com/codelabs/anthos-service-mesh-workshop)
- [KubeCon EU 2019 - Reinventing Networking: A Deep Dive into Istio's Multicluster Gateways - Steve Dake, Independent](https://youtu.be/-t2BfT59zJA?t=982)
- Google Cloud Next'18 SF
  - [Day 1 Keynote](https://youtu.be/vJ9OaAqfxo4?t=2416) showing GKE On-Prem
  - [Day 3 Keynote](https://youtu.be/JQPOPV_VH5w?t=815) showing Stackdriver
    APM (Tracing, Code Search, Profiler, Google Cloud Build)
  - [Introduction to Service Management with Istio](https://www.youtube.com/watch?v=wCJrdKdD6UM&feature=youtu.be&t=586)
- [Google Cloud Next'18 London – Keynote](https://youtu.be/nIq2pkNcfEI?t=3071)
  showing Stackdriver Incident Response Management

---

This is not an official Google project.
