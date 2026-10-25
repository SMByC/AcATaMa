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

# This script merge different AcATaMa yaml saved files.
# The general purpose is when you have a big sample file,
# you clip/divide it in multiples sample files with the idea
# that different people can help to label it. When all
# individual files are ready (labeled) run this script
# to merge all yamls files in one, then you can load it
# again in AcATaMa and you can get the result of accuracy
# assessment of the original yaml of the big sample file.
#
# Example:
# $ python acatama_yamls_merger.py original.yaml clip_01.yaml clip_02.yaml ...
#                                         |              |           |
#                                 (not labeled) (individual files labeled)

import argparse
import os

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


def merge(yaml_configs):
    """Merge the labeled samples and the samples order of the clips, a sample in several clips
    keeps the first label found

    Returns:
        (samples, samples_order, conflicts) where conflicts are the sample ids with different labels
    """
    samples = {}
    samples_order = []
    conflicts = set()
    for yaml_config in yaml_configs:
        for sample in (yaml_config.get("samples", yaml_config.get("points")) or {}).values():
            sample_id = sample.get("sample_id", sample.get("shape_id"))
            label_id = sample.get("label_id", sample.get("classif_id"))
            if label_id is None:
                continue
            if sample_id in samples:
                if samples[sample_id] != label_id:
                    conflicts.add(sample_id)
                continue
            samples[sample_id] = label_id
        for sample_id in yaml_config.get("samples_order", yaml_config.get("points_order")) or []:
            if sample_id not in samples_order:
                samples_order.append(sample_id)
    return samples, samples_order, conflicts


def script():
    """Run as a script with arguments"""
    parser = argparse.ArgumentParser(prog="acatama_yamls_merger", description="Merge AcATaMa yaml files")
    parser.add_argument("template", type=str, help="AcATaMa yaml file (not labeled) used as template")
    parser.add_argument("inputs", type=str, nargs="+", help="AcATaMa yaml files of the clips labeled")
    args = parser.parse_args()

    yaml_files = [os.path.abspath(f) for f in args.inputs if os.path.isfile(f) and f.endswith((".yml", ".yaml"))]
    if not yaml_files:
        parser.error("no labeled yaml files found")

    print(f"\nTEMPLATE FILE: {os.path.basename(args.template)}")
    print(f"\nMERGING YAML FILES: {len(yaml_files)}")

    yml_template = load_yaml(args.template)
    samples, samples_order, conflicts = merge([load_yaml(yaml_file) for yaml_file in yaml_files])
    for sample_id in sorted(conflicts):
        print(f"  warning: the sample {sample_id} has different labels in the clips, the first one is kept")

    yml_template.pop("points", None)
    yml_template.pop("points_order", None)
    yml_template["samples"] = {
        idx: {"label_id": label_id, "sample_id": sample_id} for idx, (sample_id, label_id) in enumerate(samples.items())
    }
    yml_template["samples_order"] = samples_order

    output_file = os.path.splitext(args.template)[0] + "_merged.yaml"
    with open(output_file, "w", encoding="utf-8") as yaml_file:
        yaml.dump(yml_template, yaml_file, Dumper=SafeDumper, default_flow_style=False, sort_keys=False)

    print("saving: ", output_file)
    print("\nDONE")


if __name__ == "__main__":
    script()
