# Lesson 06 — Networking Deep Dive

## Goal
Understand how containers communicate with each other and with the outside
world. Wire containers together correctly without hardcoding IP addresses.

## Prerequisites
Lesson 03 — Under the Hood (net namespace), Lesson 02 — Core Building Blocks

## After This Lesson You Will Be Able To
- Create custom bridge networks and connect containers to them
- Explain why containers use service names instead of IP addresses
- Map container ports to your Mac using `-p`
- Debug container networking failures using `docker network inspect`

---

## The Problem

Each container has its own `net` namespace — its own isolated network stack.
Two containers cannot talk to each other by default. Docker networking is how
you control which containers can talk to which, and how traffic gets in from
the outside.

---

## The Office Building Analogy

```
┌─────────────────────────────────────────┐
│           OFFICE BUILDING (Your Mac)    │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  Room A     │    │  Room B     │    │
│  │  Python App │    │  Database   │    │
│  └─────────────┘    └─────────────┘    │
│                                         │
└─────────────────────────────────────────┘
              │
         Outside World (browser)
```

- Container → Container = talk directly inside the building (no port mapping)
- Mac/Browser → Container = need a door (port mapping with `-p`)

---

## Docker Network Types

| Network | What it does |
|---|---|
| `bridge` | Default. Containers communicate internally + NAT to outside. |
| `host` | Container shares Mac's network stack directly. No isolation. |
| `none` | No network at all. Completely isolated. |
| `overlay` | Multi-host networking. Used by Swarm/Kubernetes. |

You will use `bridge` 95% of the time.

---

## Default Bridge vs Custom Bridge

| | Default bridge | Custom bridge |
|---|---|---|
| Container discovery | By IP only | By container name (DNS) |
| DNS resolution | ❌ No | ✅ Yes |
| Use case | Never in production | Always |

```
Default bridge:   container A → ping 172.17.0.3    ← fragile, IP changes on restart
Custom bridge:    container A → ping my-database    ← reliable, name never changes
```

**Always create a custom network for any multi-container setup.**

---

## Port Mapping — Getting Traffic In

```
docker run -p 8080:80 nginx
           ↑     ↑
           │     └── container port (where app listens inside)
           └──────── host port (what you access on Mac)
```

Open `http://localhost:8080` on Mac → Docker forwards to port 80 in container.

### EXPOSE vs -p

```dockerfile
EXPOSE 80        # documentation only — does NOT open any port
```

```bash
docker run -p 8080:80   # THIS actually opens the port
```

`EXPOSE` is a sticky note. `-p` is the actual door.

---

## How Container-to-Container DNS Works

```
my-network: 172.18.0.0/16
├── Gateway:          172.18.0.1   (Docker's virtual router)
├── webserver(nginx): 172.18.0.2   (listening on port 80)
└── python container: 172.18.0.3   (connects to http://webserver)
```

When Python container says `http://webserver`:
1. Docker DNS resolves `webserver` → `172.18.0.2`
2. Python connects directly to `172.18.0.2:80` inside virtual network
3. Your Mac is never involved — traffic stays inside the virtual network

Port 80 here = the port nginx is **listening on** inside the container.
Not a port mapping — a direct internal connection.

---

## Docker Network Subnet

When you run `docker network create my-network`, Docker automatically assigns
a `/16` subnet (e.g., `172.18.0.0/16`):

