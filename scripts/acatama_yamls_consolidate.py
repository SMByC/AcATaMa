# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2023 by Xavier C. Llano, SMByC
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

# This script consolidate different AcATaMa yaml saved files.
# The general purpose is consolidated 3 yml files Full
# labeled, the result let the label in where
# at least 2 (or 3) interpreters coincide, the samples
# where the 3 interpreters set different labels
# the label of the sample is removed (as unlabeled)
#
# Example:
# $ python acatama_yamls_consolidate.py original_yml.yml 01.yml 02.yml ...
#                                       |             |       |
#                             (not labeled) (individual files labeled)

import argparse
import os
import itertools
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def script():
    """Run as a script with arguments
    """
    parser = argparse.ArgumentParser(
        prog='acatama_yamls_consolidate',
        description='Consolidate AcATaMa yml files')

    parser.add_argument('inputs', type=str, nargs='*')
    args = parser.parse_args()

    yaml_files = []
    for _input in args.inputs:
        if os.path.isfile(_input) and _input.endswith('.yml'):
            yaml_files.append(os.path.abspath(_input))

    print("\nTEMPLATE FILE: {}".format(os.path.basename(yaml_files[0])))
    print("\nCONSOLIDATING YAMLS FILES: {}".format(len(yaml_files)-1))

    samples = []
    yml_template = None
    for yaml_file_path in yaml_files:
        with open(yaml_file_path, 'r') as yaml_file:
            yaml_config = yaml.load(yaml_file, Loader=Loader)
            if yml_template is None:
                yml_template = yaml_config
                continue
            samples += yaml_config["samples"].values()
    
    print(samples)
    # consolidate
    samples_consolidated = []
    samples = sorted(samples, key=lambda samples: samples['sample_id'])
    for key, group in itertools.groupby(samples, lambda samples: samples['sample_id']):
        group = list(group)
        print(key, " :", group)
        # pass control rule: 2 of 3 have the same label_id, else unlabeled
        group_label_id = [x['label_id'] for x in group]
        group_label_id.sort(reverse=True)
        counts, label_id = [(group_label_id.count(x), x) for x in set(group_label_id)][0]
        
        if counts in [2, 3]:
            samples_consolidated.append({'label_id': label_id, 'sample_id': key})
        
    yml_template["samples"] = {x: p for x, p in zip(range(len(samples_consolidated)), samples_consolidated)}

    with open(os.path.splitext(yaml_files[0])[0] + "_consolidated.yml", 'w') as yaml_file:
        yaml.dump(yml_template, yaml_file, Dumper=Dumper)

    print("saving: ", os.path.splitext(yaml_files[0])[0] + "_consolidated.yml")
    print("\nDONE")


if __name__ == '__main__':
    script()
