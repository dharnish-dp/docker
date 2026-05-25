#!/bin/bash
# deploy.sh — Automated deployment script
#
# Usage: ./deploy.sh <version> <server_ip>
# Example: ./deploy.sh 1.2 192.168.1.100
#
# What it does:
# 1. Builds new image on your Mac
# 2. Pushes to Docker Hub
# 3. SSHes into server
# 4. Pulls new image
# 5. Restarts only the app container (DB stays up)

set -e  # exit immediately if any command fails

# ── Configuration ─────────────────────────────────────────────────
DOCKER_USERNAME="yourusername"        # ← change this
IMAGE_NAME="my-fastapi"
VERSION=${1:-"latest"}               # first argument or "latest"
SERVER_IP=${2:-"YOUR_SERVER_IP"}     # second argument

# ── Build ─────────────────────────────────────────────────────────
echo "Building image $IMAGE_NAME:$VERSION ..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME:$VERSION .
docker tag $DOCKER_USERNAME/$IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:latest

# ── Push ──────────────────────────────────────────────────────────
echo "Pushing to Docker Hub ..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME:latest

# ── Deploy ────────────────────────────────────────────────────────
echo "Deploying to server $SERVER_IP ..."
ssh root@$SERVER_IP << EOF
  cd ~/app

  # Update the version in .env
  sed -i "s/APP_VERSION=.*/APP_VERSION=$VERSION/" .env

  # Pull new image
  docker pull $DOCKER_USERNAME/$IMAGE_NAME:$VERSION

  # Restart only the app service (not DB, not Redis)
  docker compose up -d --no-deps app

  # Wait for health check to pass
  echo "Waiting for app to be healthy..."
  sleep 15

  # Verify deployment
  docker compose ps
  echo "Deployment complete!"
EOF

echo "✅ Deployed $IMAGE_NAME:$VERSION successfully"
