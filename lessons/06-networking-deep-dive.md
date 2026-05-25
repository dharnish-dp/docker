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

## Practical Exercises — Run These Yourself

These exercises prove every networking concept with real commands.
Run them in order — each one builds on the previous.

---

### Practical 1 — Prove Default Bridge Has No DNS

The default `bridge` network does NOT support container name DNS.
Let's prove it by trying to ping one container from another by name.

**Step 1 — Start two containers on the DEFAULT bridge (no --network flag):**

```bash
# Terminal 1: start a long-running container named "container-a"
docker run -d --name container-a python:3.11-slim sleep 300

# Terminal 2: start another container and try to reach container-a by name
docker run --rm python:3.11-slim python -c "
import socket
try:
    ip = socket.gethostbyname('container-a')
    print(f'Resolved container-a → {ip}')
except socket.gaierror as e:
    print(f'DNS failed: {e}')
"
```

**Expected output:**
```
DNS failed: [Errno -2] Name or service not known
```

DNS resolution failed — containers on the default bridge cannot find each other by name.

**Clean up:**
```bash
docker rm -f container-a
```

---

### Practical 2 — Prove Custom Bridge Has DNS

Same setup but using a custom network. DNS works automatically.

**Step 1 — Create a custom network:**
```bash
docker network create demo-network
```

**Step 2 — Start container-a on the custom network:**
```bash
docker run -d --name container-a --network demo-network python:3.11-slim sleep 300
```

**Step 3 — Try to reach it by name from another container on the same network:**
```bash
docker run --rm --network demo-network python:3.11-slim python -c "
import socket
try:
    ip = socket.gethostbyname('container-a')
    print(f'Resolved container-a → {ip}')
except socket.gaierror as e:
    print(f'DNS failed: {e}')
"
```

**Expected output:**
```
Resolved container-a → 172.18.0.2
```

Same code, same images — only difference is the custom network.
Docker's built-in DNS resolved the container name to its internal IP.

**Clean up:**
```bash
docker rm -f container-a
docker network rm demo-network
```

---

### Practical 3 — Prove Network Isolation

Containers on DIFFERENT networks cannot talk to each other — even on the same machine.
This is isolation working correctly.

**Step 1 — Create two separate networks:**
```bash
docker network create network-a
docker network create network-b
```

**Step 2 — Start a server on network-a:**
```bash
docker run -d --name server-a --network network-a nginx
```

**Step 3 — Try to reach it from a container on network-b:**
```bash
docker run --rm --network network-b python:3.11-slim python -c "
import urllib.request
try:
    urllib.request.urlopen('http://server-a', timeout=3)
    print('Connected!')
except Exception as e:
    print(f'Cannot reach server-a: {e}')
"
```

**Expected output:**
```
Cannot reach server-a: <urlopen error [Errno -2] Name or service not known>
```

`server-a` is invisible from `network-b`. The networks are completely isolated.

**Step 4 — Now connect server-a to network-b as well:**
```bash
# A container can be on multiple networks simultaneously
docker network connect network-b server-a
```

**Step 5 — Try again — now it works:**
```bash
docker run --rm --network network-b python:3.11-slim python -c "
import urllib.request
try:
    resp = urllib.request.urlopen('http://server-a', timeout=3)
    print(f'Connected! Status: {resp.status}')
except Exception as e:
    print(f'Still cannot reach: {e}')
"
```

**Expected output:**
```
Connected! Status: 200
```

`docker network connect` added `server-a` to `network-b` while it was running — no restart needed.

**Clean up:**
```bash
docker rm -f server-a
docker network rm network-a network-b
```

---

### Practical 4 — Port Mapping Proof

Prove that without `-p`, a container's port is invisible from your Mac.
Then prove that with `-p` it becomes accessible.

**Step 1 — Run nginx WITHOUT port mapping:**
```bash
docker run -d --name nginx-no-port nginx
```

**Step 2 — Try to access it from your Mac:**
```bash
curl http://localhost:80
# curl: (7) Failed to connect to localhost port 80: Connection refused
```

Port 80 inside the container is completely invisible to your Mac.

**Step 3 — Run nginx WITH port mapping:**
```bash
docker run -d --name nginx-with-port -p 8080:80 nginx
```

**Step 4 — Now access it:**
```bash
curl http://localhost:8080
# <!DOCTYPE html>  ← nginx default page HTML
```

Same image, same container — the only difference is `-p 8080:80`.

