---
title: Documentation
---

[![Build Status](https://img.shields.io/drone/build/xoxys/docker-tidy?logo=drone)](https://cloud.drone.io/xoxys/docker-tidy)
[![Docker Hub](https://img.shields.io/badge/docker-latest-blue.svg?logo=docker&logoColor=white)](https://hub.docker.com/r/xoxys/docker-tidy)
[![Python Version](https://img.shields.io/pypi/pyversions/docker-tidy.svg)](https://pypi.org/project/docker-tidy/)
[![PyPi Status](https://img.shields.io/pypi/status/docker-tidy.svg)](https://pypi.org/project/docker-tidy/)
[![PyPi Release](https://img.shields.io/pypi/v/docker-tidy.svg)](https://pypi.org/project/docker-tidy/)
[![License: MIT](https://img.shields.io/github/license/xoxys/docker-tidy)](LICENSE)

## Install

There are three installation options

### Container

```Shell
docker pull xoxys/docker-tidy
docker run -ti \
    -v /var/run/docker.sock:/var/run/docker.sock \
    xoxys/docker-tidy docker-tidy gc --help
```

### Source

```Shell
pip install git+https://github.com/xoxys/docker-tidy.git
```

## Garbage Collector

Remove old docker containers and docker images.

`docker-tidy gc` will remove stopped containers and unused images that are older
than \"max age\". Running containers, and images which are used by a
container are never removed.

Maximum age can be specificied with any format supported by
[pytimeparse].

Example:

```Shell
docker-tidy gc --max-container-age 3days --max-image-age 30days
```

### Prevent images from being removed

`docker-tidy gc` supports an image exclude list. If you have images that you\'d
like to keep around forever you can use the exclude list to prevent them
from being removed.

```Shell
    --exclude-image
        Never remove images with this tag. May be specified more than once.
```

### Prevent containers and associated images from being removed

`docker-tidy gc` also supports a container exclude list based on labels. If there
are stopped containers that you\'d like to keep, then you can check the
labels to prevent them from being removed.

```Shell
    --exclude-container-label
        Never remove containers that have the label key=value. =value can be
        omitted and in that case only the key is checked. May be specified
        more than once.
```

## Autostop

Stop containers that have been running for too long.

`docker-tidy stop` will `docker stop` containers where the container name starts
with [\--prefix]{.title-ref} and it has been running for longer than
[\--max-run-time]{.title-ref}.

Example:

```Shell
docker-tidy stop --max-run-time 2days --prefix "projectprefix_"
```
