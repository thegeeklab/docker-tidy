FROM python:3.8-alpine

LABEL maintainer="Robert Kaussow <mail@geeklabor.de>" \
    org.label-schema.name="docker-tidy" \
    org.label-schema.vcs-url="https://github.com/xoxys/docker-tidy" \
    org.label-schema.vendor="Robert Kaussow" \
    org.label-schema.schema-version="1.0"

ENV PY_COLORS=1
ENV TZ=UTC

ADD dist/docker_tidy-*.whl /

RUN \
    apk --update add --virtual .build-deps gcc g++ && \
    pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir docker_tidy-*.whl && \
    rm -f docker_tidy-*.whl && \
    apk del .build-deps && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/ && \
    rm -rf /tmp/*

USER root
CMD []
ENTRYPOINT ["/usr/local/bin/docker-tidy", "gc"]
