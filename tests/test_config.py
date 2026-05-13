import pytest

from AcATaMa.core import config


def compare_config_files(restore_config_file, tmpdir, input_yml_path):
    # restore
    restore_config_file(input_yml_path)
    with open(input_yml_path) as f:
        input_yml_content = f.read()
    # save
    output_yml_file = tmpdir.join("acatama_config.yaml")
    config.save(output_yml_file.strpath)

    assert output_yml_file.read() == input_yml_content


def disabled_test_restore_and_save_config_file(restore_config_file, tmpdir):
    yml_files = [pytest.tests_data_dir.parent.parent / "examples" / "Simple exercise - 2019-2020 change - Tinigua.yaml"]

    for yml_file in yml_files:
        compare_config_files(restore_config_file, tmpdir, yml_file)
