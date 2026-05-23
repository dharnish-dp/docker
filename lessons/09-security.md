# Lesson 09 — Security

## Goal
Harden containers against the most common attack vectors. This is where
most Docker users have the biggest gaps — and where breaches happen.

## Prerequisites
Lesson 03 — Namespaces & cgroups, Lesson 04 — Dockerfile

## After This Lesson You Will Be Able To
- Run containers as non-root with a proper system user
- Handle secrets correctly without leaking them into images or inspect output
- Drop all Linux capabilities and add back only what's needed
- Apply read-only filesystem with targeted writable mounts
- Use the complete hardened `docker run` command for production

---

## The 5 Most Common Docker Security Mistakes

```
1. Running containers as root
2. Baking secrets into images or environment variables
3. Using bloated base images with unnecessary tools
4. Giving containers more Linux capabilities than they need
5. Writable filesystem when it doesn't need to be
```

---

## Mistake 1 — Running as Root

By default, container processes run as root (UID 0). Verify:

```bash
docker run --rm myimage whoami
# output: root  ← dangerous
```

### The Fix — Non-Root User in Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .

# Create system group and user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Switch to non-root user — all commands after this run as appuser
USER appuser

CMD ["python", "app.py"]
```

**Why USER comes after COPY:** COPY needs to write files. If USER is set
earlier, file ownership may cause permission errors. Always set USER as the
last step before CMD.

Verify the fix:
```bash
docker run --rm myimage whoami
# output: appuser  ✅
```

---

### What Happens When a Non-Root User Tries to Write Files

This is where beginners get stuck. Once you switch to a non-root user,
writing to certain paths fails with a permission error.

**The problem — non-root user writing to a root-owned folder:**

```
PermissionError: [Errno 13] Permission denied: '/app/output.txt'
```

Why? `WORKDIR /app` runs as root, so `/app` is owned by root.
`appuser` has no write permission to a root-owned directory.

**Fix 1 — `chown` the folder before switching user:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Give appuser ownership of /app BEFORE switching to that user
RUN chown -R appuser:appgroup /app

USER appuser
CMD ["python", "app.py"]
```

`chown -R appuser:appgroup /app` — recursively changes ownership of `/app`
and everything inside it. Now `appuser` can read and write inside `/app`.

**Fix 2 — `COPY --chown` to set ownership at copy time (cleaner):**

```dockerfile
FROM python:3.11-slim
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app

# Copy files AND assign ownership in one step — no separate chown needed
COPY --chown=appuser:appgroup requirements.txt .
RUN pip install -r requirements.txt
COPY --chown=appuser:appgroup app.py .

USER appuser
CMD ["python", "app.py"]
```

`COPY --chown=appuser:appgroup` copies the file and sets its owner in one
instruction. This is the cleanest pattern — use this in production.

---

### Linux File Permission Levels in Docker

Every file in Linux has three permission levels:

```
Owner  Group  Others
 rwx    rwx    rwx
  │      │      └── everyone else (r=read, w=write, x=execute)
  │      └───────── the group the file belongs to
  └──────────────── the user who owns the file
```

When you run `ls -la /app` inside a container:

```
drwxr-xr-x  appuser  appgroup  /app/        ← appuser owns, group can read
-rw-r--r--  appuser  appgroup  app.py       ← appuser can write, others read-only
-rw-r--r--  root     root      config.json  ← root-owned, appuser cannot write
```

**Practical rules for non-root containers:**

| File type | Owner | Permission | Why |
|---|---|---|---|
| Files app only reads | `root` | `644` | Readable by all, only root writes |
| Files app writes | `appuser` | `644` | appuser owns, can write |
| Directories app writes into | `appuser` | `755` | appuser can create files inside |

**Useful debug commands:**
```bash
# See ownership of all files in container
docker run --rm myimage ls -la /app

# Check what UID/GID the user has
docker run --rm myimage id
# uid=100(appuser) gid=101(appgroup)

# This UID is what --user 100:101 refers to in docker run
docker run --user 100:101 myimage
```

