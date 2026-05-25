# What Comes After Docker — Complete Learning Roadmap

## Where You Stand Now

You have completed full Docker mastery:
- Images, containers, registries
- Dockerfile writing and optimization
- Layer caching and BuildKit
- Networking, storage, security
- Docker Compose
- Production patterns
- Real-world projects

This puts you at the level of most senior developers.
The gap between here and a DevOps / Platform / SRE engineer is three things:

```
Docker (done ✅) → Kubernetes → Cloud → Observability
```

---

## The Big Picture

```
LEVEL 1 — You Are Here
  Docker            Package and run apps in containers

LEVEL 2 — Next
  Kubernetes        Orchestrate containers across many servers
  Cloud (AWS/GCP)   Where those servers actually live

LEVEL 3 — After That
  Terraform         Define all infrastructure as code
  Observability     Monitor, log, trace everything

LEVEL 4 — Advanced
  GitOps / ArgoCD   Deployments triggered by git, not humans
  Service Mesh      Istio / Linkerd for microservice networking
  Platform Eng      Build internal tools that other teams use
```

---

## Technology 1 — Kubernetes (K8s)

### What It Is
Kubernetes is a system that runs and manages containers across multiple servers.
Docker Compose manages containers on 1 machine.
Kubernetes manages containers on 10, 100, or 1000 machines.

### Why Learn It First
- Direct extension of Docker — uses the same images you already build
- Highest job market demand of any DevOps technology
- Everything else (Helm, ArgoCD, Istio) builds on top of it
- Required for any serious production workload

### What Docker Can't Do That K8s Can

| Problem | Docker Compose | Kubernetes |
|---|---|---|
| Container crashes at 3am | Stays dead until someone restarts it | Auto-restarts on any healthy node |
| Traffic spike hits your app | Manual scale up | Automatically adds more pods |
| Deploy new version | Brief downtime | Zero-downtime rolling deployment |
| The server dies | Everything on that server is gone | Reschedules all containers on other nodes |
| Running on 10 servers | 10 separate Compose files | One config file, runs on all 10 |

### Key Concepts to Learn

```
Pod           → smallest unit — 1 or more containers that share network/storage
Deployment    → manages replicas of your app (e.g. run 3 copies of my API)
Service       → stable DNS + load balancing between pods
Ingress       → handles external traffic into the cluster (like Nginx)
ConfigMap     → non-secret configuration (env vars, config files)
Secret        → sensitive config (passwords, API keys)
Namespace     → isolation between teams or environments
Node          → a physical/virtual server in the cluster
Cluster       → the collection of all nodes
Helm          → package manager for K8s (like pip, but for K8s apps)
```

### The Relationship Between Docker and K8s

```
You write:     Dockerfile  →  docker build  →  image
K8s runs:      image inside a Pod, managed by a Deployment
               exposed via a Service
               accessed via an Ingress
```

Your Docker knowledge is the foundation. K8s is the orchestration layer on top.

### How to Start

```bash
# Install minikube — runs a local K8s cluster on your Mac
brew install minikube
minikube start

# Install kubectl — the CLI for Kubernetes (like docker CLI for Docker)
brew install kubectl

# Your first K8s deployment
kubectl create deployment hello --image=nginx
kubectl expose deployment hello --port=80 --type=NodePort
minikube service hello   # opens in browser
```

### Certifications Worth Getting
- **CKA** (Certified Kubernetes Administrator) — industry gold standard
- **CKAD** (Certified Kubernetes Application Developer) — for developers
- Both are hands-on exams, not multiple choice

### Best Free Resource
TechWorld with Nana — Kubernetes full course on YouTube.
Best structured K8s content available, completely free.

### Time to Learn
- 4-6 weeks to be productive
- 3-6 months to be confident
- Ongoing to master

---

## Technology 2 — Cloud Platform (AWS Recommended)

### What It Is
Kubernetes runs somewhere. That somewhere is a cloud provider.
AWS, GCP, and Azure all offer managed Kubernetes — you get the cluster
without managing the servers yourself.

### Why AWS First
- Largest market share (32% of cloud market)
- Most job postings require AWS knowledge
- Managed K8s = EKS (Elastic Kubernetes Service)
- Free tier available for learning

### Key AWS Services for Container Engineers

| AWS Service | What it does | Docker/K8s equivalent |
|---|---|---|
| ECS | Run containers without managing K8s | Docker Compose on a managed platform |
| EKS | Managed Kubernetes | K8s without managing the control plane |
| ECR | Private container registry | Docker Hub (private) |
| RDS | Managed PostgreSQL/MySQL | Postgres container (but with backups, failover) |
| ElastiCache | Managed Redis | Redis container |
| ALB | Application Load Balancer | Nginx + ingress |
| Secrets Manager | Managed secrets | Docker secrets + rotation |
| CloudWatch | Logs + metrics + alerts | Grafana + Loki |

### Why Not Run Your Own K8s on a VPS
Running K8s yourself means managing the control plane (etcd, API server,
scheduler) — complex and fragile. Managed K8s (EKS/GKE/AKS) gives you
the cluster already running. You just deploy your apps.

### Certification Worth Getting
**AWS Solutions Architect Associate** — most recognised cloud cert.
Many companies pay for this. Opens significantly higher salary bands.

### Time to Learn
- 2-3 months for practical fluency
- 1 month focused study for the SAA certification

---

## Technology 3 — Terraform (Infrastructure as Code)

### What It Is
Terraform lets you define your entire infrastructure — servers, databases,
networks, DNS, SSL — as code in `.tf` files. Run `terraform apply` and it
builds everything exactly as defined.

