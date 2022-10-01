# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2022 by Xavier C. Llano, SMByC
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
import os
import re
from collections import OrderedDict
import yaml

from AcATaMa.gui.generate_sampling_widget import SelectCategoricalMapClasses
from AcATaMa.gui.response_design_window import ResponseDesignWindow

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from qgis.core import Qgis, QgsUnitTypes
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.system_utils import wait_process, block_signals_to
from AcATaMa.utils.sampling_utils import fill_stratified_sampling_table
from AcATaMa.utils.qgis_utils import get_current_file_path_in, get_file_path_of_layer, load_and_select_filepath_in, \
    select_item_in
from AcATaMa.utils.others_utils import set_nodata_format

CONFIG_FILE_VERSION = None


@wait_process
def save(file_out):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    from AcATaMa.gui.acatama_dockwidget import VERSION

    def setup_yaml():
        """
        Keep dump ordered with orderedDict
        """
        represent_dict_order = lambda self, data: self.represent_mapping('tag:yaml.org,2002:map',
                                                                         list(data.items()))
        yaml.add_representer(OrderedDict, represent_dict_order)

    setup_yaml()

    data = OrderedDict()

    # ######### general configuration ######### #
    data["general"] = \
        {"config_file_version": int(''.join(['{:0>2}'.format(re.sub('\D', '', x)) for x in VERSION.split('.')])),
         "tab_activated": AcATaMa.dockwidget.tabWidget.currentIndex()}

    # ######### thematic ######### #
    data["thematic_map"] = \
        {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicMap, show_message=False),
         "band": int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
            if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText() != '' else -1,
         "nodata": AcATaMa.dockwidget.nodata_ThematicMap.text()}

    # ######### sampling design ######### #
    data["sampling_design"] = {}
    data["sampling_design"]["tab_activated"] = AcATaMa.dockwidget.tabs_SamplingStrategy.currentIndex()
    # simple random sampling
    data["sampling_design"]["simple_random_sampling"] = {
        "num_samples": AcATaMa.dockwidget.numberOfSamples_SimpRS.value(),
        "min_distance": AcATaMa.dockwidget.minDistance_SimpRS.value(),

        "post_stratify": AcATaMa.dockwidget.QGBox_SimpRSwithCR.isChecked(),
        "categ_map_path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_CategMap_SimpRS, show_message=False),
        "categ_map_band": int(AcATaMa.dockwidget.QCBox_band_CategMap_SimpRS.currentText())
            if AcATaMa.dockwidget.QCBox_band_CategMap_SimpRS.currentText() != '' else -1,
        "classes_selected_for_sampling": AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SimpRS.text(),

        "with_neighbors_aggregation": AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.isChecked(),
        "num_neighbors": AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors.currentText(),
        "min_neighbors_with_the_same_class": AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors.currentText(),
        "random_sampling_options": AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_random_sampling_options.isChecked(),
        "automatic_random_seed": AcATaMa.dockwidget.widget_generate_SimpRS.automatic_random_seed.isChecked(),
        "with_random_seed_by_user": AcATaMa.dockwidget.widget_generate_SimpRS.with_random_seed_by_user.isChecked(),
        "random_seed_by_user": AcATaMa.dockwidget.widget_generate_SimpRS.random_seed_by_user.text(),
    }
    # stratified random sampling
    srs_method = "fixed values" if AcATaMa.dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values") \
        else "area based proportion"
    with_srs_table = AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentText() in AcATaMa.dockwidget.srs_tables and \
        srs_method in AcATaMa.dockwidget.srs_tables[AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentText()]
    data["sampling_design"]["stratified_random_sampling"] = {
        "categ_map_path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_CategMap_StraRS, show_message=False),
        "categ_map_band": int(AcATaMa.dockwidget.QCBox_band_CategMap_StraRS.currentText())
            if AcATaMa.dockwidget.QCBox_band_CategMap_StraRS.currentText() != '' else -1,
        "categ_map_nodata": AcATaMa.dockwidget.nodata_CategMap_StraRS.text(),

        "sampling_random_method": AcATaMa.dockwidget.QCBox_StraRS_Method.currentText(),
        "overall_std_error": AcATaMa.dockwidget.TotalExpectedSE.value(),
        "stratified_random_sampling_table": AcATaMa.dockwidget.srs_tables
            [AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentText()][srs_method] if with_srs_table else None,

        # TODO:
        # save the values color table of the QCBox_CategMap_StraRS

        "min_distance": AcATaMa.dockwidget.minDistance_StraRS.value(),
        "with_neighbors_aggregation": AcATaMa.dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.isChecked(),
        "num_neighbors": AcATaMa.dockwidget.widget_generate_StraRS.QCBox_NumberOfNeighbors.currentText(),
        "min_neighbors_with_the_same_class": AcATaMa.dockwidget.widget_generate_StraRS.QCBox_SameClassOfNeighbors.currentText(),
        "random_sampling_options": AcATaMa.dockwidget.widget_generate_StraRS.QGBox_random_sampling_options.isChecked(),
        "automatic_random_seed": AcATaMa.dockwidget.widget_generate_StraRS.automatic_random_seed.isChecked(),
        "with_random_seed_by_user": AcATaMa.dockwidget.widget_generate_StraRS.with_random_seed_by_user.isChecked(),
        "random_seed_by_user": AcATaMa.dockwidget.widget_generate_StraRS.random_seed_by_user.text(),
    }
    # systematic sampling
    data["sampling_design"]["systematic_sampling"] = {
        "points_spacing": AcATaMa.dockwidget.PointsSpacing_SystS.value(),
        "initial_inset": AcATaMa.dockwidget.InitialInset_SystS.value(),
        "max_xy_offset": AcATaMa.dockwidget.MaxXYoffset_SystS.value(),

        "post_stratify": AcATaMa.dockwidget.QGBox_SystSwithCR.isChecked(),
        "categ_map_path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_CategMap_SystS, show_message=False),
        "categ_map_band": int(AcATaMa.dockwidget.QCBox_band_CategMap_SystS.currentText())
        if AcATaMa.dockwidget.QCBox_band_CategMap_SystS.currentText() != '' else -1,
        "classes_selected_for_sampling": AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SystS.text(),
        "with_neighbors_aggregation": AcATaMa.dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.isChecked(),
        "num_neighbors": AcATaMa.dockwidget.widget_generate_SystS.QCBox_NumberOfNeighbors.currentText(),
        "min_neighbors_with_the_same_class": AcATaMa.dockwidget.widget_generate_SystS.QCBox_SameClassOfNeighbors.currentText(),
        "random_sampling_options": AcATaMa.dockwidget.widget_generate_SystS.QGBox_random_sampling_options.isChecked(),
        "automatic_random_seed": AcATaMa.dockwidget.widget_generate_SystS.automatic_random_seed.isChecked(),
        "with_random_seed_by_user": AcATaMa.dockwidget.widget_generate_SystS.with_random_seed_by_user.isChecked(),
        "random_seed_by_user": AcATaMa.dockwidget.widget_generate_SystS.random_seed_by_user.text(),
    }

    # ######### response design configuration ######### #
    sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
    if sampling_layer in ResponseDesign.instances:
        response_design = ResponseDesign.instances[sampling_layer]
        data["sampling_layer"] = get_file_path_of_layer(response_design.sampling_layer)
        # TODO:
        # save sampling_layer style

        data["dialog_size"] = response_design.dialog_size
        data["grid_view_widgets"] = {"columns": response_design.grid_columns, "rows": response_design.grid_rows}
        data["current_sample_idx"] = response_design.current_sample_idx
        data["sampling_unit_pixel_buffer"] = response_design.sampling_unit_pixel_buffer
        data["sampling_unit_color"] = response_design.sampling_unit_color.name()
        data["fit_to_sample"] = response_design.fit_to_sample
        data["is_completed"] = response_design.is_completed
        data["view_widgets_config"] = response_design.view_widgets_config
        data["labeling_buttons"] = response_design.buttons_config
        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(response_design.points):
            if point.is_labeled:
                points_config[pnt_idx] = {"label_id": point.label_id, "sample_id": point.sample_id}
        data["samples"] = points_config
        # save the samples order
        data["samples_order"] = [p.sample_id for p in response_design.points]
    else:
        response_design = None

    # ######### accuracy assessment ######### #
    data["analysis"] = {}
    data["analysis"]["sampling_file"] = get_current_file_path_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                                                 show_message=False)
    data["analysis"]["sampling_type"] = AcATaMa.dockwidget.QCBox_SamplingEstimator_A.currentIndex()
    # save config of the accuracy assessment dialog if exists
    if response_design and response_design.analysis:
        data["analysis"]["accuracy_assessment"] = {
            "area_unit": QgsUnitTypes.toString(response_design.analysis.area_unit),
            "z_score": response_design.analysis.z_score,
            "csv_separator": response_design.analysis.csv_separator,
            "csv_decimal": response_design.analysis.csv_decimal,
        }

    with open(file_out, 'w') as yaml_file:
        yaml.dump(data, yaml_file, Dumper=Dumper)


