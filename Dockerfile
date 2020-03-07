FROM python:3.8-alpine

LABEL maintainer="Robert Kaussow <mail@geeklabor.de>" \
    org.label-schema.name="docker-tidy" \
    org.label-schema.vcs-url="https://github.com/xoxys/docker-tidy" \
    org.label-schema.vendor="Robert Kaussow" \
    org.label-schema.schema-version="1.0"

ENV PY_COLORS=1

ADD dist/docker_tidy-*.whl /

RUN \
    apk update --no-cache && \
    rm -rf /var/cache/apk/* && \
    pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir --find-links=. docker-tidy && \
    rm -f docker_tidy-*.whl && \
    rm -rf /root/.cache/

USER root
CMD []
ENTRYPOINT ["/usr/local/bin/docker-tidy"]
