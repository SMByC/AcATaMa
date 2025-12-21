#!/usr/bin/env bash

set -e

pushd /usr/src/AcATaMa
DEFAULT_PARAMS='./tests/ -v --qgis_disable_gui --qgis_disable_init'
xvfb-run pytest ${@:-`echo $DEFAULT_PARAMS`}
popd
