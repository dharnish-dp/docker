# Project 03 — Deploy to a Real Server

## What This Project Does

Takes the Project 02 app and deploys it to a real Linux server (VPS).
Covers the full deployment workflow: push image → SSH to server → pull → run.

## Prerequisites

- Completed Project 02
- A VPS (any of these work):
  - DigitalOcean Droplet — $6/month, easiest for beginners
  - Hetzner CX11 — €4/month, best value in Europe
  - AWS EC2 t2.micro — free tier available
  - Any Ubuntu 22.04 VPS

## Architecture

```
Your Mac                 Docker Hub              Production VPS
────────────            ────────────────        ─────────────────────
docker build    ──────▶  myapp:1.0      ──────▶  docker pull
docker push              (registry)              docker compose up
                                                 Nginx (SSL)
                                                 FastAPI
                                                 PostgreSQL
                                                 Redis
```

---

## Step 1 — Push Your Image to Docker Hub

```bash
# Login to Docker Hub (create account at hub.docker.com if needed)
docker login

# Tag your image with your Docker Hub username
# Replace "yourusername" with your actual Docker Hub username
docker tag my-fastapi:1.0 yourusername/my-fastapi:1.0

# Push to Docker Hub (publicly accessible)
docker push yourusername/my-fastapi:1.0
```

---

## Step 2 — Set Up the VPS

### On DigitalOcean / Hetzner:
1. Create a new Droplet/Server: Ubuntu 22.04, cheapest plan
2. Add your SSH public key during setup
3. Note the server's IP address

### SSH into your server:

```bash
ssh root@YOUR_SERVER_IP
```

### Install Docker on the server:

```bash
# Update package list
apt-get update

# Install Docker's official GPG key and repository
curl -fsSL https://get.docker.com | sh

# Start Docker daemon
systemctl enable docker
systemctl start docker

# Verify Docker is running
docker --version
```

---

## Step 3 — Deploy the App

### Copy files to server:

```bash
# From your Mac — copy the production compose file to the server
scp docker-compose.prod.yml root@YOUR_SERVER_IP:~/app/docker-compose.yml
scp .env.prod root@YOUR_SERVER_IP:~/app/.env
scp nginx/nginx.prod.conf root@YOUR_SERVER_IP:~/app/nginx.conf
```

### On the server — start the app:

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# Navigate to app directory
cd ~/app

# Pull the latest image
docker pull yourusername/my-fastapi:1.0

# Start everything
docker compose up -d

# Check status
docker compose ps
docker compose logs app
```

---

## Step 4 — Add SSL with Let's Encrypt (HTTPS)

SSL is free using Certbot + Let's Encrypt.
You need a domain name pointing to your server's IP first.

### Point your domain to the server:
Add an A record in your domain's DNS: `api.yourdomain.com` → `YOUR_SERVER_IP`

### Get SSL certificate (on the server):

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
certbot --nginx -d api.yourdomain.com

# Auto-renewal (certbot adds this automatically)
certbot renew --dry-run  # test that renewal works
```

---

## Step 5 — Update Deployment (Zero Downtime)

When you have a new version:

```bash
# On your Mac — build and push new version
docker build -t yourusername/my-fastapi:1.1 .
docker push yourusername/my-fastapi:1.1

# On the server — pull new image and restart
ssh root@YOUR_SERVER_IP
cd ~/app
docker pull yourusername/my-fastapi:1.1
docker compose up -d --no-deps app  # restart only the app container
```

`--no-deps` = only restart the specified service, not its dependencies (DB stays up).

---

## Files in This Project

```
03-deploy-to-vps/
├── docker-compose.prod.yml  ← production Compose (uses registry image)
├── nginx/
│   └── nginx.prod.conf      ← production Nginx with SSL
├── .env.prod.example        ← production env vars template
├── deploy.sh                ← automated deployment script
└── README.md
```

---

## Monitoring Your Server

```bash
# Watch container resource usage live
docker stats

# View all logs in one stream
docker compose logs -f

# Check disk usage
docker system df

# Clean up old images (saves disk space)
docker image prune -a
```
