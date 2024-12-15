import pytest

from AcATaMa.core import config


def test_get_n_calculates_correct_samples_simple(plugin, unwrap):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sample_size.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    # set values
    sampling_design.determine_number_samples_dialog_SimpRS.get_n()

    assert sampling_design.determine_number_samples_dialog_SimpRS.NumberOfSamples.text() == "306"

def test_point_spacing_calculates_correct_samples_systematic(plugin, unwrap, monkeypatch):
    # restore
    input_yml_path = pytest.tests_data_dir / "test_sample_size.yml"
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    sampling_design = plugin.dockwidget.sampling_design_window

    determine_number_samples_dialog = sampling_design.determine_number_samples_dialog_SystS

    # Replace QDialog.exec_ to always return QDialog.Accepted
    monkeypatch.setattr(determine_number_samples_dialog, "exec_", lambda: determine_number_samples_dialog.Accepted)
    sampling_design.determine_number_samples_dialog_SystS.get_n()

    assert sampling_design.PointSpacing_SystS.value() == 1028.9
