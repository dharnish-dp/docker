# Lesson 03 — Under the Hood: Namespaces & cgroups

## Goal
Understand how Docker actually creates isolation. This is what separates
top 1% Docker knowledge from average — when things break, you reason from
first principles instead of guessing.

---

## The Core Question

When you run `docker run python:3.11-slim bash` and get a Linux shell on
your Mac — how does that actually work? Your Mac is macOS. No VM involved.
Yet you get a Debian filesystem, a separate process tree, a separate network.

The answer: **two Linux kernel features** — namespaces and cgroups.
Docker is a user-friendly wrapper around these two things.

---

## 1. Namespaces — The Walls (Isolation)

A namespace puts walls around a container so it can't see outside.

**One sentence:** Namespaces control what a container can **see**.

Docker uses 6 namespaces per container:

| Namespace | What it isolates | What the container sees |
|---|---|---|
| `pid` | Process IDs | Only its own processes — not your Mac's |
| `net` | Network | Its own network interfaces and IP |
| `mnt` | Filesystem mounts | Its own filesystem (the Debian root) |
| `uts` | Hostname | Its own hostname (the container ID) |
| `ipc` | Inter-process communication | Isolated message queues |
| `user` | User/group IDs | Can be root inside without being root on Mac |

### Proof — pid namespace in action

Your Mac's process count:
```bash
ps aux | wc -l   # returns ~625
```

Same machine, inside a container:
```bash
docker run python:3.11-slim sh -c "ls /proc | grep -E '^[0-9]+$'"
# returns: 1, 7, 8  — only 3 processes visible
```

625 processes on the Mac. Container sees only 3. Same kernel.
The `pid` namespace wall is what makes this happen.

**Note:** `ps` is not installed in slim images — use `/proc` instead.
Every running process appears as a numbered directory in `/proc`.

### Why PID 1 matters

Inside a container, PID 1 is the first process (bash, your app, etc.).
When PID 1 exits, the container exits. This is why exiting bash stops
the container — bash was PID 1.

---

## 2. cgroups — The Budget (Resource Limits)

cgroups (control groups) limit how much of the host's resources a
container can consume — CPU, memory, disk I/O.

**One sentence:** cgroups control how much a container can **use**.

```
Without cgroups:
  Container goes rogue → consumes 100% CPU → your Mac freezes

With cgroups:
  Container hits the limit → kernel throttles/kills it → Mac stays stable
```

### How to set cgroup limits

```bash
docker run --memory 100m --cpus 0.5 python:3.11-slim python -c "import sys; print(sys.version)"
```

- `--memory 100m` — container cannot use more than 100MB RAM
- `--cpus 0.5` — container gets at most half a CPU core
- If memory limit is exceeded → kernel OOM-kills the container
- If CPU limit is exceeded → kernel throttles it (slows it down)

The container has no say. cgroups operate at the kernel level.

**Always set memory and CPU limits in production.** Without them, one
misbehaving container can starve all others — and the host.

---

## The Full Docker Formula

```
docker run = namespaces + cgroups + overlay filesystem
             ↑            ↑          ↑
             what it sees  how much   where files come from
                           it uses    (image layers stacked)
```

Everything else in Docker — images, registries, compose, networking —
is built on top of these three primitives.

---

## Why Mac Needs a Linux VM

Namespaces and cgroups are Linux kernel features. macOS doesn't have them.
So Docker Desktop runs a lightweight Linux VM (via Apple's Virtualization
framework) silently in the background. Your containers run inside that VM —
but you never see or manage it. Docker Desktop handles it transparently.

This is also why Docker Desktop must be running before any `docker` command
works — the Linux VM must be up for the kernel features to be available.

---

## Summary

| Concept | One line | Docker flag |
|---|---|---|
| Namespace | Controls what the container can see | (automatic) |
| cgroup | Controls how much the container can use | `--memory`, `--cpus` |
| overlay fs | Stacks image layers into a filesystem | (automatic) |

---

## Key Commands

```bash
# Run with resource limits (cgroups)
docker run --memory 512m <image>          # max 512MB RAM
docker run --memory 512m --memory-swap 512m <image>  # disable swap too
docker run --cpus 1.5 <image>             # max 1.5 CPU cores
docker run --cpus 0.5 --memory 256m <image>  # both limits together
docker run --pids-limit 100 <image>       # max 100 processes (prevents fork bombs)

# See processes inside container (slim images don't have ps)
docker run <image> sh -c "ls /proc | grep -E '^[0-9]+$'"

# See resource usage of running containers live
docker stats                              # live CPU, RAM, network, disk I/O

# See container's cgroup limits
docker inspect <container> | grep -i memory
```

---

## Check Your Understanding — Q&A

### Q1. What is the difference between a namespace and a cgroup?

**Answer:**
- **Namespace** = controls what the container can **see** (isolation)
- **cgroup** = controls how much the container can **use** (resource limits)

Namespace puts walls around the container. cgroup gives it a budget.

---

### Q2. Your container has a memory leak. You set `--memory 256m`. What happens when it exceeds 256MB?

**Answer:** The Linux kernel **OOM-kills** (Out of Memory kills) the container
process. The container exits with status `Exited (137)`.

**Common mistake:** Saying the kernel "blocks" the usage. It doesn't block —
it terminates. Exit code 137 always means OOM kill. This is how you identify
memory limit breaches in production.

---

### Q3. Why does Docker Desktop need to be running on Mac for containers to work?

**Answer:** Namespaces and cgroups are **Linux kernel features**. macOS does
not have a Linux kernel. Docker Desktop runs a lightweight Linux VM silently
in the background (via Apple's Virtualization framework). Your containers
actually run inside that Linux VM — not directly on macOS. No Docker Desktop
= no Linux VM = no kernel features = no containers.

---

### Q4. A container has PID 1 = your Python script. The script crashes (exit code 1). What happens to the container?

**Answer:** The container **exits immediately** with `Exited (1)`.

**The rule:** PID 1 exits → container exits. No exceptions. The exit code
of the container matches the exit code of PID 1. This is why your app must
be PID 1 — not wrapped in a shell script — so crash signals propagate correctly.
