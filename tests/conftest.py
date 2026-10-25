import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from AcATaMa import classFactory
from AcATaMa.core import config
from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget

pytest_plugins = ("pytest_qgis",)
pytest.tests_data_dir = Path(__file__).parent.resolve() / "data"

# pytest-qgis owns the QgsApplication lifecycle. Since pytest-qgis 5.0.1 it creates the
# application before importing the initial conftest files, so creating it here as well
# (with qgis.testing.start_app) would conflict with the widgets that pytest-qgis has
# already created. In Docker the process is force-exited at the end of the session to
# avoid the Qt/OpenGL cleanup segfault.
_is_docker = os.environ.get("IS_DOCKER_CONTAINER", "")[:1].lower() in ("t", "y", "1")


def pytest_sessionfinish(session, exitstatus):
    """Force-exit after tests complete in Docker to avoid the Qt/OpenGL cleanup segfault."""
    if _is_docker:
        os._exit(exitstatus)


@pytest.fixture
def unwrap():
    def unwrapper(func):
        if not hasattr(func, "__wrapped__"):
            return func

        return unwrapper(func.__wrapped__)

    yield unwrapper


@pytest.fixture
def restore_config_file(monkeypatch):
    mock_iface = MagicMock()
    monkeypatch.setattr("AcATaMa.core.config.iface", mock_iface)
    monkeypatch.setattr("AcATaMa.utils.system_utils.iface", mock_iface)

    def _load_config_file(input_yml_path):
        config.restore(input_yml_path)

    return _load_config_file


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


@pytest.fixture
def make_raster(tmp_path):
    """Create a single band raster of 1x1 m pixels from an array, with a paletted symbology (of all its values
    or the ones given) and load it in the project"""
    import numpy as np
    from osgeo import gdal, gdal_array, osr
    from qgis.core import QgsPalettedRasterRenderer, QgsProject, QgsRasterLayer
    from qgis.PyQt.QtGui import QColor

    def _make_raster(data, nodata=None, styled_values=None, name="map", data_type=gdal.GDT_Byte, crs=None):
        data = np.asarray(data, dtype=gdal_array.GDALTypeCodeToNumericTypeCode(data_type))
        path = tmp_path / f"{name}.tif"
        dataset = gdal.GetDriverByName("GTiff").Create(str(path), data.shape[1], data.shape[0], 1, data_type)
        dataset.SetGeoTransform((500000, 1, 0, 1000000, 0, -1))
        spatial_reference = osr.SpatialReference()
        if crs is None:
            spatial_reference.ImportFromEPSG(32618)
        else:
            spatial_reference.ImportFromProj4(crs)
        dataset.SetProjection(spatial_reference.ExportToWkt())
        dataset.GetRasterBand(1).WriteArray(data)
        if nodata is not None:
            dataset.GetRasterBand(1).SetNoDataValue(nodata)
        dataset = None
        layer = QgsRasterLayer(str(path), name)
        values = np.unique(data).tolist() if styled_values is None else styled_values
        classes = [QgsPalettedRasterRenderer.Class(value, QColor("red"), str(value)) for value in values]
        layer.setRenderer(QgsPalettedRasterRenderer(layer.dataProvider(), 1, classes))
        QgsProject.instance().addMapLayer(layer)
        return layer

    return _make_raster
