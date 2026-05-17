# Docker Cheat Sheet

## Images

```bash
docker images                        # list all local images
docker pull <image>:<tag>            # download image from registry
docker rmi <image>                   # remove image
docker image prune                   # remove all dangling images
docker image prune -a                # remove all unused images
docker inspect <image>               # full details about an image
docker history <image>               # show image layers
```

## Containers

```bash
docker run <image>                   # create + start container
docker run -it <image> bash          # interactive shell
docker run -d <image>                # run in background (detached)
docker run --rm <image>              # auto-remove container when it stops
docker run --name myapp <image>      # give container a name
docker run -p 8080:80 <image>        # map host port 8080 → container port 80
docker run -e KEY=VALUE <image>      # set environment variable
docker run -v myvolume:/app <image>  # mount a named volume
docker run -v $(pwd):/app <image>    # bind mount current directory

docker ps                            # list running containers
docker ps -a                         # list all containers (including stopped)
docker stop <id>                     # graceful stop (sends SIGTERM)
docker kill <id>                     # force stop (sends SIGKILL)
docker start <id>                    # start a stopped container
docker restart <id>                  # restart a container
docker rm <id>                       # remove a stopped container
docker rm -f <id>                    # force remove (even if running)
docker container prune               # remove all stopped containers

docker exec -it <id> bash            # open shell in running container
docker logs <id>                     # view container logs
docker logs -f <id>                  # follow logs (like tail -f)
docker inspect <id>                  # full details about a container
docker stats                         # live resource usage (CPU, RAM)
docker top <id>                      # processes inside a container
docker cp <id>:/path ./local         # copy file from container to host
```

## Building Images

```bash
docker build .                       # build from Dockerfile in current dir
docker build -t myapp:1.0 .          # build with a tag
docker build -f Dockerfile.prod .    # use specific Dockerfile
docker build --no-cache .            # build without using cache
```

## Networking

```bash
docker network ls                    # list networks
docker network create mynet          # create a custom bridge network
docker network inspect mynet         # details about a network
docker run --network mynet <image>   # attach container to network
```

## Volumes

```bash
docker volume ls                     # list volumes
docker volume create myvol           # create a named volume
docker volume inspect myvol          # details about a volume
docker volume rm myvol               # remove a volume
docker volume prune                  # remove all unused volumes
```

## Docker Compose

```bash
docker compose up                    # start all services
docker compose up -d                 # start in background
docker compose down                  # stop and remove containers
docker compose down -v               # also remove volumes
docker compose logs -f               # follow logs for all services
docker compose ps                    # list service containers
docker compose exec <service> bash   # shell into a service
docker compose build                 # rebuild images
docker compose pull                  # pull latest images
```

## System Cleanup

```bash
docker system df                     # disk usage
docker system prune                  # remove all unused resources
docker system prune -a               # aggressive cleanup (removes all unused images)
```