---

## Mistake 2 — Secrets in Environment Variables

### Why it's dangerous

```bash
# WRONG — secret visible to anyone with docker access
docker run -e DB_PASSWORD=secret123 myimage

# Inspect reveals it in plain text
docker inspect <container> | grep -A 5 "Env"
# "DB_PASSWORD=secret123"  ← fully exposed
```

Same problem with Dockerfile `ENV`:
```dockerfile
ENV DB_PASSWORD=secret123   # WRONG — baked into image forever
```
Visible in `docker history`. If the image is ever pushed to a registry,
the secret is permanently exposed to anyone who pulls it.

### The Fix — Secret Files

```bash
# Create secret file on Mac (never commit to git)
echo "secret123" > /tmp/db_password.txt

# Mount read-only into container at /run/secrets/
docker run --rm \
  -v /tmp/db_password.txt:/run/secrets/db_password:ro \
  myimage
```

```python
# In your Python code — read file, not env var
with open("/run/secrets/db_password") as f:
    password = f.read().strip()
```

The secret is never in the image, never in `docker inspect`. Only the
file path is visible — not the value.

---

### Where the Secret File Lives on Your Mac

When you create a secret file:

```bash
echo "supersecret123" > /tmp/db_password.txt
```

This file lives on your **Mac's filesystem** at `/tmp/db_password.txt`.
`/tmp` on Mac is a real folder — you can open Finder and see it.

When you bind mount it into the container:

```bash
docker run -v /tmp/db_password.txt:/run/secrets/db_password:ro myimage
```

```
Your Mac filesystem:                   Container filesystem:
/tmp/db_password.txt  ←── same file ──→  /run/secrets/db_password
```

The file is NOT copied into the image. It's a live link — the container
reads directly from your Mac's `/tmp/db_password.txt` at runtime.
Remove the file from your Mac and the container can no longer read it.

**Why `/tmp` is only for development:**
`/tmp` is cleared on Mac restart. It's also readable by any process on
your Mac — not truly secure. For production use proper secret stores.

**Recommended locations for secret files in development:**

```bash
# Option 1 — /tmp (simple, cleared on reboot)
echo "secret" > /tmp/myapp_secret.txt

# Option 2 — project folder (keep in .gitignore!)
echo "secret" > ./secrets/db_password.txt
# .gitignore must contain: secrets/

# Option 3 — encrypted file (most secure for dev)
# Use tools like SOPS or age to encrypt secret files
```

**What NOT to do:**
```bash
# NEVER commit secret files to git
git add secrets/  # ← catastrophic — secrets in git history forever

# NEVER put secrets in a file inside the image
COPY secrets/ /app/secrets/  # ← WRONG — baked into image
```

**In production — use a proper secret manager:**

| Tool | How it works |
|---|---|
| Docker Secrets (Swarm) | Encrypted, injected into `/run/secrets/` automatically |
| AWS Secrets Manager | Fetch at runtime via API, never touch disk |
| HashiCorp Vault | Centralized secret storage, fine-grained access control |
| Kubernetes Secrets | Base64 encoded (not encrypted by default — use sealed-secrets) |

### Secret Rules

| Method | Safe? | Why |
|---|---|---|
| `ENV` in Dockerfile | ❌ | Baked into image layer permanently |
| `-e` in docker run | ❌ | Visible in `docker inspect` |
| Secret file mount | ✅ | Not in image, not in inspect |
| Docker secrets (Swarm) | ✅ | Encrypted, only in memory |
| External manager (Vault, AWS SM) | ✅ | Gold standard for production |

---

## Mistake 3 — Bloated Base Images

Every tool in your image is a potential attack vector.

```
python:3.11          → ~1GB    full Debian + everything
python:3.11-slim     → ~236MB  Debian, most tools removed
python:3.11-alpine   → ~60MB   Alpine Linux, minimal
gcr.io/distroless    → ~50MB   NO shell, NO package manager
```

