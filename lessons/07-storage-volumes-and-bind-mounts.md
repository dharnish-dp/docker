# Lesson 07 — Storage: Volumes & Bind Mounts

## Goal
Persist data beyond container lifecycle and share files between your Mac
and containers. Understand when to use each storage type.

## Prerequisites
Lesson 02 — Core Building Blocks (ephemeral containers)

## After This Lesson You Will Be Able To
- Persist database data across container restarts using named volumes
- Mount your project folder into a container for live code reload (no rebuild)
- Choose the right storage type for any situation
- Use `$(pwd)` bind mount pattern for local development

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

## Volume Syntax — All Forms

```bash
# Named volume
-v mydata:/data

# Named volume — read-only (container cannot write to it)
-v mydata:/data:ro

# Bind mount (absolute path or ~)
-v /Users/ddp/myapp:/app
-v ~/myapp:/app
-v $(pwd):/app          ← current directory (most common in dev)

# Bind mount — read-only (container can read but not modify your Mac files)
-v $(pwd):/app:ro
```

**Read-only volumes** (`:ro`) are important for security — if a container
is compromised, it cannot modify your source files or corrupt your data.

`$(pwd)` is the most useful pattern — mount whatever directory you're
currently in:

```bash
cd ~/Desktop/docker/my-first-image
docker run --rm -v $(pwd):/app python:3.11-slim sh -c "ls /app"
```

---

## Command Reference — Every Command Explained

---

### `docker volume create mydata`

```
docker volume create  → create a named volume managed by Docker
mydata                → name of the volume (you choose this)
                        Returns the volume name on success
                        Docker allocates storage in its Linux VM
                        You never interact with the storage path directly
```

---

### `docker volume ls`

```
docker volume ls  → list all named volumes on your machine
Output columns:
  DRIVER    → "local" = stored on this machine's disk
  VOLUME NAME → the name you gave it (or auto-generated if unnamed)
```

---

### `docker volume inspect mydata`

```
docker volume inspect  → show full JSON details of a volume
mydata                 → volume name
Key fields:
  "Mountpoint" → actual path on disk inside Docker's Linux VM
                 (e.g. /var/lib/docker/volumes/mydata/_data)
                 You cannot access this path from macOS directly
  "Driver"     → "local" = stored on this machine
  "CreatedAt"  → when the volume was created
  "Scope"      → "local" = this machine only
```

---

### `docker volume rm mydata`

```
docker volume rm  → permanently delete a volume and ALL its data
mydata            → volume name
                    PERMANENT AND IRREVERSIBLE — no recycle bin
                    FAILS if any container (running or stopped) is using it
                    Remove containers first: docker rm <container>
```

---

### `docker volume prune`

```
docker volume prune  → delete ALL volumes not currently used by any container
                       Asks for confirmation (y/N)
                       "Unused" = no running OR stopped container references it
                       Use for cleanup after docker compose down -v
```

---

### `docker run -v mydata:/data python:3.11-slim`

```
-v mydata:/data    → mount the named volume "mydata" at path /data inside container
                    Left side  = volume name OR absolute Mac path
                    Right side = path inside the container
                    If volume doesn't exist → Docker creates it automatically
                    Any writes to /data inside container → saved to the volume
```

---

### `docker run -v $(pwd):/app python:3.11-slim`

```
-v $(pwd):/app     → bind mount: mount current Mac directory into container at /app
$(pwd)             → shell expansion: replaced with the absolute path of current dir
                    e.g. if you're in /Users/ddp/myproject → /Users/ddp/myproject:/app
:/app              → where to mount it inside the container
                    Files are NOT copied — they are the same files, shared live
```

---

### `docker run --rm -v mydata:/data python:3.11-slim sh -c "echo 'hello' > /data/file.txt"`

```
--rm               → delete container when it exits
-v mydata:/data    → mount the volume at /data
sh -c "..."        → run a shell and execute the quoted command
                    Needed because we chain multiple shell commands with > and &&
echo 'hello'       → print "hello" to stdout
> /data/file.txt   → redirect stdout to a file (creates or overwrites)
                    This write goes to the volume, survives container deletion
```

---

### `docker run --tmpfs /tmp myimage`

```
--tmpfs /tmp       → create a RAM filesystem at /tmp inside the container
                    Writable: container can read and write here
                    Temporary: contents exist only in RAM, lost when container stops
                    Never on disk: nothing is ever written to the host's storage
                    Multiple: --tmpfs /tmp --tmpfs /var/log --tmpfs /run
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
