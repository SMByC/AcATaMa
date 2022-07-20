from pathlib import Path
import pytest


pytest_plugins = ('pytest_qgis',)

pytest.tests_data_dir = Path(__file__).parent.resolve() / "data"


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
    from AcATaMa import classFactory
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget

    plugin = classFactory(qgis_iface)
    plugin.initGui()
    plugin.dockwidget = AcATaMaDockWidget()

    yield plugin
    plugin.removes_temporary_files()

