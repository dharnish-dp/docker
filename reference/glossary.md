# Docker Glossary

**Image**
A read-only blueprint for a container. Contains the OS filesystem, application
code, dependencies, and config. Like a Python class definition — not running,
just a template. Built from a Dockerfile.

**Container**
A running (or stopped) instance of an image. Isolated process with its own
filesystem, network, and process list. Like a Python object instantiated from
a class. Ephemeral by default — changes are lost when removed.

**Dockerfile**
A text file with instructions for building a Docker image. Each instruction
creates a layer. Think of it as a recipe.

**Layer**
One step in an image's filesystem history. Images are made of stacked layers.
Layers are cached — unchanged layers are reused on rebuild.

**Registry**
A server that stores and distributes Docker images. Docker Hub is the default
public registry. Like PyPI, but for images.

**Tag**
A label on an image that identifies its version. Format: `image:tag`.
Example: `python:3.11-slim`. Defaults to `latest` if omitted.

**Docker Hub**
The default public registry at hub.docker.com. Hosts official images
(python, postgres, nginx, etc.) and community images.

**Docker Engine**
The background service (daemon) that manages containers, images, networks,
and volumes on your machine. Runs as `dockerd`.

**Docker CLI**
The `docker` command you type. It sends commands to the Docker Engine via API.

**Namespace**
A Linux kernel feature that provides isolation. Docker uses namespaces to give
each container its own view of the pid tree, network, filesystem, etc.

**cgroup (Control Group)**
A Linux kernel feature that limits resources. Docker uses cgroups to cap how
much CPU, memory, and I/O a container can use.

**Union Filesystem (overlay2)**
The filesystem technology that makes image layers possible. Layers stack on top
of each other, with the topmost writable layer being the container's read-write layer.

**Volume**
A Docker-managed storage mechanism. Data persists beyond container lifecycle.
Stored outside the container's union filesystem.

**Bind Mount**
Mounting a host directory directly into a container. Used in dev workflows.
`-v /host/path:/container/path`

**Port Mapping**
Forwarding traffic from a host port to a container port.
`-p 8080:80` means host port 8080 → container port 80.

**Docker Compose**
A tool for defining and running multi-container applications using a YAML file.

**BuildKit**
The modern Docker build engine. Faster builds, parallel stages, cache mounts,
secret mounts. Enabled by default in Docker 23+.

**Multi-stage Build**
A Dockerfile technique that uses multiple FROM instructions to separate the
build environment from the runtime image. Produces smaller final images.

**Distroless**
Minimal base images (from Google) that contain only the application and its
runtime dependencies — no shell, no package manager. Smallest attack surface.

**Entrypoint**
The command that runs when a container starts. Defined with `ENTRYPOINT` in
Dockerfile. Cannot be overridden by `docker run` arguments (unlike CMD).

**CMD**
Default arguments passed to the entrypoint. Can be overridden at `docker run`.

**SIGTERM / SIGKILL**
Linux signals. `docker stop` sends SIGTERM (graceful shutdown — app can
clean up). `docker kill` sends SIGKILL (immediate termination, no cleanup).

**PID 1**
The first process inside a container. Must handle SIGTERM properly for
graceful shutdown. Your app should be PID 1, not a shell wrapper.

**containerd**
The container runtime that Docker uses under the hood. Manages container
lifecycle (create, start, stop, delete). Docker is a higher-level wrapper.

**runc**
The low-level tool that actually spawns containers. Reads an OCI bundle
and calls the Linux kernel to create namespaces and start the process.

**OCI (Open Container Initiative)**
Industry standard for container formats and runtimes. Ensures containers
built with Docker can run with other tools (Podman, containerd, etc.).