**Distroless** (from Google) = your app + runtime only. No bash, no sh,
no curl. An attacker with code execution has nothing to work with.

```dockerfile
# Multi-stage: build with full image, run with distroless
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --target=/deps -r requirements.txt

FROM gcr.io/distroless/python3
COPY --from=builder /deps /deps
COPY app.py /app/
ENV PYTHONPATH=/deps
CMD ["/app/app.py"]
```

**Tradeoff:** Distroless can't be exec'd into with a shell — harder to
debug. Use `slim` in development, distroless in production.

---

## Mistake 4 — Excessive Linux Capabilities

Containers get 14 Linux capabilities by default. Most apps need zero.

Check default capabilities:
```bash
docker run --rm python:3.11-slim sh -c "cat /proc/self/status | grep CapEff"
# CapEff: 00000000a80425fb  ← 14 capabilities active
```

Default capabilities include:
- `CAP_NET_RAW` — send raw packets (network sniffing)
- `CAP_SYS_CHROOT` — used in container escape attacks
- `CAP_DAC_OVERRIDE` — bypass file permission checks

### Full List of Default Container Capabilities

These 14 capabilities are active in every container by default:

| Capability | What it allows | Risk if abused |
|---|---|---|
| `CHOWN` | Change file ownership | Modify ownership of sensitive files |
| `DAC_OVERRIDE` | Bypass file read/write/execute permission checks | Read any file ignoring permissions |
| `FSETID` | Set setuid/setgid bits on files | Privilege escalation via setuid |
| `FOWNER` | Bypass permission checks when file UID matches | Modify protected files |
| `MKNOD` | Create special device files | Create device files for exploitation |
| `NET_RAW` | Send raw/packet sockets | Sniff network traffic, craft spoofed packets |
| `SETGID` | Manipulate group IDs | Gain group privileges |
| `SETUID` | Manipulate user IDs | Become another user including root |
| `SETFCAP` | Set file capabilities | Grant capabilities to other executables |
| `SETPCAP` | Modify process capabilities | Elevate own capabilities |
| `NET_BIND_SERVICE` | Bind to ports below 1024 | Hijack privileged ports |
| `SYS_CHROOT` | Call chroot() | Escape container filesystem restrictions |
| `KILL` | Send signals to any process | Kill other processes in container |
| `AUDIT_WRITE` | Write audit log entries | Tamper with audit trail |

Most Python automation scripts need **none** of these.

### The Fix — Drop All, Add Back Only What's Needed

```bash
# Drop everything
docker run --cap-drop ALL myimage
# CapEff: 0000000000000000  ← zero capabilities ✅

# Drop all, add back only what's required
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myimage
```

### What Breaks When You Drop All Capabilities

Test by running your app with `--cap-drop ALL`. If it fails, the error
message tells you what's missing. Common issues:

```bash
# App needs to bind to port 80 (port < 1024)
Error: Permission denied (port 80)
Fix: --cap-add NET_BIND_SERVICE

# App needs to change file ownership
Error: Operation not permitted (chown)
Fix: --cap-add CHOWN

# App uses ptrace for debugging
Error: Permission denied (ptrace)
Fix: --cap-add SYS_PTRACE  ← dev only, never production

# App needs to ping (raw sockets)
Error: socket: Operation not permitted
Fix: --cap-add NET_RAW  ← or use non-raw ping libraries
```

### Workflow — How to Find What Your App Actually Needs

```bash
# Step 1: Run with ALL capabilities dropped
docker run --cap-drop ALL myimage

# Step 2: If it fails, run with strace to see what system calls fail
docker run --cap-drop ALL --cap-add SYS_PTRACE myimage strace -e trace=process python app.py

# Step 3: Add back only the specific capability that failed
docker run --cap-drop ALL --cap-add <specific-cap> myimage

# Step 4: Repeat until app works — each added capability is documented
```

Common capabilities you might actually need:

