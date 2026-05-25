# Project 04 — CI/CD Pipeline with GitHub Actions

## What This Project Does

Automates the full build → test → push → deploy cycle.
Every push to `main` branch automatically:
1. Runs tests inside a Docker container
2. Builds the production image
3. Pushes to Docker Hub
4. Deploys to your VPS

## Architecture

```
git push main
      ↓
GitHub Actions (runs in GitHub's cloud)
      ↓
┌─────────────────────────────────────────┐
│  Job 1: test                            │
│    docker compose -f docker-compose.test.yml up  │
│    pytest runs inside container         │
│    Reports uploaded as artifacts        │
└─────────────────────────────────────────┘
      ↓ (only if tests pass)
┌─────────────────────────────────────────┐
│  Job 2: build-and-push                  │
│    docker build                         │
│    docker push → Docker Hub             │
└─────────────────────────────────────────┘
      ↓ (only on main branch)
┌─────────────────────────────────────────┐
│  Job 3: deploy                          │
│    SSH into VPS                         │
│    docker pull                          │
│    docker compose up -d --no-deps app   │
└─────────────────────────────────────────┘
```

## Setup (One Time)

### Step 1 — Add GitHub Secrets

In your GitHub repo: Settings → Secrets and variables → Actions → New secret

Add these secrets:

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (Settings → Security → Access Tokens) |
| `VPS_HOST` | Your server's IP address |
| `VPS_SSH_KEY` | Your private SSH key (`cat ~/.ssh/id_rsa`) |

### Step 2 — Add workflow file to your repo

Copy `.github/workflows/deploy.yml` from this project into your app repo.

### Step 3 — Push to main

```bash
git add .
git commit -m "Add CI/CD pipeline"
git push origin main
```

Go to GitHub → Actions tab to watch the pipeline run.

## Files in This Project

```
04-cicd-pipeline/
├── .github/
│   └── workflows/
│       └── deploy.yml        ← the pipeline definition
├── docker-compose.test.yml   ← compose file for running tests in CI
└── README.md
```
