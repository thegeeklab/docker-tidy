---
title: Setup
---

{{< toc >}}

## Pip

<!-- markdownlint-disable -->
{{< highlight Shell "linenos=table" >}}
# From PyPI as unprivilegd user
$ pip install docker-tidy --user

# .. or as root
$ sudo pip install docker-tidy

# From Wheel file
$ pip install https://github.com/xoxys/docker-tidy/releases/download/v0.1.0/docker_tidy-0.1.0-py2.py3-none-any.whl
{{< /highlight >}}
<!-- markdownlint-enable -->

## Docker

The default entrypoint is set to the `gc` subcommand and you have to overwrite it
if you want to use other subcommands like `stop`.

<!-- markdownlint-disable -->
{{< highlight Shell "linenos=table" >}}
docker run \
    -e TIDY_GC_MAX_CONTAINER_AGE="3 days ago" \
    -e TIDY_GC_MAX_IMAGE_AGE="5 days ago" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    xoxys/docker-tidy
{{< /highlight >}}
<!-- markdownlint-enable -->

<!-- markdownlint-disable -->
{{< hint info >}}
**Info**\
Keep in mind, that you have to pass selinux labels (:Z or :z) to your mount option if you are working on selinux enabled systems.
{{< /hint >}}
<!-- markdownlint-enable -->
