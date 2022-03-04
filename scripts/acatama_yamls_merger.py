# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2021 by Xavier Corredor Llano, SMByC
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
# $ python acatama_yamls_merger.py original_yml.yml clip_01.yml clip_02.yml ...
#                                         |              |           |
#                                 (not labeled) (individual files labeled)

import argparse
import os
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def script():
    """Run as a script with arguments
    """
    parser = argparse.ArgumentParser(
        prog='acatama_yamls_merger',
        description='Merge AcATaMa yml files')

    parser.add_argument('inputs', type=str, nargs='*')
    args = parser.parse_args()

    yaml_files = []
    for _input in args.inputs:
        if os.path.isfile(_input) and _input.endswith('.yml'):
            yaml_files.append(os.path.abspath(_input))

    print("\nTEMPLATE FILE: {}".format(os.path.basename(yaml_files[0])))
    print("\nMERGING YAMLS FILES: {}".format(len(yaml_files)-1))

    points = []
    points_order = []
    yml_template = None
    for yaml_file_path in yaml_files:
        with open(yaml_file_path, 'r') as yaml_file:
            yaml_config = yaml.load(yaml_file, Loader=Loader)

            if yml_template is None:
                yml_template = yaml_config
                continue

            points += yaml_config["points"].values()
            points_order += yaml_config["points_order"]

    points_merged = {x: p for x, p in zip(range(len(points)), points)}

    yml_template["points"] = points_merged
    yml_template["points_order"] = points_order

    with open(os.path.splitext(yaml_files[0])[0] + "_merged.yml", 'w') as yaml_file:
        yaml.dump(yml_template, yaml_file, Dumper=Dumper)

    print("saving: ", os.path.splitext(yaml_files[0])[0] + "_merged.yml")
    print("\nDONE")

if __name__ == '__main__':
    script()
