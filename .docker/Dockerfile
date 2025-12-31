ARG QGIS_TEST_VERSION=latest
FROM qgis/qgis:${QGIS_TEST_VERSION}

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml /tmp/
RUN pip3 install "/tmp/.[test]" --break-system-packages

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV IS_DOCKER_CONTAINER=true
ENV QT_QPA_PLATFORM=offscreen
ENV DISPLAY=:99

WORKDIR /
