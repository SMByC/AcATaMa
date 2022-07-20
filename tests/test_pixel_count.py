import pytest


def test_pixel_count(plugin, unwrap):
    from AcATaMa.core import config
    from AcATaMa.utils.others_utils import get_pixel_count_by_pixel_values

    # restore
    input_yml_path = pytest.tests_data_dir / "test_pixel_count_acatama.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)

    pixel_count = get_pixel_count_by_pixel_values(plugin.dockwidget.QCBox_ThematicMap.currentLayer(), band=2, nodata=None)

    assert pixel_count == {0: 3227, 34: 11, 35: 44, 36: 22, 37: 49, 38: 17, 40: 2, 42: 1, 43: 1,
                           44: 79, 45: 5, 46: 468, 47: 57, 49: 3, 51: 1, 52: 15, 53: 24}

