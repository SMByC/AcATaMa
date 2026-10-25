import pytest
from osgeo import gdal
from qgis.PyQt.QtWidgets import QDialog


def test_get_n_calculates_correct_samples_simple(plugin, restore_config_file):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sample_size.yaml"
    restore_config_file(input_yml_path)

    sampling_design = plugin.dockwidget.sampling_design_window

    # set values
    sampling_design.determine_number_samples_dialog_SimpRS.get_n()

    # n = 1.96^2 * 0.85 * 0.15 / 0.04^2 = 306.13, rounded up to reach the half-width of the interval
    assert sampling_design.determine_number_samples_dialog_SimpRS.NumberOfSamples.text() == "307"


def test_point_spacing_calculates_correct_samples_systematic(plugin, restore_config_file, monkeypatch):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sample_size.yaml"
    restore_config_file(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    determine_number_samples_dialog = sampling_design.determine_number_samples_dialog_SystS
    # n = 1.44^2 * 0.9 * 0.1 / 0.03^2 = 207.36, rounded up
    determine_number_samples_dialog.get_n()
    assert determine_number_samples_dialog.NumberOfSamples.text() == "208"

    # Replace QDialog.exec to always return QDialog.Accepted
    monkeypatch.setattr(determine_number_samples_dialog, "exec", lambda: QDialog.DialogCode.Accepted)
    sampling_design.determine_number_samples_SystS()

    # the expected number of samples of a systematic grid with a random start is the valid area / spacing^2
    dataset = gdal.Open(str(pytest.tests_data_dir / "test_stack.tif"))
    valid_pixels = int((dataset.GetRasterBand(2).ReadAsArray() != 0).sum())
    pixel_size = dataset.GetGeoTransform()[1]
    expected_spacing = (valid_pixels / 208) ** 0.5 * pixel_size
    assert sampling_design.QCBox_Systematic_Sampling_Unit.currentText() == "Distance"
    assert sampling_design.PointSpacing_SystS.value() == pytest.approx(expected_spacing, abs=0.1)