- `/16` = 65,534 usable IPs
- `.1` = always the gateway (Docker's virtual router)
- `.2` onwards = assigned to containers

Custom subnet:
```bash
docker network create --subnet 192.168.100.0/24 my-network
# /24 = 254 usable IPs
```

Use a custom subnet to avoid IP conflicts with your office/home network.

---

## Two Traffic Paths — Summary

```
Container → Container:
  Direct internal connection using container name (DNS)
  Port mapping NOT required
  Traffic never leaves the virtual network

Mac/Browser → Container:
  Must use -p flag to map a host port to container port
  Traffic comes from outside the virtual network
  Port mapping IS required
```

---

## Command Reference — Every Command Explained

---

### `docker network ls`

```
docker network ls  → list all Docker networks on your machine
Output columns:
  NETWORK ID → short hash identifier
  NAME       → network name (bridge, host, none are always present)
  DRIVER     → bridge (local virtual switch), host (share Mac network), null (none)
  SCOPE      → local (this machine only) vs swarm (multi-machine cluster)
```

---

### `docker network create my-network`

```
docker network create  → create a new virtual network
my-network             → name you assign (used in --network flag and Compose)
                        Docker auto-assigns a /16 subnet (e.g. 172.18.0.0/16)
                        Returns the full network ID on success
```

---

### `docker network create --subnet 192.168.100.0/24 my-network`

```
--subnet 192.168.100.0/24  → define the IP range for this network manually
                             Format: <network-address>/<prefix-length>
                             /24 = 254 usable IPs (256 - network & broadcast)
                             /16 = 65534 usable IPs (Docker default)
                             Use custom subnet to:
                             - Avoid conflicts with your home/office network
                             - Assign predictable IPs to containers
```

---

### `docker network inspect my-network`

```
docker network inspect  → show full JSON details of a network
my-network              → network name or ID
Key fields in output:
  "Subnet"    → the IP range assigned (e.g. "172.18.0.0/16")
  "Gateway"   → Docker's virtual router IP (always .1, e.g. 172.18.0.1)
  "Containers" → all containers currently attached with their IPs
```

Use this for debugging — if a container is missing from "Containers", it's on the wrong network.

---

### `docker network rm my-network`

```
docker network rm  → permanently delete a network
my-network         → network name or ID
                    FAILS if any containers (running or stopped) are attached
                    Must stop and remove containers first, then remove network
```

---

### `docker run -d --name webserver --network my-network -p 8080:80 nginx`

```
docker run         → create and start a container
-d                 → detached: run in background, print container ID, return terminal
--name webserver   → assign a fixed name (also becomes DNS hostname on custom networks)
                    Without --name: Docker generates a random name (e.g. "naughty_shaw")
--network my-network → attach to this network (enables DNS by container name)
-p 8080:80         → port mapping: Mac port 8080 → container port 80
                    Left side = your Mac, Right side = inside container
nginx              → use the official nginx image
```

---

### `docker run --rm --network my-network python:3.11-slim python -c "..."`

```
--rm               → delete container automatically when it exits
                    No manual docker rm needed
                    Use for one-shot commands you don't need to keep
--network my-network → same network as the service we want to reach
python:3.11-slim   → use this image (already pulled)
python -c "..."    → run a Python one-liner instead of the default CMD
                    -c = "command string" — execute the following as Python code
```

---

### `docker container prune`

```
docker container prune  → remove ALL stopped containers at once
                         Asks for confirmation (y/N)
                         Much faster than docker rm for cleanup
                         Does NOT remove running containers
```

Equivalent to:
```bash
docker rm $(docker ps -aq -f status=exited)
```

---

## Debugging Networking Issues

When two containers can't talk:
1. `docker network inspect <network>` — check both containers appear under `Containers`
2. If a container is missing → it's on the wrong network
3. Check container names match exactly what the code uses
4. Check the port the service is listening on matches what the client connects to

---

## Check Your Understanding — Q&A

### Q1. Why does container-to-container communication not need port mapping?

**Answer:** Both containers are on the same virtual network and can reach each
other directly using internal IPs. Port mapping is only needed for traffic
coming FROM OUTSIDE the Docker network (e.g., your Mac's browser). Inside the
network, containers talk freely — your Mac is not involved at all.

---

### Q2. What is the difference between default bridge and custom bridge?

**Answer:** Default bridge has no DNS — containers can only find each other
by IP address, which changes on every restart. Custom bridge has Docker's
built-in DNS — containers find each other by name, which never changes.
Always use a custom bridge network in any real setup.

---

### Q3. Port 80 appears in `-p 8080:80` and in `http://webserver:80`. Are they the same thing?

**Answer:** Same port number, different meaning:
- In `-p 8080:80` → the destination port inside the container (for external traffic)
- In `http://webserver:80` → the port nginx is listening on (for internal traffic)

Both refer to nginx's listening port 80, but one is a mapping rule for external
access and the other is a direct internal connection.

---

### Q4. What does `docker network inspect` tell you when debugging?

**Answer:** It shows the subnet, gateway IP, and all containers currently
connected to the network with their assigned IPs. If a container is missing
from the `Containers` section, it means it's on the wrong network — that's
the most common cause of container communication failures.
