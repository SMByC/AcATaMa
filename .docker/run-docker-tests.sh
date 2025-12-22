#!/usr/bin/env bash
# Script executed inside the Docker container to run pytest
# Usage: run-docker-tests.sh [pytest args]

set -e

cd /usr/src/AcATaMa

DEFAULT_PARAMS='./tests/ -v --qgis_disable_gui --qgis_disable_init'
xvfb-run pytest ${@:-$DEFAULT_PARAMS}