| Capability | When you need it |
|---|---|
| `NET_BIND_SERVICE` | App binds to port < 1024 (e.g., port 80) |
| `SYS_PTRACE` | Debugging tools — dev only, never production |
| `CHOWN` | App changes file ownership at runtime |
| `NET_RAW` | App sends raw network packets (ping, custom protocols) |

**Rule:** Start with `--cap-drop ALL`. Add back only what breaks.
The narrower your capabilities, the smaller your attack surface.

---

## Mistake 5 — Writable Filesystem

By default, a container can write to any path in its own filesystem.
An attacker with code execution can:
- Install tools (`apt-get install netcat`)
- Modify your app files
- Create cron jobs or init scripts for persistence
- Write malware disguised as your app

### The Fix — Read-Only Root Filesystem

```bash
docker run --read-only myimage
# Any write attempt → "Read-only file system" error ✅
```

### Real Scenarios and How to Handle Each

**Scenario 1 — App writes nothing (pure compute/API call)**
```bash
docker run --read-only myimage
# No tmpfs needed — app has no reason to write
```

**Scenario 2 — App writes temp files during processing**
```bash
docker run --read-only --tmpfs /tmp myimage
# /tmp is writable in RAM, everything else locked
# Files in /tmp disappear when container stops — that's fine for temp work
```

**Scenario 3 — App writes logs**
```bash
docker run --read-only --tmpfs /var/log myimage
# Logs go to RAM, never to disk
# Better: configure your app to write logs to stdout instead of files
# Docker captures stdout automatically — no need for a log file at all
```

**Scenario 4 — App writes multiple paths**
```bash
docker run \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /var/log \
  --tmpfs /run \
  myimage
# Each --tmpfs is a separate writable RAM mount
```

**Scenario 5 — App needs to write persistent data**
```bash
docker run \
  --read-only \
  --tmpfs /tmp \
  -v mydata:/app/data \    # named volume — writable, persistent
  myimage
# Root fs is locked, /tmp is RAM, /app/data persists via volume
```

### Understanding tmpfs vs Named Volume

```
--tmpfs /tmp          → RAM only, gone when container stops, fast, secure
-v mydata:/app/data   → persistent volume, survives container stop, on disk
```

Use `--tmpfs` for scratch space your app doesn't need to keep.
Use volumes for data that must survive.

### How to Find All Paths Your App Writes To

Before applying `--read-only`, discover what your app actually writes:

```bash
# Run without read-only, trace all file writes
docker run --rm myimage sh -c "strace -e trace=openat python app.py 2>&1 | grep 'O_WRONLY\|O_RDWR'"

# Or run with read-only and let it fail — error shows the path
docker run --read-only myimage
# Error: Read-only file system: '/var/run/app.pid'
# → add: --tmpfs /var/run
```

---

## The Complete Hardened Run Command

```bash
docker run \
  --read-only \                        # lock filesystem
  --cap-drop ALL \                     # remove all capabilities
  --security-opt no-new-privileges \   # block privilege escalation
  --user 1001:1001 \                   # non-root UID:GID
  --memory 256m \                      # cap RAM (cgroup)
  --cpus 0.5 \                         # cap CPU (cgroup)
  --tmpfs /tmp \                       # writable RAM for temp only
  my-first-image:1.0
```

### `--security-opt no-new-privileges`
Prevents the process from ever gaining more privileges than it started with —
even if it calls setuid binaries inside the container. Always add this.

---

## The Hardened Dockerfile (All Fixes Applied)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .

# Security: create and use non-root user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

USER appuser

CMD ["python", "app.py"]
```

---

## Image Scanning

Even a hardened image may contain known CVEs (vulnerabilities) in its
base OS packages. Scan before pushing to production:

```bash
# Built-in Docker scout (Docker Desktop)
docker scout cves my-first-image:1.0

