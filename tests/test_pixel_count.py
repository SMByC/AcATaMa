import os
import pytest
from osgeo import gdal

from AcATaMa.core import config
from AcATaMa.core.map import auto_symbology_classification_render
from AcATaMa.utils.others_utils import get_pixel_count_by_pixel_values, get_pixel_count_by_pixel_values_sequential, \
    get_pixel_count_by_pixel_values_parallel
from AcATaMa.utils.qgis_utils import load_layer


def test_pixel_count_without_nodata_sequential(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values_sequential(plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
                                                  band=2, nodata=None)

    assert pixel_count == {0: 3227, 34: 11, 35: 44, 36: 22, 37: 49, 38: 17, 40: 2, 42: 1, 43: 1,
                           44: 79, 45: 5, 46: 468, 47: 57, 49: 3, 51: 1, 52: 15, 53: 24}


def test_pixel_count_without_nodata_parallel(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values_parallel(plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
                                                  band=2, nodata=None)

    assert pixel_count == {0: 3227, 34: 11, 35: 44, 36: 22, 37: 49, 38: 17, 40: 2, 42: 1, 43: 1,
                           44: 79, 45: 5, 46: 468, 47: 57, 49: 3, 51: 1, 52: 15, 53: 24}


def test_pixel_count_with_nodata_sequential(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama_nodata.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    pixel_count = get_pixel_count_by_pixel_values_sequential(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
        band=int(sampling_design.QCBox_band_StratMap_StraRS.currentText()),
        nodata=float(sampling_design.nodata_StratMap_StraRS.text().strip() or "nan")
    )

    assert pixel_count == {1: 10423, 2: 418, 5: 8822}


def test_pixel_count_with_nodata_parallel(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama_nodata.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    pixel_count = get_pixel_count_by_pixel_values_parallel(
        plugin.dockwidget.QCBox_ThematicMap.currentLayer(),
        band=int(sampling_design.QCBox_band_StratMap_StraRS.currentText()),
        nodata=float(sampling_design.nodata_StratMap_StraRS.text().strip() or "nan")
    )

    assert pixel_count == {1: 10423, 2: 418, 5: 8822}


def test_pixel_count_and_auto_symbology(plugin, unwrap, tmpdir):
    # copy and unset the nodata
    layer_unsetnodata = tmpdir.join('test_layer_with_nodata.tif')
    gdal.Translate(str(layer_unsetnodata), str(pytest.tests_data_dir / "test_layer_with_nodata.tif"))
    os.system("gdal_edit.py '{}' -unsetnodata".format(layer_unsetnodata))

    layer = load_layer(str(layer_unsetnodata))
    auto_symbology_classification_render(layer, 1)
    pixel_count = get_pixel_count_by_pixel_values(layer, band=1, nodata="nan")

    assert pixel_count == {-2147483647: 15785, 1: 10423, 2: 418, 5: 8822}
