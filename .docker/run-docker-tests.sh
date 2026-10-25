#!/usr/bin/env bash
# Script executed inside the Docker container to run pytest
# Usage: run-docker-tests.sh [pytest args]

set -e

cd /usr/src/AcATaMa

# pytest-qgis initializes QGIS itself, before the conftest files are imported. Skipping
# that initialization (--qgis_disable_init) while importing tests/conftest.py, which used
# to create the QgsApplication manually, aborts with a core dump on pytest-qgis >= 5.
DEFAULT_PARAMS='./tests/ -v --qgis_disable_gui --qgis_disable_exit'
xvfb-run pytest ${@:-$DEFAULT_PARAMS}