# Trivy (open source, more detailed)
# Install: brew install trivy
trivy image my-first-image:1.0
```

Scanner output shows:
- CVE ID (e.g., CVE-2023-1234)
- Severity (CRITICAL / HIGH / MEDIUM / LOW)
- Which package has the vulnerability
- Whether a fix is available (upgrade to which version)

**Rule:** No CRITICAL vulnerabilities in production images. Run scanner
in CI/CD pipeline on every build.

---

## Security Checklist

| Check | How |
|---|---|
| Non-root user | `USER` in Dockerfile |
| No secrets in image | Use secret file mounts |
| No secrets in env vars | Read from `/run/secrets/` |
| Minimal base image | Use `slim` or `alpine` or distroless |
| Capabilities dropped | `--cap-drop ALL` |
| No privilege escalation | `--security-opt no-new-privileges` |
| Read-only filesystem | `--read-only --tmpfs /tmp` |
| Resource limits | `--memory` and `--cpus` |
| Image scanned | `docker scout` or `trivy` |

---

## Command Reference — Every Command Explained

---

### `docker run --rm myimage whoami`

```
docker run   → create and start a container
--rm         → automatically delete the container when it exits
              (no need to run docker rm manually)
myimage      → the image to run
whoami       → Linux command: prints the current username of the running process
              overrides CMD in the Dockerfile for this one run only
```

**What you see:**
- `root` → container is running as root (dangerous)
- `appuser` → container is running as non-root (safe)

---

### `RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser`

```
RUN              → execute this during image BUILD (not at runtime)
addgroup         → Linux tool to create a new group
  --system       → create a system group (GID < 1000, no login, for services)
  appgroup       → name of the group (you choose this name)
&&               → run next command only if previous succeeded
adduser          → Linux tool to create a new user
  --system       → create a system user (UID < 1000, no password, no home dir, no login shell)
  --ingroup appgroup → add this user to the appgroup group we just created
  appuser        → name of the user (you choose this name)
```

**Result:** A group `appgroup` and a user `appuser` now exist inside the image.
`appuser` has no password, cannot log in, and belongs to `appgroup`.

---

### `RUN chown -R appuser:appgroup /app`

```
chown            → Linux command: change ownership of a file or directory
  -R             → recursive — apply to the directory AND everything inside it
  appuser        → new owner (user)
  :appgroup      → new group owner (the colon separates user from group)
  /app           → the path to change ownership on
```

**Before:** `/app` owned by `root:root` — `appuser` cannot write here
**After:** `/app` owned by `appuser:appgroup` — `appuser` can read and write

---

### `COPY --chown=appuser:appgroup requirements.txt .`

```
COPY             → copy files from your Mac into the image
--chown=appuser:appgroup → set the owner of the copied file immediately
                  Format: --chown=<user>:<group>
requirements.txt → source file on your Mac
.                → destination = current WORKDIR inside the image
```

**Why use this instead of chown:** One step instead of two. The file is
copied and its ownership is set in the same layer — cleaner and more efficient.

---

### `docker run --rm myimage ls -la /app`

```
docker run   → start a container
--rm         → delete container after it exits
myimage      → the image to use
ls           → Linux command: list directory contents
  -l         → long format — shows permissions, owner, group, size, date
  -a         → all files — includes hidden files starting with .
  /app       → the directory to list
```

**Sample output explained:**
```
drwxr-xr-x  appuser appgroup  4096  /app
│││││││││└─ others: r-x (read + execute, no write)
││││││└──── group:  r-x (read + execute, no write)
│││└─────── owner:  rwx (read + write + execute)
││└──────── setgid bit (not set)
│└───────── setuid bit (not set)
└────────── d = directory (- would mean regular file)
```

---

### `docker run --rm myimage id`

```
docker run   → start a container
--rm         → delete after exit
myimage      → the image
id           → Linux command: prints the UID, GID, and group memberships
              of the current user
```

**Sample output:**
```
uid=100(appuser) gid=101(appgroup) groups=101(appgroup)
│                │                 └── all groups this user belongs to
│                └───────────────── primary group ID and name
└────────────────────────────────── user ID and name
```

This UID (100) is the number used in `--user 100:101`.

---

### `docker run --user 100:101 myimage`

```
docker run   → start a container
--user 100:101  → run the container process as UID 100, GID 101
              Format: --user <uid>:<gid>
              Alternative: --user appuser (use name instead of number)
