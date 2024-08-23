#!/bin/bash

export GITHUB_WORKSPACE=$PWD
docker compose -f docker-compose.gh.yml run qgis /usr/src/AcATaMa/.docker/run-docker-tests.sh $@
docker compose -f docker-compose.gh.yml rm -s -f
