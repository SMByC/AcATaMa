# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2024 by Xavier C. Llano, SMByC
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
from collections import OrderedDict
import yaml

from AcATaMa.gui.post_stratification_classes_dialog import PostStratificationClassesDialog

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
from AcATaMa.utils.others_utils import set_nodata_format, get_plugin_version, get_nodata_format

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
        {"config_file_version": get_plugin_version(VERSION)}

    # ######### thematic ######### #
    data["thematic_map"] = \
        {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicMap, show_message=False),
         "band": int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
            if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText() != '' else -1,
         "nodata": AcATaMa.dockwidget.nodata_ThematicMap.text()}

    # ######### sampling design ######### #
    sampling_design = AcATaMa.dockwidget.sampling_design_window
    data["sampling_design"] = {}
    data["sampling_design"]["tab_activated"] = sampling_design.tabs_SamplingStrategy.currentIndex()
    # simple random sampling
    data["sampling_design"]["simple_random_sampling"] = {
        "num_samples": sampling_design.numberOfSamples_SimpRS.value(),
        "min_distance": sampling_design.minDistance_SimpRS.value(),

        "post_stratification": sampling_design.QGBox_SimpRSwithPS.isChecked(),
        "post_stratification_map_path": get_current_file_path_in(sampling_design.QCBox_PostStratMap_SimpRS, show_message=False),
        "post_stratification_map_band": int(sampling_design.QCBox_band_PostStratMap_SimpRS.currentText())
            if sampling_design.QCBox_band_PostStratMap_SimpRS.currentText() != '' else -1,
        "post_stratification_map_nodata": sampling_design.nodata_PostStratMap_SimpRS.text(),
        "classes_selected_for_sampling": sampling_design.QPBtn_PostStratMapClasses_SimpRS.text()
            if sampling_design.QPBtn_PostStratMapClasses_SimpRS.text() != 'click to select' else None,

        "with_neighbors_aggregation": sampling_design.QGBox_neighbour_aggregation_SimpRS.isChecked(),
        "num_neighbors": sampling_design.QCBox_NumberOfNeighbors_SimpRS.currentText(),
        "min_neighbors_with_the_same_class": sampling_design.QCBox_SameClassOfNeighbors_SimpRS.currentText(),
        "random_sampling_options": sampling_design.QGBox_random_sampling_options_SimpRS.isChecked(),
        "automatic_random_seed": sampling_design.automatic_random_seed_SimpRS.isChecked(),
        "with_random_seed_by_user": sampling_design.with_random_seed_by_user_SimpRS.isChecked(),
        "random_seed_by_user": sampling_design.random_seed_by_user_SimpRS.text(),
    }
    # stratified random sampling
    srs_method = "fixed values" if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values") \
        else "area based proportion"
    with_srs_table = sampling_design.QCBox_StratMap_StraRS.currentText() in sampling_design.srs_tables and \
        srs_method in sampling_design.srs_tables[sampling_design.QCBox_StratMap_StraRS.currentText()]
    data["sampling_design"]["stratified_random_sampling"] = {
        "stratification_map_path": get_current_file_path_in(sampling_design.QCBox_StratMap_StraRS, show_message=False),
        "stratification_map_band": int(sampling_design.QCBox_band_StratMap_StraRS.currentText())
            if sampling_design.QCBox_band_StratMap_StraRS.currentText() != '' else -1,
        "stratification_map_nodata": sampling_design.nodata_StratMap_StraRS.text(),

        "sampling_random_method": sampling_design.QCBox_StraRS_Method.currentText(),
        "overall_std_error": sampling_design.TotalExpectedSE.value(),
        "minimum_samples_per_stratum": sampling_design.MinimumSamplesPerStratum.value(),
        "stratified_random_sampling_table": sampling_design.srs_tables
            [sampling_design.QCBox_StratMap_StraRS.currentText()][srs_method] if with_srs_table else None,

        # TODO:
        # save the values color table of the QCBox_StratMap_StraRS

        "min_distance": sampling_design.minDistance_StraRS.value(),
        "with_neighbors_aggregation": sampling_design.QGBox_neighbour_aggregation_StraRS.isChecked(),
        "num_neighbors": sampling_design.QCBox_NumberOfNeighbors_StraRS.currentText(),
        "min_neighbors_with_the_same_class": sampling_design.QCBox_SameClassOfNeighbors_StraRS.currentText(),
        "random_sampling_options": sampling_design.QGBox_random_sampling_options_StraRS.isChecked(),
        "automatic_random_seed": sampling_design.automatic_random_seed_StraRS.isChecked(),
        "with_random_seed_by_user": sampling_design.with_random_seed_by_user_StraRS.isChecked(),
        "random_seed_by_user": sampling_design.random_seed_by_user_StraRS.text(),
    }
    # systematic sampling
    data["sampling_design"]["systematic_sampling"] = {
        "points_spacing": sampling_design.PointsSpacing_SystS.value(),
        "initial_inset_mode": sampling_design.QCBox_InitialInsetMode_SystS.currentText(),
        "initial_inset": sampling_design.InitialInsetFixed_SystS.value(),
        "max_xy_offset": sampling_design.MaxXYoffset_SystS.value(),

        "post_stratification": sampling_design.QGBox_SystSwithPS.isChecked(),
        "post_stratification_map_path": get_current_file_path_in(sampling_design.QCBox_PostStratMap_SystS, show_message=False),
        "post_stratification_map_band": int(sampling_design.QCBox_band_PostStratMap_SystS.currentText())
            if sampling_design.QCBox_band_PostStratMap_SystS.currentText() != '' else -1,
        "post_stratification_map_nodata": sampling_design.nodata_PostStratMap_SystS.text(),
        "classes_selected_for_sampling": sampling_design.QPBtn_PostStratMapClasses_SystS.text()
            if sampling_design.QPBtn_PostStratMapClasses_SystS.text() != 'click to select' else None,
        "with_neighbors_aggregation": sampling_design.QGBox_neighbour_aggregation_SystS.isChecked(),
        "num_neighbors": sampling_design.QCBox_NumberOfNeighbors_SystS.currentText(),
        "min_neighbors_with_the_same_class": sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText(),
        "random_sampling_options": sampling_design.QGBox_random_sampling_options_SystS.isChecked(),
        "automatic_random_seed": sampling_design.automatic_random_seed_SystS.isChecked(),
        "with_random_seed_by_user": sampling_design.with_random_seed_by_user_SystS.isChecked(),
        "random_seed_by_user": sampling_design.random_seed_by_user_SystS.text(),
    }

    # ######### sampling report configuration ######### #
    from AcATaMa.gui.sampling_report import SamplingReport
    sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
    if sampling_layer and sampling_layer in SamplingReport.instances:
        sampling_report = SamplingReport.instances[sampling_layer]
        data["sampling_report"] = sampling_report.report

    # ######### response design configuration ######### #
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
        data["auto_next_sample"] = response_design.auto_next_sample
        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(response_design.points):
            if point.is_labeled:
                points_config[pnt_idx] = {"label_id": point.label_id, "sample_id": point.sample_id}
        data["samples"] = points_config
        # save the samples order
        data["samples_order"] = [p.sample_id for p in response_design.points]

        # save the ccd plugin config
        if response_design.ccd_plugin_config is not None:
            data["ccd_plugin_config"] = response_design.ccd_plugin_config
            data["ccd_plugin_opened"] = response_design.ccd_plugin_opened
    else:
        response_design = None

    # ######### accuracy assessment ######### #
    data["analysis"] = {}
    data["analysis"]["estimator"] = AcATaMa.dockwidget.QCBox_SamplingEstimator.currentText()
    # save config of the accuracy assessment dialog if exists
    if response_design and response_design.analysis:
        data["analysis"]["accuracy_assessment"] = {
            "area_unit": response_design.analysis.area_unit.value,
            "z_score": response_design.analysis.z_score,
            "csv_separator": response_design.analysis.csv_separator,
            "csv_decimal": response_design.analysis.csv_decimal,
        }

    with open(file_out, 'w') as yaml_file:
        yaml.dump(data, yaml_file, Dumper=Dumper)