myimage      → the image
```

**When to use `--user` in docker run vs `USER` in Dockerfile:**
- `USER` in Dockerfile = baked into the image, always runs as that user
- `--user` in docker run = override at runtime, useful when running someone else's image

---

### `docker inspect <container> | grep -A 5 "Env"`

```
docker inspect   → outputs full JSON metadata of a container
<container>      → container name or ID
|                → pipe: send output of docker inspect into grep
grep             → Linux tool: search for a pattern in text
  -A 5           → After match: also print 5 lines AFTER the matching line
                  (so you see the full Env array, not just the header)
  "Env"          → the pattern to search for in the JSON output
```

**Why this matters:** `docker inspect` output is ~200 lines of JSON.
`grep -A 5 "Env"` finds the Env section and shows it with 5 lines of context —
just enough to see what environment variables are set.

---

### `docker run --rm python:3.11-slim sh -c "cat /proc/self/status | grep CapEff"`

```
docker run              → start a container
--rm                    → delete after exit
python:3.11-slim        → use this image
sh -c "..."             → run a shell and execute the quoted command inside it
                        (needed because we're chaining two commands with |)
cat /proc/self/status   → print the status file of the current process
                        /proc = virtual filesystem exposing kernel info
                        /proc/self = the current process (not PID, always "self")
                        /proc/self/status = text file with process info
|                       → pipe output to grep
grep CapEff             → filter for only the line containing "CapEff"
                        CapEff = Effective Capabilities (what's currently active)
```

**Output:** `CapEff: 00000000a80425fb`
Each bit in this hex number represents one Linux capability.
`a80425fb` = 14 capabilities active. `00000000` = zero capabilities.

---

### `docker run --cap-drop ALL myimage`

```
docker run     → start a container
--cap-drop ALL → drop ALL Linux capabilities from this container
               ALL is a special keyword meaning every capability
               You can also drop specific ones: --cap-drop NET_RAW
myimage        → the image
```

**Effect:** The container process has zero Linux capabilities.
It cannot change file ownership, bind to ports, sniff packets, or anything else.
It can still read files, make network connections, and run code normally.

---

### `docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myimage`

```
--cap-drop ALL           → first drop everything
--cap-add NET_BIND_SERVICE → then add back only this one capability
                          NET_BIND_SERVICE = allow binding to ports < 1024
                          (e.g., port 80 for HTTP, port 443 for HTTPS)
```

**Order matters:** Drop first, then add. This ensures you start from zero
and only have exactly what you specified — not the default 14 plus your additions.

---

### `docker run --read-only myimage`

```
docker run    → start a container
--read-only   → mount the container's root filesystem as read-only
              The container CANNOT write to ANY path by default
              Any write attempt → "Read-only file system" error
myimage       → the image
```

**What it locks:** Everything in the container's filesystem — `/app`, `/etc`,
`/usr`, `/var`, etc. The image layers become completely immutable at runtime.

**What it does NOT lock:** Volumes and tmpfs mounts — those are separate
filesystems added on top, and they follow their own rules.

---

### `docker run --read-only --tmpfs /tmp myimage`

```
--read-only    → lock the root filesystem
--tmpfs /tmp   → create a temporary filesystem in RAM at /tmp
               tmpfs = temporary filesystem (lives in memory, not disk)
               /tmp is now writable, but only in RAM
               Contents disappear when the container stops
               Multiple paths: --tmpfs /tmp --tmpfs /var/log --tmpfs /run
```

**Memory usage:** tmpfs uses actual RAM. Don't mount huge directories as
tmpfs — it will consume your container's memory budget.

---

### `docker run --security-opt no-new-privileges myimage`

```
docker run              → start a container
--security-opt          → set a security option
  no-new-privileges     → prevent the process from gaining more privileges
                        after it starts — even via setuid binaries
                        setuid = files with special bit set that run as their owner
                        (e.g., /usr/bin/passwd runs as root regardless of caller)
```

**Why `USER appuser` alone isn't enough:**
If your image contains a setuid file, even `appuser` could call it and get
root access. `no-new-privileges` blocks this at the kernel level — no setuid
file can ever elevate the process's privileges.

---

### `docker run --user 1001:1001 myimage`

```
--user 1001:1001  → run the container as UID 1001, GID 1001
                  Format: --user <uid>:<gid>
                  1001 is a safe non-root UID (above 1000 = regular user range)
                  Both UID and GID set to 1001 here (same number, different concepts)
```

**Difference from USER in Dockerfile:**
`USER` in Dockerfile = user must exist inside the image (created with adduser)
`--user 1001` at runtime = any UID, no need for the user to exist in /etc/passwd
(though some apps break if the UID has no entry in /etc/passwd)

---

### `docker scout cves my-first-image:1.0`

```
docker scout      → Docker's built-in security scanning tool
  cves            → subcommand: scan for CVEs (Common Vulnerabilities and Exposures)
                  CVE = a publicly known security vulnerability with an ID like CVE-2023-1234
my-first-image:1.0 → the image to scan
```

**Output includes:**
- CVE ID and description
- Severity: CRITICAL / HIGH / MEDIUM / LOW / UNSPECIFIED
- Package name and vulnerable version
- Fixed version (if a fix exists)

**Alternative — Trivy (more detailed, open source):**
```bash
brew install trivy          # install once on Mac
trivy image my-first-image:1.0  # scan the image
```

---

### `strace -e trace=openat python app.py 2>&1 | grep 'O_WRONLY\|O_RDWR'`

```
strace               → Linux tool: trace system calls made by a program
  -e trace=openat    → only show the openat() system call (file open events)
python app.py        → the program to trace
2>&1                 → redirect stderr (2) to stdout (1) — strace outputs to stderr
                     merging both streams so grep can filter all output
|                    → pipe merged output to grep
grep                 → filter the output
  'O_WRONLY\|O_RDWR' → match lines containing O_WRONLY (write-only) OR O_RDWR (read-write)
                     \| is the OR operator in grep's basic regex
                     O_WRONLY = file opened for writing only
                     O_RDWR   = file opened for reading AND writing
```

**What this tells you:** Every file your app opens for writing — exactly the
paths you need to allow with `--tmpfs` or a volume when using `--read-only`.

---

## Check Your Understanding — Q&A

### Q1. Why is passing secrets via `-e` dangerous even if the image itself doesn't contain them?

**Answer:** Environment variables passed via `-e` are stored in the container's
metadata and are fully visible in `docker inspect` to anyone with Docker access
on that machine. They also appear in logs and crash reports. Use secret file
mounts (`/run/secrets/`) instead — the value is never stored in metadata.

---

### Q2. Your app only makes HTTP requests. What capabilities does it need?

**Answer:** Zero. An app that only makes outbound HTTP requests needs no Linux
capabilities. Use `--cap-drop ALL`. If it later breaks, add back only the
specific capability that's required. Start from zero and expand — not the
other way around.

---

### Q3. What does `--security-opt no-new-privileges` do that `USER appuser` doesn't?

**Answer:** `USER appuser` sets the starting user. `--security-opt no-new-privileges`
ensures the process can NEVER gain more privileges after startup — even if it
calls a setuid binary (a file with the setuid bit set that runs as root).
`USER` alone doesn't prevent privilege escalation via setuid. Both are needed.

---

### Q4. You use `--read-only` but your app needs to write log files. What do you do?

**Answer:** Add `--tmpfs /var/log` to mount a writable RAM filesystem at the
log path only. Everything else stays read-only. The logs exist in RAM only —
they don't persist after the container stops, which is fine since logs should
go to a log collector anyway, not be stored in the container.
