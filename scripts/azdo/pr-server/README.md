# NILRT PatchRev Server Container

## Starting the Server

The PR server can be started with sensible defaults through the normal `docker-compose up` workflow.

```bash
docker-compose -f pr-server.compose.yml up pr-server
```

This command will start the PR service on network port `0.0.0.0` and port `8585`.

## Configuring the Server

### Build-time arguments

These values are set or passed to the `pr-server.Dockerfile`.

* `PRSERVER_BB_REF` sets the upstream `bitbake` git object reference, which will be the target of the `git clone` operation during container setup. This value is directly passed to the `--branch` argument of `git clone`.
* `PRSERVER_BB_REMOTE` sets the remote URL of the upstream `bitbake` repo.

### Run-time environment variables

These values are set or passed to the `pr-server.compose.yml`.

* `PRSERVER_HOST` sets the container ipv4 address through which the PR server will be hosted.
* `PRSERVER_PORT` sets the container ipv4 port through which the PR server will be hosted.
* `VERBOSE` raises the PR server `loglevel` to `DEBUG`, if set to `"true"`. Otherwise, the loglevel is set to `INFO`.

## Container Architecture

The `pr-server` container is based upon the upstream [python](https://hub.docker.com/_/python) docker container layer. It's mission is to setup and run a single instance of the bitbake PatchRev server.

The container sources its implementation of the bitbake PR server from a shallow-clone of an upstream `bitbake` git repo instance. The bitbake source is checked out to the `WORKDIR` (`/srv/bitbake`), and the server is run using an unprivileged system user account called `bitbake`.

The PR server database `.sqlite3` file and log file are stored in the `/var/pr-server` directory. This directory is volatile with respect to the lifetime of the container overlay. To permanently retain the databse and log file, bind-mount the data directory to a persistent location on the container host machine.

It is a terrible idea to have multiple instances of this container accessing the same underlying database file.
