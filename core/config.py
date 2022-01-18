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
import os
from collections import OrderedDict

from qgis.core import Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.system_utils import wait_process
from AcATaMa.utils.qgis_utils import get_current_file_path_in, get_file_path_of_layer, load_and_select_filepath_in


@wait_process
def save(file_out):
    import yaml
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    def setup_yaml():
        """
        Keep dump ordered with orderedDict
        """
        represent_dict_order = lambda self, data: self.represent_mapping('tag:yaml.org,2002:map',
                                                                         list(data.items()))
        yaml.add_representer(OrderedDict, represent_dict_order)

    setup_yaml()

    data = OrderedDict()
    data["thematic_map"] = \
        {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicMap, show_message=False),
         "band": int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
         if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText() else None,
         "nodata": AcATaMa.dockwidget.nodata_ThematicMap.value()}

    # ######### general configuration ######### #
    data["general"] = {"tab_activated": AcATaMa.dockwidget.tabWidget.currentIndex()}

    # ######### response design configuration ######### #
    sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
    if sampling_layer in ResponseDesign.instances:
        response_design = ResponseDesign.instances[sampling_layer]
        data["sampling_layer"] = get_file_path_of_layer(response_design.sampling_layer)
        data["dialog_size"] = response_design.dialog_size
        data["grid_view_widgets"] = {"columns": response_design.grid_columns, "rows": response_design.grid_rows}
        data["current_sample_idx"] = response_design.current_sample_idx
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
    data["analysis"]["sampling_type"] = AcATaMa.dockwidget.QCBox_SamplingType_A.currentIndex()
    # save config of the accuracy assessment dialog if exists
    if response_design and response_design.analysis:
        data["analysis"]["accuracy_assessment"] = {
            "area_unit": QgsUnitTypes.toString(response_design.analysis.area_unit),
            "z_score": response_design.analysis.z_score,
            "csv_separator": response_design.analysis.csv_separator,
            "csv_decimal": response_design.analysis.csv_decimal,
        }

    with open(file_out, 'w') as yaml_file:
        yaml.dump(data, yaml_file)


@wait_process
def restore(file_path):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # load the yaml file
    import yaml
    with open(file_path, 'r') as yaml_file:
        try:
            yaml_config = yaml.load(yaml_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            iface.messageBar().pushMessage("AcATaMa", "Error while read the AcATaMa configuration file: {}".format(err),
                                           level=Qgis.Critical)
            return

    # ######### general configuration ######### #
    if "general" in yaml_config:
        AcATaMa.dockwidget.tabWidget.setCurrentIndex(yaml_config["general"]["tab_activated"])

    # support load the old format of config file TODO: delete
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
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_ThematicMap,
                                    yaml_config["thematic_map"]["path"])
        AcATaMa.dockwidget.select_thematic_map(AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer())
        # band number
        if "band" in yaml_config["thematic_map"]:
            AcATaMa.dockwidget.QCBox_band_ThematicMap.setCurrentIndex(yaml_config["thematic_map"]["band"] - 1)
        # nodata
        AcATaMa.dockwidget.nodata_ThematicMap.setValue(yaml_config["thematic_map"]["nodata"])

    # ######### response_design configuration ######### #
    # restore the response_design settings
    # load the sampling file save in yaml config
    sampling_filepath = yaml_config["sampling_layer"]
    if os.path.isfile(sampling_filepath):
        sampling_layer = load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile, sampling_filepath)
        response_design = ResponseDesign(sampling_layer)

        AcATaMa.dockwidget.grid_columns.setValue(yaml_config["grid_view_widgets"]["columns"])
        AcATaMa.dockwidget.grid_rows.setValue(yaml_config["grid_view_widgets"]["rows"])
        response_design.dialog_size = yaml_config["dialog_size"]
        response_design.grid_columns = yaml_config["grid_view_widgets"]["columns"]
        response_design.grid_rows = yaml_config["grid_view_widgets"]["rows"]
        response_design.current_sample_idx = yaml_config["current_sample_idx"]
        response_design.fit_to_sample = yaml_config["fit_to_sample"]
        response_design.is_completed = yaml_config["is_completed"]
        # restore the buttons config
        response_design.buttons_config = yaml_config["labeling_buttons"]
        # restore the view widget config
        response_design.view_widgets_config = yaml_config["view_widgets_config"]

        # support load the old format of config file TODO: delete
        for x in response_design.view_widgets_config.values():
            if "render_file" in x:
                x["render_file_path"] = x["render_file"]
                del x["render_file"]
            if "name" in x:
                x["view_name"] = x["name"]
                del x["name"]
            if "layer_name" not in x:
                x["layer_name"] = None
        # support load the old format of config file TODO: delete
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
    # support load the old format of config file TODO: delete
    if "accuracy_assessment_sampling_file" in yaml_config and yaml_config["accuracy_assessment_sampling_file"]:
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                    yaml_config["accuracy_assessment_sampling_file"])
    if "accuracy_assessment_sampling_type" in yaml_config:
        AcATaMa.dockwidget.QCBox_SamplingType_A.setCurrentIndex(yaml_config["accuracy_assessment_sampling_type"])

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
                                    yaml_config["analysis"]["sampling_file"])
    if "analysis" in yaml_config and "sampling_type" in yaml_config["analysis"]:
        AcATaMa.dockwidget.QCBox_SamplingType_A.setCurrentIndex(-1)
        AcATaMa.dockwidget.QCBox_SamplingType_A.setCurrentIndex(yaml_config["analysis"]["sampling_type"])

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
