"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2026 by Xavier C. Llano, SMByC
        email                : xavier.corredor.llano@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# This script consolidates the AcATaMa yaml files labeled independently by
# several interpreters over the same samples. A sample keeps the label chosen
# by a strict majority of the interpreters (at least 2 of 3), otherwise the
# sample is left unlabeled to be reviewed (e.g. by consensus).
#
# Example:
# $ python acatama_yamls_consolidate.py original.yaml 01.yaml 02.yaml 03.yaml
#                                       |             |       |       |
#                             (not labeled)   (files labeled by each interpreter)

import argparse
import os
from collections import Counter

import yaml

try:
    from yaml import CSafeDumper as SafeDumper
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeDumper, SafeLoader


class LegacyLoader(SafeLoader):
    """Safe loader that also reads the python tuples and ordered dicts of old AcATaMa files"""


LegacyLoader.add_constructor(
    "tag:yaml.org,2002:python/tuple", lambda loader, node: loader.construct_sequence(node, deep=True)
)
LegacyLoader.add_constructor(
    "tag:yaml.org,2002:python/object/apply:collections.OrderedDict",
    lambda loader, node: dict(loader.construct_sequence(node, deep=True)[0]),
)


def load_yaml(file_path):
    with open(file_path, encoding="utf-8") as yaml_file:
        return yaml.load(yaml_file, Loader=LegacyLoader)  # nosec B506 - LegacyLoader is a SafeLoader


def get_samples(yaml_config):
    """Labeled samples as {sample_id: label_id}, supporting the old AcATaMa key names"""
    samples = yaml_config.get("samples", yaml_config.get("points")) or {}
    labels = {}
    for sample in samples.values():
        sample_id = sample.get("sample_id", sample.get("shape_id"))
        label_id = sample.get("label_id", sample.get("classif_id"))
        if label_id is not None:
            labels[sample_id] = label_id
    return labels


def consolidate(labels_by_interpreter):
    """Keep the label of each sample chosen by a strict majority of the interpreters

    Args:
        labels_by_interpreter: list of {sample_id: label_id}, one dict by interpreter
    """
    sample_ids = sorted({sample_id for labels in labels_by_interpreter for sample_id in labels})
    consolidated = {}
    for sample_id in sample_ids:
        votes = Counter(labels[sample_id] for labels in labels_by_interpreter if sample_id in labels)
        label_id, count = votes.most_common(1)[0]
        if count > len(labels_by_interpreter) / 2:
            consolidated[sample_id] = label_id
    return consolidated


def script():
    """Run as a script with arguments"""
    parser = argparse.ArgumentParser(prog="acatama_yamls_consolidate", description="Consolidate AcATaMa yaml files")
    parser.add_argument("template", type=str, help="AcATaMa yaml file (not labeled) used as template")
    parser.add_argument("inputs", type=str, nargs="+", help="AcATaMa yaml files labeled by each interpreter")
    args = parser.parse_args()

    yaml_files = [os.path.abspath(f) for f in args.inputs if os.path.isfile(f) and f.endswith((".yml", ".yaml"))]
    if len(yaml_files) < 2:
        parser.error("at least two labeled yaml files are required")

    print(f"\nTEMPLATE FILE: {os.path.basename(args.template)}")
    print(f"\nCONSOLIDATING YAML FILES: {len(yaml_files)}")

    yml_template = load_yaml(args.template)
    labels_by_interpreter = [get_samples(load_yaml(yaml_file)) for yaml_file in yaml_files]
    consolidated = consolidate(labels_by_interpreter)

    all_sample_ids = {sample_id for labels in labels_by_interpreter for sample_id in labels}
    print(f"\nSamples with a majority label: {len(consolidated)} of {len(all_sample_ids)}")
    for sample_id in sorted(all_sample_ids - set(consolidated)):
        votes = [labels.get(sample_id) for labels in labels_by_interpreter]
        print(f"  sample {sample_id} left unlabeled, labels: {votes}")

    yml_template.pop("points", None)
    yml_template["samples"] = {
        idx: {"label_id": label_id, "sample_id": sample_id}
        for idx, (sample_id, label_id) in enumerate(consolidated.items())
    }

    output_file = os.path.splitext(args.template)[0] + "_consolidated.yaml"
    with open(output_file, "w", encoding="utf-8") as yaml_file:
        yaml.dump(yml_template, yaml_file, Dumper=SafeDumper, default_flow_style=False, sort_keys=False)

    print("saving: ", output_file)
    print("\nDONE")


if __name__ == "__main__":
    script()
