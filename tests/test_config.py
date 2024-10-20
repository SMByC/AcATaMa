import pytest

from AcATaMa.core import config


def compare_config_files(unwrap, tmpdir, input_yml_path):
    # restore
    config_restore = unwrap(config.restore)
    config_restore(input_yml_path)
    input_yml_file = open(input_yml_path, 'r')
    # save
    output_yml_file = tmpdir.join('acatama_config.yml')
    config_save = unwrap(config.save)
    config_save(output_yml_file.strpath)

    assert output_yml_file.read() == input_yml_file.read()


def disabled_test_restore_and_save_config_file(plugin, unwrap, tmpdir):
    yml_files = [pytest.tests_data_dir.parent.parent / "examples" / "Simple exercise - 2019-2020 change - Tinigua.yml"]

    for yml_file in yml_files:
        compare_config_files(unwrap, tmpdir, yml_file)
