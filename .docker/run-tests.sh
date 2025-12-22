#!/bin/bash
# Script to run tests locally using Docker
# Usage: cd .docker && ./run-tests.sh [pytest args]

set -e

export GITHUB_WORKSPACE=$(dirname "$PWD")
docker compose -f docker-compose.gh.yml run --rm qgis /usr/src/AcATaMa/.docker/run-docker-tests.sh "$@"
docker compose -f docker-compose.gh.yml down