### Why Learn It
```
Without Terraform:
  SSH into server → run commands → hope you remember what you did
  New server → repeat everything manually → slightly different every time

With Terraform:
  Write .tf files → terraform apply → identical infrastructure every time
  Reviewed in PRs → version controlled → reproducible → destroyable
```

### What You Define as Code
- EC2 servers / Kubernetes clusters
- VPCs, subnets, security groups (networking)
- RDS databases, ElastiCache (Redis)
- Load balancers, DNS records
- SSL certificates
- IAM roles and permissions

### Example

```hcl
# Create an EC2 server in AWS — defined as code
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"   # Ubuntu 22.04
  instance_type = "t2.micro"

  tags = {
    Name = "my-app-server"
  }
}
```

Run `terraform apply` → server exists in AWS.
Run `terraform destroy` → server is gone.
Commit to git → teammates can create identical infrastructure.

### Time to Learn
3-4 weeks to be productive.

---

## Technology 4 — Observability (Monitoring, Logging, Tracing)

### What It Is
When something breaks in production, observability tells you what happened,
where, and why — before the customer calls you.

### Three Pillars

```
Logs    → what happened
         Tool: Grafana Loki, ELK Stack (Elasticsearch + Logstash + Kibana)
         Docker connection: containers already log to stdout — you just collect it

Metrics → how the system is performing (CPU, memory, request rate, error rate)
         Tool: Prometheus (collection) + Grafana (dashboards)
         Docker connection: expose /metrics endpoint from your FastAPI app

Traces  → where time is spent inside a single request (which function was slow)
         Tool: Jaeger, OpenTelemetry
         Docker connection: add tracing library to your app
```

### The Grafana Stack (Industry Standard)

```
App → stdout logs → Grafana Loki → Grafana dashboards
App → /metrics   → Prometheus   → Grafana dashboards
App → traces     → Jaeger       → Grafana dashboards
```

All three visualised in one Grafana interface.
All three can run in containers (Docker Compose / Kubernetes).

### Why It Matters
Every production system needs this. An app with no observability is flying blind.
When something breaks, you have no way to debug it except SSH and hope.

### Time to Learn
3-4 weeks for basics, ongoing to master.

---

## Technology 5 — GitOps / ArgoCD

### What It Is
GitOps means: the state of your production system is defined entirely in git.
You never SSH into a server and run docker pull. Instead:

```
Developer pushes to git
      ↓
CI/CD builds and pushes image
      ↓
ArgoCD detects the new image
      ↓
ArgoCD automatically deploys it to Kubernetes
```

### Why It Matters
- Every deployment is a git commit — full audit trail
- Easy rollback: revert the git commit, ArgoCD reverts the deployment
- No human touching production servers directly
- Industry standard for K8s deployments

### Time to Learn
2-3 weeks after learning K8s.

---

## For Automation Engineers Specifically

Your Python + automation background opens a specific niche that is
highly valuable and undersupplied:

### Test Infrastructure Engineering

```
What you already know:  Python + Selenium + Docker
What you add:           Kubernetes + Cloud

Result: Run 500 browser tests in parallel on Kubernetes
        Each test gets its own pod with Chrome
        Tests finish in 2 minutes instead of 3 hours
        Infrastructure auto-scales down to zero when tests aren't running
```

### Platform Engineering
Build internal tools that other developers use:
- Automated environment provisioning (dev spins up test env with one command)
- Containerized test data management
- CI/CD pipelines with automated test gates
- Internal Kubernetes deployment tooling

This niche pays very well — most people know testing OR infrastructure,
rarely both. You will know both.

---

## Recommended Learning Order

```
Month 1-2   Kubernetes
            → Start with minikube locally
            → Deploy your Docker projects to K8s
            → Learn kubectl, Deployments, Services, Ingress

Month 2-3   Cloud (AWS)
            → Create an AWS account (free tier)
            → Deploy your K8s app to EKS
            → Learn ECR, RDS, ALB
            → Study for AWS SAA certification

Month 3-4   Terraform
            → Define your AWS infrastructure as code
            → Version control your infrastructure
            → Destroy and recreate environments with one command

Month 4-5   Observability
            → Add Prometheus + Grafana to your K8s cluster
            → Set up Grafana Loki for logs
            → Build dashboards for your apps

Month 5-6   ArgoCD / GitOps
            → Automate K8s deployments from git
            → Implement blue/green deployments
            → Set up full GitOps workflow
```

---

## Summary — Why This Order

```
Kubernetes first  → directly extends Docker, highest market value
Cloud second      → K8s needs infrastructure to run on
Terraform third   → manage that infrastructure as code
Observability     → see what your production systems are doing
GitOps last       → automate everything, touch nothing manually
```

Each step builds on the previous one.
Docker was the foundation — everything above runs on top of containers.

---

## Resources

| Technology | Best Free Resource |
|---|---|
| Kubernetes | TechWorld with Nana — Kubernetes full course (YouTube) |
| AWS | AWS official free training at skill.aws |
| Terraform | HashiCorp official tutorials at developer.hashicorp.com |
| Observability | Grafana Labs official tutorials at grafana.com/tutorials |
| GitOps | ArgoCD official getting started guide |

---

## Where to Go From Here

Complete the 5 Docker projects in `exercises/` first — they cover:
- Containerized Selenium (automation engineering)
- FastAPI + PostgreSQL + Redis (full stack)
- VPS deployment (real server)
- CI/CD pipeline (GitHub Actions)
- Data pipeline (scheduled scraper)

Once those are done, start Kubernetes with the same apps you already have.
You already have the Docker images — deploying to K8s is the natural next step.
