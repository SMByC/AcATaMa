import importlib.util
import subprocess  # nosec B404 - runs the repository scripts in the tests
import sys

import pytest
import yaml

SCRIPTS_DIR = pytest.tests_data_dir.parent.parent / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


consolidate_script = load_script("acatama_yamls_consolidate")
merger_script = load_script("acatama_yamls_merger")


def write_config(path, samples, samples_order=None):
    config = {"general": {"config_file_version": 260100}, "samples": samples}
    if samples_order is not None:
        config["samples_order"] = samples_order
    path.write_text(yaml.safe_dump(config))
    return path


def test_consolidate_keeps_the_majority_label():
    labels = [{1: 3, 2: 1, 3: 2, 4: 5}, {1: 3, 2: 2, 3: 2}, {1: 1, 2: 3, 3: 4, 4: 5}]
    # sample 1: 2 of 3 agree on a label that is not the smallest one
    # sample 2: no agreement, sample 4: labeled by 2 of the 3 interpreters with the same label
    assert consolidate_script.consolidate(labels) == {1: 3, 3: 2, 4: 5}


def test_consolidate_requires_a_strict_majority():
    assert consolidate_script.consolidate([{1: 2}, {1: 2}, {1: 2}, {1: 2}]) == {1: 2}
    assert consolidate_script.consolidate([{1: 2}, {1: 2}, {1: 1}, {1: 1}]) == {}
    assert consolidate_script.consolidate([{1: 2}, {}, {}]) == {}


def test_get_samples_supports_legacy_config_files():
    legacy_config = consolidate_script.load_yaml(pytest.tests_data_dir / "test_samples_in_zero_and_outside.yaml")
    labels = consolidate_script.get_samples(legacy_config)
    assert labels
    assert all(isinstance(label_id, int) for label_id in labels.values())


def test_consolidate_script(tmp_path):
    template = write_config(tmp_path / "template.yaml", {}, [1, 2, 3])
    inputs = [
        write_config(tmp_path / f"{n}.yaml", {i: {"sample_id": s, "label_id": lb} for i, (s, lb) in enumerate(lbs)})
        for n, lbs in (("01", [(1, 3), (2, 1)]), ("02", [(1, 3), (2, 2)]), ("03", [(1, 1), (2, 3)]))
    ]
    subprocess.run(  # nosec B603 - fixed command with test files
        [sys.executable, SCRIPTS_DIR / "acatama_yamls_consolidate.py", template, *inputs],
        check=True,
        capture_output=True,
    )
    result = yaml.safe_load((tmp_path / "template_consolidated.yaml").read_text())
    assert list(result["samples"].values()) == [{"label_id": 3, "sample_id": 1}]
    assert result["samples_order"] == [1, 2, 3]


def test_merge_current_and_legacy_key_names():
    clip_1 = {"samples": {0: {"sample_id": 1, "label_id": 2}}, "samples_order": [1, 2]}
    clip_2 = {"points": {0: {"shape_id": 3, "classif_id": 1}, 1: {"shape_id": 1, "classif_id": 5}}, "points_order": [3]}
    samples, samples_order, conflicts = merger_script.merge([clip_1, clip_2])
    assert samples == {1: 2, 3: 1}
    assert samples_order == [1, 2, 3]
    assert conflicts == {1}


def test_merge_ignores_unlabeled_samples():
    clip_1 = {"samples": {0: {"sample_id": 1, "label_id": None}}}
    clip_2 = {"samples": {0: {"sample_id": 1, "label_id": 4}}}
    samples, _samples_order, conflicts = merger_script.merge([clip_1, clip_2])
    assert samples == {1: 4}
    assert not conflicts


def test_merger_script(tmp_path):
    template = write_config(tmp_path / "template.yaml", {}, [1, 2, 3, 4])
    clip_1 = write_config(tmp_path / "clip_1.yaml", {0: {"sample_id": 1, "label_id": 2}}, [1, 2])
    clip_2 = write_config(tmp_path / "clip_2.yaml", {0: {"sample_id": 3, "label_id": 1}}, [3, 4])
    subprocess.run(  # nosec B603 - fixed command with test files
        [sys.executable, SCRIPTS_DIR / "acatama_yamls_merger.py", template, clip_1, clip_2],
        check=True,
        capture_output=True,
    )
    result = yaml.safe_load((tmp_path / "template_merged.yaml").read_text())
    assert sorted((s["sample_id"], s["label_id"]) for s in result["samples"].values()) == [(1, 2), (3, 1)]
    assert result["samples_order"] == [1, 2, 3, 4]
