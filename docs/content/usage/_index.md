---
title: Usage
---

{{< toc >}}

## Garbage Collector

Remove old docker containers and docker images.

`docker-tidy gc` will remove stopped containers and unused images that are older
than \"max age\". Running containers, and images which are used by a
container are never removed.

Maximum age can be specificied with any format supported by
[dateparser](https://dateparser.readthedocs.io/en/latest/index.html#features).

__Example:__

```Shell
docker-tidy gc --max-container-age "3 days ago" --max-image-age "30 days ago"
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
with [\--prefix]{.title-ref} and/or it has been running for longer than
[\--max-run-time]{.title-ref}.

If no prefix is set, __all__ containers matching the `max-run-time` will be stopped!

__Example:__

```Shell
docker-tidy stop --max-run-time "2 days ago" --prefix "projectprefix_"
```