@wait_process
def restore(yml_file_path):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # load the yaml file
    with open(yml_file_path, 'r') as yaml_file:
        try:
            yaml_config = yaml.load(yaml_file, Loader=Loader)
        except yaml.YAMLError as err:
            iface.messageBar().pushMessage("AcATaMa", "Error while read the AcATaMa configuration file: {}".format(err),
                                           level=Qgis.Critical)
            return

    # clear some stuff
    SelectCategoricalMapClasses.instances = {}
    ResponseDesign.instances = {}
    ResponseDesignWindow.instance = None

    def get_restore_path(_path):
        """check if the file path exists or try using relative path to the yml file"""
        if _path is None:
            return None
        if not os.path.isfile(_path):
            _path = os.path.join(os.path.dirname(yml_file_path), _path)
        return os.path.abspath(_path)

    # ######### general configuration ######### #
    global CONFIG_FILE_VERSION
    if "general" in yaml_config and "config_file_version" in yaml_config["general"]:
        CONFIG_FILE_VERSION = yaml_config["general"]["config_file_version"]
    else:
        CONFIG_FILE_VERSION = 191121  # v19.11.21

    if "general" in yaml_config:
        AcATaMa.dockwidget.tabWidget.setCurrentIndex(yaml_config["general"]["tab_activated"])

    # support load the old format of config file TODO: deprecated, legacy config input
    if "thematic_raster" in yaml_config:
        yaml_config["thematic_map"] = yaml_config.pop("thematic_raster")
    if "classification_buttons" in yaml_config:
        yaml_config["labeling_buttons"] = yaml_config.pop("classification_buttons")
    if "points" in yaml_config:
        yaml_config["samples"] = yaml_config.pop("points")
    if "points_order" in yaml_config:
        yaml_config["samples_order"] = yaml_config.pop("points_order")
    if "accuracy_assessment" in yaml_config:
        yaml_config["analysis"] = yaml_config.pop("accuracy_assessment")
    if "analysis" in yaml_config and "dialog" in yaml_config["analysis"]:
        yaml_config["analysis"]["accuracy_assessment"] = yaml_config["analysis"].pop("dialog")

    # restore the thematic map
    if yaml_config["thematic_map"]["path"]:
        # thematic map
        load_status = load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_ThematicMap,
                                                  get_restore_path(yaml_config["thematic_map"]["path"]))
        if not load_status:
            return
        AcATaMa.dockwidget.select_thematic_map(AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer())
        # band number
        if "band" in yaml_config["thematic_map"]:
            AcATaMa.dockwidget.QCBox_band_ThematicMap.setCurrentIndex(yaml_config["thematic_map"]["band"] - 1)
        # nodata
        nodata = set_nodata_format(yaml_config["thematic_map"]["nodata"])
        if CONFIG_FILE_VERSION <= 191121 and nodata == "-1":
            AcATaMa.dockwidget.nodata_ThematicMap.setText("nan")
        else:
            AcATaMa.dockwidget.nodata_ThematicMap.setText(nodata)

    # ######### sampling design configuration ######### #
    if "sampling_design" in yaml_config:
        AcATaMa.dockwidget.tabs_SamplingStrategy.setCurrentIndex(yaml_config["sampling_design"]["tab_activated"])

        # simple random sampling
        AcATaMa.dockwidget.numberOfSamples_SimpRS.setValue(
            yaml_config["sampling_design"]["simple_random_sampling"]['num_samples'])
        AcATaMa.dockwidget.minDistance_SimpRS.setValue(
            yaml_config["sampling_design"]["simple_random_sampling"]['min_distance'])
        AcATaMa.dockwidget.QGBox_SimpRSwithCR.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['post_stratify'])
        AcATaMa.dockwidget.widget_SimpRSwithCR.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['post_stratify'])
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_CategMap_SimpRS,
                                    get_restore_path(yaml_config["sampling_design"]["simple_random_sampling"]['categ_map_path']))
        AcATaMa.dockwidget.select_categorical_map_SimpRS()
        AcATaMa.dockwidget.QCBox_band_CategMap_SimpRS.setCurrentIndex(
            yaml_config["sampling_design"]["simple_random_sampling"]['categ_map_band'] - 1)
        AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SimpRS.setText(
            yaml_config["sampling_design"]["simple_random_sampling"]['classes_selected_for_sampling'])

        AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_neighbors_aggregation'])
        AcATaMa.dockwidget.widget_generate_SimpRS.widget_neighbour_aggregation.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_neighbors_aggregation'])
        select_item_in(AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors,
                       yaml_config["sampling_design"]["simple_random_sampling"]['num_neighbors'])
        select_item_in(AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors,
                       yaml_config["sampling_design"]["simple_random_sampling"]['min_neighbors_with_the_same_class'])
        AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_random_sampling_options.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_sampling_options'])
        AcATaMa.dockwidget.widget_generate_SimpRS.widget_random_sampling_options.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_sampling_options'])
        AcATaMa.dockwidget.widget_generate_SimpRS.automatic_random_seed.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['automatic_random_seed'])
        AcATaMa.dockwidget.widget_generate_SimpRS.with_random_seed_by_user.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_random_seed_by_user'])
        AcATaMa.dockwidget.widget_generate_SimpRS.random_seed_by_user.setText(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_seed_by_user'])

        # stratified random sampling
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_CategMap_StraRS,
                                    get_restore_path(yaml_config["sampling_design"]["stratified_random_sampling"]['categ_map_path']))
        AcATaMa.dockwidget.select_categorical_map_StraRS(AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentLayer())
        AcATaMa.dockwidget.QCBox_band_CategMap_StraRS.setCurrentIndex(
            yaml_config["sampling_design"]["stratified_random_sampling"]['categ_map_band'] - 1)
        # nodata
        nodata = set_nodata_format(yaml_config["sampling_design"]["stratified_random_sampling"]["categ_map_nodata"])
        if CONFIG_FILE_VERSION <= 191121 and nodata == "-1":
            AcATaMa.dockwidget.nodata_CategMap_StraRS.setText("nan")
        else:
            AcATaMa.dockwidget.nodata_CategMap_StraRS.setText(nodata)

        with block_signals_to(AcATaMa.dockwidget.QCBox_StraRS_Method):
            select_item_in(AcATaMa.dockwidget.QCBox_StraRS_Method,
                           yaml_config["sampling_design"]["stratified_random_sampling"]['sampling_random_method'])
        with block_signals_to(AcATaMa.dockwidget.TotalExpectedSE):
            AcATaMa.dockwidget.TotalExpectedSE.setValue(
                yaml_config["sampling_design"]["stratified_random_sampling"]['overall_std_error'])

        srs_table = yaml_config["sampling_design"]["stratified_random_sampling"]['stratified_random_sampling_table']
        srs_method = "fixed values" if AcATaMa.dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values") \
            else "area based proportion"
        AcATaMa.dockwidget.srs_tables[AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentText()] = {}
        AcATaMa.dockwidget.srs_tables[AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentText()][srs_method] = srs_table
        fill_stratified_sampling_table(AcATaMa.dockwidget)
        # restore the pixel count by pixel value
        if srs_table and 'pixel_count' in srs_table:
            from AcATaMa.utils.others_utils import storage_pixel_count_by_pixel_values
            global storage_pixel_count_by_pixel_values
            storage_pixel_count_by_pixel_values[
                (AcATaMa.dockwidget.QCBox_CategMap_StraRS.currentLayer(),
                 int(AcATaMa.dockwidget.QCBox_band_CategMap_StraRS.currentText()),
                 set_nodata_format(AcATaMa.dockwidget.nodata_CategMap_StraRS.text().strip() or "nan"))
            ] = dict(zip(srs_table['values_and_colors_table']['Pixel Value'], srs_table['pixel_count']))

        # TODO:
        # restore the values color table of the QCBox_CategMap_StraRS saved

        AcATaMa.dockwidget.minDistance_StraRS.setValue(
            yaml_config["sampling_design"]["stratified_random_sampling"]['min_distance'])
        AcATaMa.dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_neighbors_aggregation'])
        AcATaMa.dockwidget.widget_generate_StraRS.widget_neighbour_aggregation.setVisible(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_neighbors_aggregation'])
        select_item_in(AcATaMa.dockwidget.widget_generate_StraRS.QCBox_NumberOfNeighbors,
                       yaml_config["sampling_design"]["stratified_random_sampling"]['num_neighbors'])
        select_item_in(AcATaMa.dockwidget.widget_generate_StraRS.QCBox_SameClassOfNeighbors,
                       yaml_config["sampling_design"]["stratified_random_sampling"]['min_neighbors_with_the_same_class'])
        AcATaMa.dockwidget.widget_generate_StraRS.QGBox_random_sampling_options.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_sampling_options'])
        AcATaMa.dockwidget.widget_generate_StraRS.widget_random_sampling_options.setVisible(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_sampling_options'])
        AcATaMa.dockwidget.widget_generate_StraRS.automatic_random_seed.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['automatic_random_seed'])
        AcATaMa.dockwidget.widget_generate_StraRS.with_random_seed_by_user.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_random_seed_by_user'])
        AcATaMa.dockwidget.widget_generate_StraRS.random_seed_by_user.setText(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_seed_by_user'])

        # systematic sampling
        if "systematic_sampling" in yaml_config["sampling_design"]:
            AcATaMa.dockwidget.PointsSpacing_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['points_spacing'])
            AcATaMa.dockwidget.InitialInset_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['initial_inset'])
            AcATaMa.dockwidget.MaxXYoffset_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['max_xy_offset'])

            AcATaMa.dockwidget.QGBox_SystSwithCR.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['post_stratify'])
            AcATaMa.dockwidget.widget_SystSwithCR.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['post_stratify'])
            load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_CategMap_SystS,
                                        get_restore_path(yaml_config["sampling_design"]["systematic_sampling"]['categ_map_path']))
            AcATaMa.dockwidget.select_categorical_map_SystS()
            AcATaMa.dockwidget.QCBox_band_CategMap_SystS.setCurrentIndex(
                yaml_config["sampling_design"]["systematic_sampling"]['categ_map_band'] - 1)
            AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SystS.setText(
                yaml_config["sampling_design"]["systematic_sampling"]['classes_selected_for_sampling'])

            AcATaMa.dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['with_neighbors_aggregation'])
            AcATaMa.dockwidget.widget_generate_SystS.widget_neighbour_aggregation.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['with_neighbors_aggregation'])
            select_item_in(AcATaMa.dockwidget.widget_generate_SystS.QCBox_NumberOfNeighbors,
                           yaml_config["sampling_design"]["systematic_sampling"]['num_neighbors'])
            select_item_in(AcATaMa.dockwidget.widget_generate_SystS.QCBox_SameClassOfNeighbors,
                           yaml_config["sampling_design"]["systematic_sampling"]['min_neighbors_with_the_same_class'])
            AcATaMa.dockwidget.widget_generate_SystS.QGBox_random_sampling_options.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['random_sampling_options'])
            AcATaMa.dockwidget.widget_generate_SystS.widget_random_sampling_options.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['random_sampling_options'])
            AcATaMa.dockwidget.widget_generate_SystS.automatic_random_seed.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['automatic_random_seed'])
            AcATaMa.dockwidget.widget_generate_SystS.with_random_seed_by_user.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['with_random_seed_by_user'])
            AcATaMa.dockwidget.widget_generate_SystS.random_seed_by_user.setText(
                yaml_config["sampling_design"]["systematic_sampling"]['random_seed_by_user'])

    # ######### response_design configuration ######### #
    # restore the response_design settings
    # load the sampling file save in yaml config
    if "sampling_layer" in yaml_config and os.path.isfile(get_restore_path(yaml_config["sampling_layer"])):
        sampling_layer = load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile,
                                                     get_restore_path(yaml_config["sampling_layer"]))
        if not sampling_layer:
            return
        response_design = ResponseDesign(sampling_layer)
        # TODO:
        # restore sampling_layer style

        AcATaMa.dockwidget.grid_columns.setValue(yaml_config["grid_view_widgets"]["columns"])
        AcATaMa.dockwidget.grid_rows.setValue(yaml_config["grid_view_widgets"]["rows"])
        response_design.dialog_size = yaml_config["dialog_size"]
        response_design.grid_columns = yaml_config["grid_view_widgets"]["columns"]
        response_design.grid_rows = yaml_config["grid_view_widgets"]["rows"]
        response_design.current_sample_idx = yaml_config["current_sample_idx"]
        if "sampling_unit_pixel_buffer" in yaml_config:
            response_design.sampling_unit_pixel_buffer = yaml_config["sampling_unit_pixel_buffer"]
        if "sampling_unit_color" in yaml_config:
            response_design.sampling_unit_color = QColor(yaml_config["sampling_unit_color"])
        response_design.fit_to_sample = yaml_config["fit_to_sample"]
        response_design.is_completed = yaml_config["is_completed"]
        # restore the buttons config
        response_design.buttons_config = yaml_config["labeling_buttons"]
        # restore the view widget config
        response_design.view_widgets_config = yaml_config["view_widgets_config"]

        # support load the old format of config file TODO: deprecated, legacy config input
        for x in response_design.view_widgets_config.values():
            if "render_file" in x:
                x["render_file_path"] = x["render_file"]
                del x["render_file"]
            if "name" in x:
                x["view_name"] = x["name"]
                del x["name"]
            if "layer_name" not in x:
                x["layer_name"] = None
        # support load the old format of config file TODO: deprecated, legacy config input
        for sample in yaml_config["samples"].values():
            if "classif_id" in sample:
                sample["label_id"] = sample["classif_id"]
                del sample["classif_id"]
            if "shape_id" in sample:
                sample["sample_id"] = sample["shape_id"]
                del sample["shape_id"]

        # restore the samples order
        samples_ordered = []
        for sample_id in yaml_config["samples_order"]:
            # point saved exist in shape file
            if sample_id in [p.sample_id for p in response_design.points]:
                samples_ordered.append([p for p in response_design.points if p.sample_id == sample_id][0])
        # added new point inside shape file that not exists in yaml config
        for new_point_id in set([p.sample_id for p in response_design.points]) - set(yaml_config["samples_order"]):
            samples_ordered.append([p for p in response_design.points if p.sample_id == new_point_id][0])
        # reassign points loaded and ordered
        response_design.points = samples_ordered
        # restore sample state response_design
        for sample in yaml_config["samples"].values():
            if sample["sample_id"] in [p.sample_id for p in response_design.points]:
                sample_to_restore = [p for p in response_design.points if p.sample_id == sample["sample_id"]][0]
                sample_to_restore.label_id = sample["label_id"]
                if sample_to_restore.label_id is not None:
                    sample_to_restore.is_labeled = True
        # update the status and labels plugin with the current sampling response_design
        response_design.reload_labeling_status()
        AcATaMa.dockwidget.update_response_design_state()
        # define if this response_design was made with thematic classes
        if response_design.buttons_config and yaml_config["thematic_map"]["path"] and \
                True in [bc["thematic_class"] is not None and bc["thematic_class"] != "" for bc in response_design.buttons_config.values()]:
            response_design.with_thematic_classes = True
    else:
        response_design = None

    # ######### accuracy assessment ######### #
    # restore accuracy assessment settings
    # support load the old format of config file TODO: deprecated, legacy config input
    if "accuracy_assessment_sampling_file" in yaml_config and yaml_config["accuracy_assessment_sampling_file"]:
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                    get_restore_path(yaml_config["accuracy_assessment_sampling_file"]))
    if "accuracy_assessment_sampling_type" in yaml_config:
        AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(yaml_config["accuracy_assessment_sampling_type"])

    if "accuracy_assessment_dialog" in yaml_config and response_design:
        from AcATaMa.core.analysis import Analysis
        analysis = Analysis(response_design)
        area_unit, success = QgsUnitTypes.stringToAreaUnit(yaml_config["accuracy_assessment_dialog"]["area_unit"])
        if success:
            analysis.area_unit = area_unit
        analysis.z_score = yaml_config["accuracy_assessment_dialog"]["z_score"]
        analysis.csv_separator = yaml_config["accuracy_assessment_dialog"]["csv_separator"]
        analysis.csv_decimal = yaml_config["accuracy_assessment_dialog"]["csv_decimal"]
        response_design.analysis = analysis
    # support load the old format end here

    if "analysis" in yaml_config and "sampling_file" in yaml_config["analysis"]:
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                    get_restore_path(yaml_config["analysis"]["sampling_file"]))
    if "analysis" in yaml_config and "sampling_type" in yaml_config["analysis"]:
        AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
        AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(yaml_config["analysis"]["sampling_type"])

    if "analysis" in yaml_config and "accuracy_assessment" in yaml_config["analysis"] and response_design:
        from AcATaMa.core.analysis import Analysis
        analysis = Analysis(response_design)
        area_unit, success = QgsUnitTypes.stringToAreaUnit(yaml_config["analysis"]["accuracy_assessment"]["area_unit"])
        if success:
            analysis.area_unit = area_unit
        analysis.z_score = yaml_config["analysis"]["accuracy_assessment"]["z_score"]
        analysis.csv_separator = yaml_config["analysis"]["accuracy_assessment"]["csv_separator"]
        analysis.csv_decimal = yaml_config["analysis"]["accuracy_assessment"]["csv_decimal"]
        response_design.analysis = analysis

    # reload sampling file status in accuracy assessment
    AcATaMa.dockwidget.set_sampling_file_in_analysis()
