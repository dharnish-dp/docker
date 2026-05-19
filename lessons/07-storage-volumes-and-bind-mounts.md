# Lesson 07 — Storage: Volumes & Bind Mounts

## Goal
Persist data beyond container lifecycle and share files between your Mac
and containers. Understand when to use each storage type.

---

## The Problem

Containers are ephemeral. When deleted, everything inside is gone.

```
docker run python:3.11-slim sh -c "echo 'data' > /tmp/data.txt"  ← writes file
# container deleted
docker run python:3.11-slim sh -c "cat /tmp/data.txt"            ← file gone
# cat: /tmp/data.txt: No such file or directory
```

This is catastrophic for databases, logs, user uploads. You need storage
that survives container deletion.

---

## Three Storage Types

```
┌─────────────────────────────────────────────────────┐
│                    Your Mac                         │
│                                                     │
│  /Users/ddp/myapp  ←── Bind Mount (you control)    │
│  Docker storage    ←── Named Volume (Docker manages)│
│  RAM               ←── tmpfs (memory only)          │
└─────────────────────────────────────────────────────┘
             ↕ mounted into container at a path
┌─────────────────────────────────────────────────────┐
│  Container: /data  or  /app  or any path you choose │
└─────────────────────────────────────────────────────┘
```

| Type | Managed by | Lives on | Survives deletion | Use case |
|---|---|---|---|---|
| Named Volume | Docker | Docker's Linux VM | ✅ Yes | Databases, persistent data |
| Bind Mount | You | Your Mac folder | ✅ Yes | Local dev, live code reload |
| tmpfs | Docker | RAM only | ❌ No | Secrets, temp data |

---

## 1. Named Volumes

Docker manages everything — where data lives, permissions, lifecycle.
You only use the volume name.

### Create a volume
```bash
docker volume create mydata
```

### Mount it into a container
```bash
docker run -v mydata:/data python:3.11-slim sh -c "echo 'hello' > /data/file.txt"
#          ↑              ↑
#     volume name    path inside container
```

### Data survives container deletion
```bash
# Container 1: writes data, gets deleted (--rm)
docker run --rm -v mydata:/data python:3.11-slim sh -c "echo 'important data' > /data/data.txt"

# Container 2: brand new, mounts same volume — data is there
docker run --rm -v mydata:/data python:3.11-slim sh -c "cat /data/data.txt"
# output: important data  ✅
```

### Inspect a volume
```bash
docker volume inspect mydata
```
```json
{
  "Driver": "local",
  "Mountpoint": "/var/lib/docker/volumes/mydata/_data",
  "Scope": "local"
}
```
Data lives inside Docker's Linux VM. Docker manages it — never touch
this path directly.

### Remove a volume
```bash
docker volume rm mydata    ← PERMANENT. All data destroyed. Irreversible.
```
Docker refuses if any container is currently using the volume.

---

## 2. Bind Mounts

Mount a folder from your Mac directly into the container. Both see the
same files in real time. No rebuild needed when files change.

```bash
docker run -v ~/Desktop/docker/my-first-image:/app python:3.11-slim sh -c "ls /app"
#          ↑                               ↑
#    your Mac path               path inside container
```

### Live code reload — the dev superpower

```
1. Run container with bind mount (once)
2. Edit code on Mac in your IDE
3. Container immediately sees the change — no rebuild, no restart
```

**Proof:**
```bash
# Edit file on Mac
echo 'print("bind mount works!")' >> app.py

# Container reads updated file instantly
docker run --rm -v ~/Desktop/myapp:/app python:3.11-slim sh -c "tail -1 /app/app.py"
# output: print("bind mount works!")  ✅
```

### Bind mount vs Named volume

| | Named Volume | Bind Mount |
|---|---|---|
| Path control | Docker decides | You decide |
| Real-time sync | ✅ | ✅ |
| Production safe | ✅ Yes | ❌ No (ties to host path) |
| Dev workflow | ❌ Inconvenient | ✅ Perfect |

---

## 3. tmpfs

Mounts in RAM only. Never written to disk. Gone when container stops.

```bash
docker run --tmpfs /secrets python:3.11-slim sh -c "echo 'token' > /secrets/token.txt"
```

Use for secrets, session tokens, credentials that must never touch disk.

---

## Volume Syntax — Two Forms

```bash
# Named volume
-v mydata:/data

# Bind mount (absolute path or ~)
-v /Users/ddp/myapp:/app
-v ~/myapp:/app
-v $(pwd):/app          ← current directory (most common in dev)
```

`$(pwd)` is the most useful pattern — mount whatever directory you're
currently in:

```bash
cd ~/Desktop/docker/my-first-image
docker run --rm -v $(pwd):/app python:3.11-slim sh -c "ls /app"
```

---

## Key Commands

```bash
docker volume create <name>        # create a named volume
docker volume ls                   # list all volumes
docker volume inspect <name>       # details — mountpoint, driver
docker volume rm <name>            # delete volume (permanent, irreversible)
docker volume prune                # delete all unused volumes

docker run -v <volume>:<path>      # mount named volume
docker run -v <host-path>:<path>   # bind mount
docker run --tmpfs <path>          # tmpfs mount
```

---

## Check Your Understanding — Q&A

### Q1. What is the difference between a named volume and a bind mount?

**Answer:**
- **Named volume** — Docker manages location, used for production data
  persistence. Data survives container deletion. Path is inside Docker's
  Linux VM — you never access it directly.
- **Bind mount** — you specify an exact Mac folder, mounted directly into
  the container. Both Mac and container see the same files in real time.
  Used for dev workflows (live code reload). Not for production.

---

### Q2. You delete a container that was using a named volume. Is the data gone?

**Answer:** No. Named volumes have an independent lifecycle from containers.
The volume and its data survive container deletion. The data is only deleted
when you explicitly run `docker volume rm` — which is permanent and irreversible.

---

### Q3. You're developing a Python automation script. Which storage type should you use and why?

**Answer:** Bind mount with `$(pwd):/app`. Mount your project folder into
the container so you can edit code in your IDE on Mac and run it inside the
container instantly — no rebuild loop. Named volumes are for persistent data
(databases), not code.

---

### Q4. What does `-v $(pwd):/app` mean?

**Answer:** Mount the current directory on your Mac into `/app` inside the
container. `$(pwd)` expands to the absolute path of whatever directory your
terminal is currently in. This is the most common pattern for local development
— run it from your project folder and the container gets your project files live.
