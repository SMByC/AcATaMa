ARG QGIS_TEST_VERSION=latest
FROM  qgis/qgis:${QGIS_TEST_VERSION}

RUN apt-get update && \
    apt-get install -y python3-pip

COPY ./pyproject.toml /tmp/
RUN pip3 install "/tmp/[test]" --break-system-packages

ENV LANG=C.UTF-8
ENV IS_DOCKER_CONTAINER=true

WORKDIR /
