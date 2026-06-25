# Running NILRT in Containers

NILRT can be built and run as an OCI/Docker container image, letting you run a
NILRT runmode system (with SSH, the NI System Web Server, mDNS discovery, and
opkg) on a regular Linux host without dedicated hardware. This is useful for
development, testing, and CI.

Two container image variants are produced:

* **`nilrt-runmode-container`** — the full Base System Image, including DKMS
  and the proprietary NI software stack.
* **`nilrt-slim-container`** — a minimal Base System Image with just the core
  runmode userspace: no desktop packages and none of the proprietary NI
  software. Smaller and faster to start; install only the NI software you
  need via `opkg`.

## 1. Prerequisites

To **build** the container images you need the same environment used to build
any NILRT image (see [Entering the Bitbake Build Environment](../README.md#entering-the-bitbake-build-environment)):

* A Linux build host (NI builds and tests on Ubuntu).
* The Docker engine (the bare engine, **not** Docker Desktop — see the build setup notes in the main README).
* The project source and submodules checked out, the `build-nilrt` pyrex image built, and `ni-oe-init-build-env` sourced.
* `MACHINE=x64` exported (containers are intended for x64 hosts).
* The core package feed and package index built first (`packagefeed-ni-core` and `package-index`), exactly as for other images.

To **run** the container images you need, on the host that will run them:

* A container runtime: **Docker** (with the Compose plugin) or **podman**.
* `python3` (used by the helper scripts for IP math and network inspection).
* For LAN-visible containers via macvlan: root/`sudo` access, and an interface
  in promiscuous mode (the setup script handles this). In VMs (e.g.
  VirtualBox/VMware) the host NIC must allow promiscuous mode.
* The containers run as `--privileged` (required by the NI RT init, niauth,
  bind-mounts, and `setcap` in the postinst), so the host must permit that.

## 2. Building the container images

After completing the build-environment setup and building the core feed and
package index, build the image recipes with bitbake:

```bash
export MACHINE=x64

# build the full runmode container image...
bitbake nilrt-runmode-container

# ...and/or the slim variant
bitbake nilrt-slim-container
```

The build emits OCI and docker-archive artifacts under
`$BUILDDIR/tmp-glibc/deploy/images/x64/`. The `*.docker.tar` archive can be
loaded directly into Docker:

```bash
cd $BUILDDIR/tmp-glibc/deploy/images/x64/

# full image
docker load -i nilrt-runmode-container-x64.docker.tar
# slim image
docker load -i nilrt-slim-container-x64.docker.tar

# verify the images are present; note the version tag
docker images nilrt-runmode-container
docker images nilrt-slim-container
```

The images are tagged `nilrt-runmode-container:<DISTRO_VERSION>` and
`nilrt-slim-container:<DISTRO_VERSION>-slim`. The `nilrt-ctr.sh` helper
auto-detects the newest locally-available tag, or you can pin one with the
`NILRT_VERSION` environment variable.

For podman, you can load the same docker-archive tarball too, e.g.:

```bash
podman load -i nilrt-runmode-container-x64.docker.tar
```

## 3. Running the containers

### a. Create the container network (once)

Containers attach to an external macvlan network named `nilrt-net`, which gives
each container its own IP address on your physical LAN (so remote hosts and NI
MAX can discover them). Create it once with:

```bash
# auto-detect interface, subnet, and gateway
bash docker/setup-nilrt-network.sh

# ...or specify everything explicitly, reserving a range for containers
bash docker/setup-nilrt-network.sh -i eth0 -s 192.0.2.0/24 -g 192.0.2.1 -r 192.0.2.64/26

# podman users
bash docker/setup-nilrt-network.sh --runtime podman
```

Reserving an IP range (`-r/--ip-range`) for containers avoids DHCP conflicts —
coordinate the range with your network administrator. The script also sets up a
`nilrt-shim` interface so the **host** can reach containers on the macvlan
network (macvlan otherwise blocks host-to-container traffic). Use `--dry-run`
to preview the commands without applying them.

### b. Launch containers

Use `nilrt-ctr.sh run`, which scans the LAN for free addresses and pins a
collision-free IP to each container:

```bash
# launch one full runmode container
bash docker/nilrt-ctr.sh run nilrt

# launch three slim containers
bash docker/nilrt-ctr.sh run nilrt-slim -n 3

# restrict allocation to a CIDR, or skip the (slow) LAN scan
bash docker/nilrt-ctr.sh run nilrt -r 192.0.2.64/26
bash docker/nilrt-ctr.sh run nilrt --no-scan
bash docker/nilrt-ctr.sh run nilrt --dry-run
```

For **podman**, assign a free address yourself with an explicit `--ip` (the
`nilrt-ctr.sh run` helper is Docker/Compose-specific):

```bash
podman run -it --privileged --network=nilrt-net --ip 192.0.2.65 \
    nilrt-runmode-container:TAG
```

### c. Manage running containers

`nilrt-ctr.sh` provides convenience commands; targets can be a container name,
an ID prefix, or a managed index:

```bash
bash docker/nilrt-ctr.sh status nilrt-1               # show a container summary
bash docker/nilrt-ctr.sh shell nilrt-1                # open an interactive shell
bash docker/nilrt-ctr.sh set-feed all 2026Q2          # point opkg at a package feed
bash docker/nilrt-ctr.sh install nilrt-1 --feed 2026Q2 ni-labview-realtime
bash docker/nilrt-ctr.sh remove nilrt-1 PKG
bash docker/nilrt-ctr.sh change-hostname nilrt-1 cRIO-test
```

Standard runtime commands work too, filtered to NILRT-managed containers:

```bash
docker ps -a --filter label=nilrt.managed=true
docker logs CONTAINER
docker exec -it CONTAINER /bin/bash
```

## 4. Configurable run options

Container behavior is driven by [`docker/docker-compose.yml`](../docker/docker-compose.yml)
and the environment variables consumed by the helper scripts. The most useful
knobs:

| Option | How to set it | Notes |
| --- | --- | --- |
| **Image variant** | `run nilrt` vs `run nilrt-slim` | Full runmode vs slim image. |
| **Image version/tag** | `NILRT_VERSION=<tag>` env var | Defaults to the newest locally-loaded tag. |
| **Number of containers** | `-n/--count N` on `run` | Launches N collision-free instances. |
| **Network name** | `NILRT_NETWORK` env var (default `nilrt-net`) | Must be an existing external macvlan network. |
| **IP address / range** | `NILRT_IP` (per container), `-r/--ip-range` on `run`/network setup | `run` pins a verified-free IP; podman uses `--ip`. |
| **LAN scan tuning** | `NILRT_SCAN=0` (disable), `NILRT_SCAN_TIMEOUT=<sec>` | Controls the free-IP probe before launch. |
| **Hostname** | `nilrt-ctr.sh change-hostname <target> <name>` | Also re-derives the NI serial number. |
| **Package feed** | `nilrt-ctr.sh set-feed <target\|all> <YYYYQN>` | Writes `/etc/opkg/base-feeds.conf`. |

Because the containers are launched through Docker Compose, you can constrain
host resources (CPU, memory, storage, devices, extra volumes) by editing
`docker/docker-compose.yml` or adding a Compose override. For example, to limit
CPU and memory and add a persistent volume, add to the relevant service:

```yaml
services:
  nilrt:
    cpus: "2.0"            # max 2 CPU cores
    cpuset: "0-1"          # pin to specific cores (optional)
    mem_limit: "4g"        # max 4 GiB RAM
    memswap_limit: "4g"    # cap swap as well
    shm_size: "1g"         # /dev/shm size
    storage_opt:
      size: "20G"          # writable-layer size cap (requires a supporting storage driver)
    volumes:
      - /host/path:/c      # persist deployed apps / data across container restarts
```

When running directly with `docker run` or `podman run`, the equivalent flags
are `--cpus`, `--cpuset-cpus`, `--memory`, `--memory-swap`, `--shm-size`,
`--storage-opt size=`, and `-v/--volume`. Note that the NILRT init requires
`--privileged`; dropping it will break niauth, the web server, and the
bind-mounts.

## 5. Supported host operating systems

The container images are **x64 Linux** images and are intended to run on a
**Linux host** with a native container runtime:

* **Docker engine** (not Docker Desktop) with the Compose plugin, or **podman**.
* NI builds and validates on **Ubuntu**; other modern Linux distributions with
  a current Docker/podman should work.
* macvlan networking (used for LAN-visible container IPs) is a Linux feature; it
  is not available on Docker Desktop for macOS/Windows, so the LAN-discovery
  workflow described here is Linux-only. Running the image without macvlan
  (e.g. with default bridge networking) is possible but loses direct LAN
  discoverability by NI MAX/VeriStand.
* When the host is itself a VM, enable nested promiscuous mode on the VM's NIC
  for macvlan to work.

> **Note:** the `docker/*` commands above are written relative to the
> repository root. Run them from the top of the nilrt checkout.