**Step 5 — See the port mapping in docker ps:**
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
# NAMES             PORTS
# nginx-with-port   0.0.0.0:8080->80/tcp
# nginx-no-port     80/tcp              ← no host mapping
```

`0.0.0.0:8080->80/tcp` = any IP on your Mac, port 8080, forwards to container port 80.
`80/tcp` alone = exposed inside Docker network only, not accessible from Mac.

**Clean up:**
```bash
docker rm -f nginx-no-port nginx-with-port
```

---

### Practical 5 — Inspect a Live Network

See exactly what IP each container gets and how Docker DNS works internally.

**Step 1 — Create a network and start two containers:**
```bash
docker network create inspect-demo
docker run -d --name web --network inspect-demo nginx
docker run -d --name api --network inspect-demo python:3.11-slim sleep 300
```

**Step 2 — Inspect the network:**
```bash
docker network inspect inspect-demo
```

Look at the `Containers` section in the output:
```json
"Containers": {
    "abc123...": {
        "Name": "web",
        "IPv4Address": "172.19.0.2/16"
    },
    "def456...": {
        "Name": "api",
        "IPv4Address": "172.19.0.3/16"
    }
}
```

**Step 3 — Verify DNS resolves to those exact IPs:**
```bash
# Check what IP "web" resolves to from inside the "api" container
docker exec api python -c "
import socket
ip = socket.gethostbyname('web')
print(f'web resolves to: {ip}')
"
# web resolves to: 172.19.0.2  ← matches the Containers section above
```

The IP in `docker network inspect` is exactly what Docker DNS returns.
This is how Docker knows where to route `http://web` traffic.

**Clean up:**
```bash
docker rm -f web api
docker network rm inspect-demo
```

---

### Practical 6 — Full Two-Container Communication

The complete real-world pattern: a Python app communicating with a web server
using container names, on a custom network.

**Step 1 — Set up the network and server:**
```bash
docker network create app-network
docker run -d --name webserver --network app-network nginx
```

**Step 2 — Run a Python container that talks to the webserver by name:**
```bash
docker run --rm --network app-network python:3.11-slim python -c "
import urllib.request

# Using container name 'webserver' — not IP address
url = 'http://webserver'
response = urllib.request.urlopen(url)

print(f'Status: {response.status}')
print(f'Connected to: {url}')
print(f'First 50 bytes: {response.read(50)}')
"
```

**Expected output:**
```
Status: 200
Connected to: http://webserver
First 50 bytes: b'<!DOCTYPE html>\n<html>\n<head>\n<title>Welcome to n'
```

No IP address used. No port mapping. Pure container-name DNS.
Traffic stayed entirely inside the virtual network.

**Clean up:**
```bash
docker rm -f webserver
docker network rm app-network
```

---

### Practical 7 — The `host` Network Mode

The `host` network removes all network isolation — the container shares
your Mac's network stack directly. Used for performance-critical scenarios.

```bash
# Run a container with host networking
docker run --rm --network host python:3.11-slim python -c "
import socket
# In host mode, hostname = your Mac's hostname
print(f'Hostname: {socket.gethostname()}')
"
```

On Linux, this would print your actual machine hostname.
On Mac, Docker Desktop's Linux VM hostname appears instead.

**When to use `host`:**
- Performance testing where network overhead matters
- Tools that need to scan the host's network interfaces
- Never for application workloads — always use bridge for apps

---

### Practical 8 — Debugging a Broken Network (Common Real Scenario)

This is the most useful practical — simulating a misconfiguration and fixing it.

**Step 1 — Create the "broken" setup (wrong network):**
```bash
docker network create correct-network
docker network create wrong-network

# Server is on correct-network
docker run -d --name myserver --network correct-network nginx

# Client accidentally started on wrong-network
docker run -d --name myclient --network wrong-network python:3.11-slim sleep 300
```

**Step 2 — Client tries to reach server — fails:**
```bash
docker exec myclient python -c "
import urllib.request
try:
    urllib.request.urlopen('http://myserver', timeout=2)
except Exception as e:
    print(f'Error: {e}')
"
# Error: <urlopen error [Errno -2] Name or service not known>
```

**Step 3 — Debug: inspect both networks:**
```bash
# Check correct-network — should have myserver
docker network inspect correct-network --format '{{range .Containers}}{{.Name}} {{end}}'
# myserver

# Check wrong-network — should have myclient
docker network inspect wrong-network --format '{{range .Containers}}{{.Name}} {{end}}'
# myclient
```

The problem is clear: client and server are on different networks.

**Step 4 — Fix: connect client to the correct network:**
```bash
docker network connect correct-network myclient
```

**Step 5 — Try again — now works:**
```bash
docker exec myclient python -c "
import urllib.request
resp = urllib.request.urlopen('http://myserver', timeout=2)
print(f'Fixed! Status: {resp.status}')
"
# Fixed! Status: 200
```

**The debugging workflow for any networking issue:**
```
1. docker network inspect <network>   → check which containers are connected
2. docker inspect <container>         → check which networks the container is on
3. docker network connect             → add container to missing network
```

**Clean up:**
```bash
docker rm -f myserver myclient
docker network rm correct-network wrong-network
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