@wait_process
def restore(yml_file_path):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    from AcATaMa.gui.sampling_design_window import SamplingDesignWindow
    from AcATaMa.gui.response_design_window import ResponseDesignWindow
    from AcATaMa.core.analysis import AccuracyAssessmentWindow
    from AcATaMa.gui.sampling_report import SamplingReport

    # load the yaml file
    with open(yml_file_path, 'r') as yaml_file:
        try:
            yaml_config = yaml.load(yaml_file, Loader=Loader)
        except yaml.YAMLError as err:
            iface.messageBar().pushMessage("AcATaMa", "Error while read the AcATaMa configuration file: {}".format(err),
                                           level=Qgis.Critical, duration=20)
            return

    # close the windows opened
    if SamplingDesignWindow.is_opened:
        AcATaMa.dockwidget.sampling_design_window.closing()
        AcATaMa.dockwidget.sampling_design_window.reject(is_ok_to_close=True)
    if ResponseDesignWindow.is_opened:
        AcATaMa.dockwidget.response_design_window.closing()
        AcATaMa.dockwidget.response_design_window.reject(is_ok_to_close=True)
    if AccuracyAssessmentWindow.is_opened:
        AcATaMa.dockwidget.accuracy_assessment_window.closing()
        AcATaMa.dockwidget.accuracy_assessment_window.reject(is_ok_to_close=True)
    if SamplingReport.instance_opened:
        SamplingReport.instance_opened.close()

    # clear some stuff
    PostStratificationClassesDialog.instances = {}
    ResponseDesign.instances = {}
    ResponseDesignWindow.inst = None
    AcATaMa.dockwidget.sampling_design_window = SamplingDesignWindow()

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
        # remove dots and alpha characters from the version string
        CONFIG_FILE_VERSION = get_plugin_version(yaml_config["general"]["config_file_version"])
    else:
        CONFIG_FILE_VERSION = 191121  # v19.11.21

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
    if "sampling_design" in yaml_config and "pixel_values_categ_map" in yaml_config["sampling_design"]["simple_random_sampling"]:
        yaml_config["sampling_design"]["simple_random_sampling"]['classes_selected_for_sampling'] = \
            yaml_config["sampling_design"]["simple_random_sampling"].pop("pixel_values_categ_map")
    # old post stratification section
    if "post_stratify" in yaml_config["sampling_design"]["simple_random_sampling"]:
        yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification'] = \
            yaml_config["sampling_design"]["simple_random_sampling"].pop("post_stratify")
    if "post_stratify" in yaml_config["sampling_design"]["systematic_sampling"]:
        yaml_config["sampling_design"]["systematic_sampling"]['post_stratification'] = \
            yaml_config["sampling_design"]["systematic_sampling"].pop("post_stratify")
    # old post stratification map path
    if "categ_map_path" in yaml_config["sampling_design"]["simple_random_sampling"]:
        yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification_map_path'] = \
            yaml_config["sampling_design"]["simple_random_sampling"].pop("categ_map_path")
    if "categ_map_path" in yaml_config["sampling_design"]["systematic_sampling"]:
        yaml_config["sampling_design"]["systematic_sampling"]['post_stratification_map_path'] = \
            yaml_config["sampling_design"]["systematic_sampling"].pop("categ_map_path")
    if "categ_map_path" in yaml_config["sampling_design"]["stratified_random_sampling"]:
        yaml_config["sampling_design"]["stratified_random_sampling"]['stratification_map_path'] = \
            yaml_config["sampling_design"]["stratified_random_sampling"].pop("categ_map_path")
    # old post stratification map band
    if "categ_map_band" in yaml_config["sampling_design"]["simple_random_sampling"]:
        yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification_map_band'] = \
            yaml_config["sampling_design"]["simple_random_sampling"].pop("categ_map_band")
    if "categ_map_band" in yaml_config["sampling_design"]["systematic_sampling"]:
        yaml_config["sampling_design"]["systematic_sampling"]['post_stratification_map_band'] = \
            yaml_config["sampling_design"]["systematic_sampling"].pop("categ_map_band")
    if "categ_map_band" in yaml_config["sampling_design"]["stratified_random_sampling"]:
        yaml_config["sampling_design"]["stratified_random_sampling"]['stratification_map_band'] = \
            yaml_config["sampling_design"]["stratified_random_sampling"].pop("categ_map_band")
    # old post stratification map nodata
    if "categ_map_nodata" in yaml_config["sampling_design"]["stratified_random_sampling"]:
        yaml_config["sampling_design"]["stratified_random_sampling"]['stratification_map_nodata'] = \
            yaml_config["sampling_design"]["stratified_random_sampling"].pop("categ_map_nodata")

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
        if CONFIG_FILE_VERSION == 191121 and nodata == "-1":
            AcATaMa.dockwidget.nodata_ThematicMap.setText("nan")
        else:
            AcATaMa.dockwidget.nodata_ThematicMap.setText(nodata)

    # ######### sampling design configuration ######### #
    if "sampling_design" in yaml_config:
        sampling_design = AcATaMa.dockwidget.sampling_design_window
        sampling_design.tabs_SamplingStrategy.setCurrentIndex(yaml_config["sampling_design"]["tab_activated"])

        # simple random sampling
        sampling_design.numberOfSamples_SimpRS.setValue(
            yaml_config["sampling_design"]["simple_random_sampling"]['num_samples'])
        sampling_design.minDistance_SimpRS.setValue(
            yaml_config["sampling_design"]["simple_random_sampling"]['min_distance'])
        sampling_design.QGBox_SimpRSwithPS.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification'])
        sampling_design.widget_SimpRSwithPS.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification'])
        load_and_select_filepath_in(sampling_design.QCBox_PostStratMap_SimpRS,
                                    get_restore_path(yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification_map_path']))
        sampling_design.update_post_stratification_map_SimpRS(item_changed="layer")
        sampling_design.QCBox_band_PostStratMap_SimpRS.setCurrentIndex(
            yaml_config["sampling_design"]["simple_random_sampling"]['post_stratification_map_band'] - 1)
        sampling_design.update_post_stratification_map_SimpRS(item_changed="band")
        if "post_stratification_map_nodata" in yaml_config["sampling_design"]["simple_random_sampling"]:
            nodata = set_nodata_format(yaml_config["sampling_design"]["simple_random_sampling"]["post_stratification_map_nodata"])
            sampling_design.nodata_PostStratMap_SimpRS.setText(nodata)
        sampling_design.update_post_stratification_map_SimpRS(item_changed="nodata")
        sampling_design.QPBtn_PostStratMapClasses_SimpRS.setText(
            yaml_config["sampling_design"]["simple_random_sampling"]['classes_selected_for_sampling']
            if yaml_config["sampling_design"]["simple_random_sampling"]['classes_selected_for_sampling'] else "click to select")

        sampling_design.QGBox_neighbour_aggregation_SimpRS.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_neighbors_aggregation'])
        sampling_design.widget_neighbour_aggregation_SimpRS.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_neighbors_aggregation'])
        select_item_in(sampling_design.QCBox_NumberOfNeighbors_SimpRS,
                       yaml_config["sampling_design"]["simple_random_sampling"]['num_neighbors'])
        select_item_in(sampling_design.QCBox_SameClassOfNeighbors_SimpRS,
                       yaml_config["sampling_design"]["simple_random_sampling"]['min_neighbors_with_the_same_class'])
        sampling_design.QGBox_random_sampling_options_SimpRS.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_sampling_options'])
        sampling_design.widget_random_sampling_options_SimpRS.setVisible(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_sampling_options'])
        sampling_design.automatic_random_seed_SimpRS.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['automatic_random_seed'])
        sampling_design.with_random_seed_by_user_SimpRS.setChecked(
            yaml_config["sampling_design"]["simple_random_sampling"]['with_random_seed_by_user'])
        sampling_design.random_seed_by_user_SimpRS.setText(
            yaml_config["sampling_design"]["simple_random_sampling"]['random_seed_by_user'])

        # stratified random sampling
        load_and_select_filepath_in(sampling_design.QCBox_StratMap_StraRS,
                                    get_restore_path(yaml_config["sampling_design"]["stratified_random_sampling"]['stratification_map_path']))
        sampling_design.update_stratification_map_StraRS(sampling_design.QCBox_StratMap_StraRS.currentLayer())
        sampling_design.QCBox_band_StratMap_StraRS.setCurrentIndex(
            yaml_config["sampling_design"]["stratified_random_sampling"]['stratification_map_band'] - 1)
        # nodata
        nodata = set_nodata_format(yaml_config["sampling_design"]["stratified_random_sampling"]["stratification_map_nodata"])
        if CONFIG_FILE_VERSION == 191121 and nodata == "-1":
            sampling_design.nodata_StratMap_StraRS.setText("nan")
        else:
            sampling_design.nodata_StratMap_StraRS.setText(nodata)

        with block_signals_to(sampling_design.QCBox_StraRS_Method):
            select_item_in(sampling_design.QCBox_StraRS_Method,
                           yaml_config["sampling_design"]["stratified_random_sampling"]['sampling_random_method'])
        with block_signals_to(sampling_design.TotalExpectedSE):
            sampling_design.TotalExpectedSE.setValue(
                yaml_config["sampling_design"]["stratified_random_sampling"]['overall_std_error'])
        if "minimum_samples_per_stratum" in yaml_config["sampling_design"]["stratified_random_sampling"]:
            with block_signals_to(sampling_design.MinimumSamplesPerStratum):
                sampling_design.MinimumSamplesPerStratum.setValue(
                    yaml_config["sampling_design"]["stratified_random_sampling"]['minimum_samples_per_stratum'])

        srs_table = yaml_config["sampling_design"]["stratified_random_sampling"]['stratified_random_sampling_table']

        # import Ui from old versions
        if CONFIG_FILE_VERSION < 240600:
            if srs_table and 'std_dev' in srs_table:
                srs_table['ui'] = srs_table.pop('std_dev')
            # change the header 'Std Dev' to 'Ui' in the header list inside srs_table
            if srs_table and 'Std Dev' in srs_table['header']:
                # replace the header python list 'Std Dev' to 'Ui'
                srs_table['header'][srs_table['header'].index('Std Dev')] = 'Ui'

        srs_method = "fixed values" if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values") \
            else "area based proportion"
        sampling_design.srs_tables[sampling_design.QCBox_StratMap_StraRS.currentText()] = {}
        sampling_design.srs_tables[sampling_design.QCBox_StratMap_StraRS.currentText()][srs_method] = srs_table
        fill_stratified_sampling_table(sampling_design)
        # restore the pixel count by pixel value
        if srs_table and 'pixel_count' in srs_table:
            from AcATaMa.utils.others_utils import storage_pixel_count_by_pixel_values
            global storage_pixel_count_by_pixel_values
            storage_pixel_count_by_pixel_values[
                (sampling_design.QCBox_StratMap_StraRS.currentLayer(),
                 int(sampling_design.QCBox_band_StratMap_StraRS.currentText()),
                 get_nodata_format(sampling_design.nodata_StratMap_StraRS.text()))
            ] = dict(zip(srs_table['values_and_colors_table']['Pixel Value'], srs_table['pixel_count']))

        # TODO:
        # restore the values color table of the QCBox_StratMap_StraRS saved

        sampling_design.minDistance_StraRS.setValue(
            yaml_config["sampling_design"]["stratified_random_sampling"]['min_distance'])
        sampling_design.QGBox_neighbour_aggregation_StraRS.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_neighbors_aggregation'])
        sampling_design.widget_neighbour_aggregation_StraRS.setVisible(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_neighbors_aggregation'])
        select_item_in(sampling_design.QCBox_NumberOfNeighbors_StraRS,
                       yaml_config["sampling_design"]["stratified_random_sampling"]['num_neighbors'])
        select_item_in(sampling_design.QCBox_SameClassOfNeighbors_StraRS,
                       yaml_config["sampling_design"]["stratified_random_sampling"]['min_neighbors_with_the_same_class'])
        sampling_design.QGBox_random_sampling_options_StraRS.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_sampling_options'])
        sampling_design.widget_random_sampling_options_StraRS.setVisible(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_sampling_options'])
        sampling_design.automatic_random_seed_StraRS.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['automatic_random_seed'])
        sampling_design.with_random_seed_by_user_StraRS.setChecked(
            yaml_config["sampling_design"]["stratified_random_sampling"]['with_random_seed_by_user'])
        sampling_design.random_seed_by_user_StraRS.setText(
            yaml_config["sampling_design"]["stratified_random_sampling"]['random_seed_by_user'])

        # systematic sampling
        if "systematic_sampling" in yaml_config["sampling_design"]:
            sampling_design.PointsSpacing_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['points_spacing'])
            if "initial_inset_mode" in yaml_config["sampling_design"]["systematic_sampling"]:
                select_item_in(sampling_design.QCBox_InitialInsetMode_SystS,
                               yaml_config["sampling_design"]["systematic_sampling"]['initial_inset_mode'])
            else:
                select_item_in(sampling_design.QCBox_InitialInsetMode_SystS, "Fixed")
            sampling_design.InitialInsetFixed_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['initial_inset'])
            sampling_design.MaxXYoffset_SystS.setValue(
                yaml_config["sampling_design"]["systematic_sampling"]['max_xy_offset'])

            sampling_design.QGBox_SystSwithPS.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['post_stratification'])
            sampling_design.widget_SystSwithPS.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['post_stratification'])
            load_and_select_filepath_in(sampling_design.QCBox_PostStratMap_SystS,
                                        get_restore_path(yaml_config["sampling_design"]["systematic_sampling"]['post_stratification_map_path']))
            sampling_design.update_post_stratification_map_SystS(item_changed="layer")
            sampling_design.QCBox_band_PostStratMap_SystS.setCurrentIndex(
                yaml_config["sampling_design"]["systematic_sampling"]['post_stratification_map_band'] - 1)
            sampling_design.update_post_stratification_map_SystS(item_changed="band")
            if "post_stratification_map_nodata" in yaml_config["sampling_design"]["systematic_sampling"]:
                nodata = set_nodata_format(yaml_config["sampling_design"]["systematic_sampling"]["post_stratification_map_nodata"])
                sampling_design.nodata_PostStratMap_SystS.setText(nodata)
            sampling_design.update_post_stratification_map_SystS(item_changed="nodata")
            sampling_design.QPBtn_PostStratMapClasses_SystS.setText(
                yaml_config["sampling_design"]["systematic_sampling"]['classes_selected_for_sampling']
                if yaml_config["sampling_design"]["systematic_sampling"]['classes_selected_for_sampling'] else "click to select")

            sampling_design.QGBox_neighbour_aggregation_SystS.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['with_neighbors_aggregation'])
            sampling_design.widget_neighbour_aggregation_SystS.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['with_neighbors_aggregation'])
            select_item_in(sampling_design.QCBox_NumberOfNeighbors_SystS,
                           yaml_config["sampling_design"]["systematic_sampling"]['num_neighbors'])
            select_item_in(sampling_design.QCBox_SameClassOfNeighbors_SystS,
                           yaml_config["sampling_design"]["systematic_sampling"]['min_neighbors_with_the_same_class'])
            sampling_design.QGBox_random_sampling_options_SystS.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['random_sampling_options'])
            sampling_design.widget_random_sampling_options_SystS.setVisible(
                yaml_config["sampling_design"]["systematic_sampling"]['random_sampling_options'])
            sampling_design.automatic_random_seed_SystS.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['automatic_random_seed'])
            sampling_design.with_random_seed_by_user_SystS.setChecked(
                yaml_config["sampling_design"]["systematic_sampling"]['with_random_seed_by_user'])
            sampling_design.random_seed_by_user_SystS.setText(
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
        # restore the auto next sample option
        if "auto_next_sample" in yaml_config:
            response_design.auto_next_sample = yaml_config["auto_next_sample"]

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

        # support relative paths in the view widgets
        for x in response_design.view_widgets_config.values():
            x["render_file_path"] = get_restore_path(x["render_file_path"])

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

        # restore the ccd plugin config
        if "ccd_plugin_config" in yaml_config:
            response_design.ccd_plugin_config = yaml_config["ccd_plugin_config"]
            response_design.ccd_plugin_opened = yaml_config["ccd_plugin_opened"]
    else:
        response_design = None

    # ######### sampling report configuration ######### #
    from AcATaMa.gui.sampling_report import SamplingReport
    if "sampling_report" in yaml_config:
        if "sampling_layer" in yaml_config and sampling_layer:
            SamplingReport(sampling_layer, report=yaml_config["sampling_report"])
            AcATaMa.dockwidget.QPBtn_openSamplingReport.setEnabled(True)

    # ######### accuracy assessment ######### #
    # restore accuracy assessment settings
    # support load the old format of config file TODO: deprecated, legacy config input
    if "accuracy_assessment_estimator" in yaml_config:
        AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(yaml_config["accuracy_assessment_estimator"])

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
    if "analysis" in yaml_config and "estimator" in yaml_config["analysis"]:
        AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(-1)
        estimators = {'Simple/systematic estimator': 0, 'Simple/systematic post-stratified estimator': 1, 'Stratified estimator': 2}
        if yaml_config["analysis"]["estimator"] in estimators:
            AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(estimators[yaml_config["analysis"]["estimator"]])

    if "analysis" in yaml_config and "accuracy_assessment" in yaml_config["analysis"] and response_design:
        from AcATaMa.core.analysis import Analysis
        analysis = Analysis(response_design)
        if yaml_config["analysis"]["accuracy_assessment"]["area_unit"] in [e.value for e in QgsUnitTypes.AreaUnit]:
            analysis.area_unit = QgsUnitTypes.AreaUnit(yaml_config["analysis"]["accuracy_assessment"]["area_unit"])
        else:  # old format
            area_unit, success = QgsUnitTypes.stringToAreaUnit(yaml_config["analysis"]["accuracy_assessment"]["area_unit"])
            analysis.area_unit = area_unit if success else QgsUnitTypes.AreaSquareMeters
        analysis.z_score = yaml_config["analysis"]["accuracy_assessment"]["z_score"]
        analysis.csv_separator = yaml_config["analysis"]["accuracy_assessment"]["csv_separator"]
        analysis.csv_decimal = yaml_config["analysis"]["accuracy_assessment"]["csv_decimal"]
        response_design.analysis = analysis

    # reload analysis status in accuracy assessment
    AcATaMa.dockwidget.update_analysis_state()
