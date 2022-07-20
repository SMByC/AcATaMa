import os
import pytest
from pathlib import Path
from qgis.testing import start_app

from AcATaMa import classFactory
from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget

pytest_plugins = ('pytest_qgis',)
pytest.tests_data_dir = Path(__file__).parent.resolve() / "data"

if os.environ.get("IS_DOCKER_CONTAINER") and os.environ["IS_DOCKER_CONTAINER"].lower()[
    0
] in ["t", "y", "1"]:
    # when running in a docker container, we use the start_app provided by qgis rather
    # than that of pytest-qgis. pytest-qgis does not cleanup the application properly
    # and results in a seg-fault
    start_app()


@pytest.fixture
def unwrap():
    def unwrapper(func):
        if not hasattr(func, '__wrapped__'):
            return func

        return unwrapper(func.__wrapped__)

    yield unwrapper


@pytest.fixture
def plugin(pytestconfig, qgis_iface, qgis_parent, qgis_new_project):
    """
    Initialize and return the plugin object.
    Resize the parent window according to config.
    """
    plugin = classFactory(qgis_iface)
    plugin.initGui()
    plugin.dockwidget = AcATaMaDockWidget()

    yield plugin
    plugin.removes_temporary_files()

