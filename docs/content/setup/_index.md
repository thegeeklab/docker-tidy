---
title: Setup
---

<!-- prettier-ignore-start -->
<!-- spellchecker-disable -->
{{< toc >}}
<!-- spellchecker-enable -->
<!-- prettier-ignore-end -->

## Pip

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- spellchecker-disable -->
{{< highlight Shell "linenos=table" >}}
# From PyPI as unprivileged user
$ pip install docker-tidy --user

# .. or as root
$ sudo pip install docker-tidy

# From Wheel file
$ pip install https://github.com/thegeeklab/docker-tidy/releases/download/v0.1.0/docker_tidy-0.1.0-py2.py3-none-any.whl
{{< /highlight >}}
<!-- spellchecker-enable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

## Docker

The default entrypoint is set to the `gc` sub-command and you have to overwrite it
if you want to use other sub-commands like `stop`.

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- spellchecker-disable -->
{{< highlight Shell "linenos=table" >}}
docker run \
    -e TIDY_GC_MAX_CONTAINER_AGE="3 days ago" \
    -e TIDY_GC_MAX_IMAGE_AGE="5 days ago" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    thegeeklab/docker-tidy
{{< /highlight >}}
<!-- spellchecker-enable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
{{< hint type=note >}}
Keep in mind, that you have to pass SELinux labels (:Z or :z) to your mount option if you are working on SELinux enabled systems.
{{< /hint >}}
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
