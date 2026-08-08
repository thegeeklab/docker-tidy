---
title: Usage
---

<!-- spellchecker-disable -->
{{< toc >}}
<!-- spellchecker-enable -->

## Garbage Collector

Remove old docker containers and docker images.

`docker-tidy gc` will remove stopped containers and unused images that are older than \"max age\". Running containers, and images which are used by a container are never removed.

Maximum age can be specified with any format supported by [dateparser](https://dateparser.readthedocs.io/en/latest/index.html#features).

**Example:**

```Shell
docker-tidy gc --max-container-age "3 days ago" --max-image-age "30 days ago"
```

### Prevent images from being removed

`docker-tidy gc` supports an image exclude list. If you have images that you\'d like to keep around forever you can use the exclude list to prevent them from being removed.

```Shell
    --exclude-image
        Never remove images with this tag. May be specified more than once.
```

### Prevent containers and associated images from being removed

`docker-tidy gc` also supports a container exclude list based on labels. If there are stopped containers that you\'d like to keep, then you can check the labels to prevent them from being removed.

```Shell
    --exclude-container-label
        Never remove containers that have the label key=value. =value can be
        omitted and in that case only the key is checked. May be specified
        more than once.
```

### Free disk space by removing oldest images

`docker-tidy gc` can remove the oldest unused images until a target amount of free disk space is available on the Docker data filesystem. This is an alternative to time-based image removal when you care more about disk pressure than image age.

The target can be specified as an absolute size or a percentage of the filesystem:

```Shell
# Remove oldest images until at least 10 GB is free
docker-tidy gc --min-free-disk-space 10GB

# Remove oldest images until at least 15% of the filesystem is free
docker-tidy gc --min-free-disk-space 15%
```

Supported size units: `B`, `KB`/`K`, `MB`/`M`, `GB`/`G`, `TB`/`T`.

By default, the filesystem containing `/var/lib/docker` is checked. To monitor a different path:

```Shell
docker-tidy gc --min-free-disk-space 5GB --disk-path /mnt/docker-data
```

Images are removed oldest-first, respecting `--exclude-image` and in-use filters. The tool re-checks free space after each removal and stops once the target is met.

This flag can be combined with `--max-image-age` and other cleanup flags; each runs independently.

## Autostop

Stop containers that have been running for too long.

`docker-tidy stop` will `docker stop` containers where the container name starts with [\--prefix]{.title-ref} and/or it has been running for longer than [\--max-run-time]{.title-ref}.

If no prefix is set, **all** containers matching the `max-run-time` will be stopped!

**Example:**

```Shell
docker-tidy stop --max-run-time "2 days ago" --prefix "projectprefix_"
```
