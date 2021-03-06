---
title: Configuration
---

<!-- spellchecker-disable -->
{{< toc >}}
<!-- spellchecker-enable -->

_docker-tidy_ comes with default settings which should be sufficient for most users to start, but you can adjust most settings to your needs.

Changes can be made on different locations which will be processed in the following order (last wins):

- default configuration (build-in)
- global configuration file (path depends on your operating system)
- directory based configuration file (.dockertidy.yml|.dockertidy.yaml|.dockertidy in current working directory)
- environment variables
- CLI options

## Default settings

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- spellchecker-disable -->
{{< highlight YAML "linenos=table" >}}
---
# don't do anything
dry_run: False
http_timeout: 60

logging:
    # possible options debug | info | warning | error | critical
    level: "warning"
    # you can enable json logging if a parsable output is required
    json: False

gc:
  max_container_age:
  max_image_age:
  dangling_volumes: false
  exclude_images: []
  exclude_container_labels: []

stop:
  max_run_time:
  prefix: []
{{< /highlight >}}
<!-- spellchecker-enable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

## Environment Variables

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- spellchecker-disable -->
{{< highlight Shell "linenos=table" >}}
TIDY_CONFIG_FILE=
TIDY_DRY_RUN=False
TIDY_HTTP_TIMEOUT=60
TIDY_LOG_LEVEL=warning
TIDY_LOG_JSON=False
TIDY_GC_MAX_CONTAINER_AGE=
TIDY_GC_MAX_IMAGE_AGE=
TIDY_GC_DANGLING_VOLUMES=False
# comma-separated list
TIDY_GC_EXCLUDE_IMAGES=
# comma-separated list
TIDY_GC_EXCLUDE_CONTAINER_LABELS=
TIDY_STOP_MAX_RUN_TIME=
# comma-separated list
TIDY_STOP_PREFIX=
{{< /highlight >}}
<!-- spellchecker-enable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

## CLI options

You can get all available CLI options by running `docker-tidy --help`:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- spellchecker-disable -->
{{< highlight Shell "linenos=table" >}}
$ docker-tidy --help
usage: docker-tidy [-h] [--dry-run] [-t HTTP_TIMEOUT] [-v] [-q] [--version]
                   {gc,stop} ...

keep docker hosts tidy

positional arguments:
  {gc,stop}             sub-command help
    gc                  run docker garbage collector
    stop                stop containers that have been running for too long

optional arguments:
  -h, --help            show this help message and exit
  --dry-run             only log actions, don't stop anything
  -t HTTP_TIMEOUT, --timeout HTTP_TIMEOUT
                        HTTP timeout in seconds for making docker API calls
  -v                    increase log level
  -q                    decrease log level
  --version             show program's version number and exit
{{< /highlight >}}
<!-- spellchecker-enable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
