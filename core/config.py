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
    # TODO migration
    data["thematic_raster"] = \
        {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicMap, show_message=False),
         "band": int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
         if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText() else None,
         "nodata": AcATaMa.dockwidget.nodata_ThematicMap.value()}

    # ######### general configuration ######### #
    data["general"] = {"tab_activated": AcATaMa.dockwidget.tabWidget.currentIndex()}

    # ######### response design configuration ######### #
    sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
    if sampling_layer in ResponseDesign.instances:
        # data["classification"] = {}  # TODO
        response_design = ResponseDesign.instances[sampling_layer]
        data["sampling_layer"] = get_file_path_of_layer(response_design.sampling_layer)
        data["dialog_size"] = response_design.dialog_size
        data["grid_view_widgets"] = {"columns": response_design.grid_columns, "rows": response_design.grid_rows}
        data["current_sample_idx"] = response_design.current_sample_idx
        data["fit_to_sample"] = response_design.fit_to_sample
        data["is_completed"] = response_design.is_completed
        data["view_widgets_config"] = response_design.view_widgets_config
        data["classification_buttons"] = response_design.buttons_config  # TODO migration
        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(response_design.points):
            if point.is_labeled:
                points_config[pnt_idx] = {"classif_id": point.label_id, "shape_id": point.shape_id}
        data["points"] = points_config
        # save the samples order
        data["points_order"] = [p.shape_id for p in response_design.points]
    else:
        response_design = None

    # ######### accuracy assessment ######### #
    data["accuracy_assessment"] = {}
    data["accuracy_assessment"]["sampling_file"] = get_current_file_path_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                                                            show_message=False)
    data["accuracy_assessment"]["sampling_type"] = AcATaMa.dockwidget.QCBox_SamplingType_A.currentIndex()
    # save config of the accuracy assessment dialog if exists
    if response_design and response_design.accuracy_assessment:
        data["accuracy_assessment"]["dialog"] = {
            "area_unit": QgsUnitTypes.toString(response_design.accuracy_assessment.area_unit),
            "z_score": response_design.accuracy_assessment.z_score,
            "csv_separator": response_design.accuracy_assessment.csv_separator,
            "csv_decimal": response_design.accuracy_assessment.csv_decimal,
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

    # restore the thematic map
    if yaml_config["thematic_raster"]["path"]:
        # thematic map
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_ThematicMap,
                                    yaml_config["thematic_raster"]["path"])
        AcATaMa.dockwidget.select_thematic_map(AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer())
        # band number
        if "band" in yaml_config["thematic_raster"]:
            AcATaMa.dockwidget.QCBox_band_ThematicMap.setCurrentIndex(yaml_config["thematic_raster"]["band"] - 1)
        # nodata
        AcATaMa.dockwidget.nodata_ThematicMap.setValue(yaml_config["thematic_raster"]["nodata"])

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
        response_design.buttons_config = yaml_config["classification_buttons"]  # TODO migration
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

        # restore the samples order
        points_ordered = []
        for shape_id in yaml_config["points_order"]:
            # point saved exist in shape file
            if shape_id in [p.shape_id for p in response_design.points]:
                points_ordered.append([p for p in response_design.points if p.shape_id == shape_id][0])
        # added new point inside shape file that not exists in yaml config
        for new_point_id in set([p.shape_id for p in response_design.points]) - set(yaml_config["points_order"]):
            points_ordered.append([p for p in response_design.points if p.shape_id == new_point_id][0])
        # reassign points loaded and ordered
        response_design.points = points_ordered
        # restore point status response_design
        for status in yaml_config["points"].values():
            if status["shape_id"] in [p.shape_id for p in response_design.points]:
                point_to_restore = [p for p in response_design.points if p.shape_id == status["shape_id"]][0]
                point_to_restore.label_id = status["classif_id"]
                if point_to_restore.label_id is not None:
                    point_to_restore.is_labeled = True
        # update the status and labels plugin with the current sampling response_design
        response_design.reload_labeling_status()
        AcATaMa.dockwidget.update_response_design_state()
        # define if this response_design was made with thematic classes
        if response_design.buttons_config and yaml_config["thematic_raster"]["path"] and \
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
        accuracy_assessment = Analysis(response_design)
        area_unit, success = QgsUnitTypes.stringToAreaUnit(yaml_config["accuracy_assessment_dialog"]["area_unit"])
        if success:
            accuracy_assessment.area_unit = area_unit
        accuracy_assessment.z_score = yaml_config["accuracy_assessment_dialog"]["z_score"]
        accuracy_assessment.csv_separator = yaml_config["accuracy_assessment_dialog"]["csv_separator"]
        accuracy_assessment.csv_decimal = yaml_config["accuracy_assessment_dialog"]["csv_decimal"]
        response_design.accuracy_assessment = accuracy_assessment
    # support load the old format end here

    if "accuracy_assessment" in yaml_config and "sampling_file" in yaml_config["accuracy_assessment"]:
        load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_SamplingFile_A,
                                    yaml_config["accuracy_assessment"]["sampling_file"])
    if "accuracy_assessment" in yaml_config and "sampling_type" in yaml_config["accuracy_assessment"]:
        AcATaMa.dockwidget.QCBox_SamplingType_A.setCurrentIndex(yaml_config["accuracy_assessment"]["sampling_type"])

    if "accuracy_assessment" in yaml_config and "dialog" in yaml_config["accuracy_assessment"] and response_design:
        from AcATaMa.core.analysis import Analysis
        accuracy_assessment = Analysis(response_design)
        area_unit, success = QgsUnitTypes.stringToAreaUnit(yaml_config["accuracy_assessment"]["dialog"]["area_unit"])
        if success:
            accuracy_assessment.area_unit = area_unit
        accuracy_assessment.z_score = yaml_config["accuracy_assessment"]["dialog"]["z_score"]
        accuracy_assessment.csv_separator = yaml_config["accuracy_assessment"]["dialog"]["csv_separator"]
        accuracy_assessment.csv_decimal = yaml_config["accuracy_assessment"]["dialog"]["csv_decimal"]
        response_design.accuracy_assessment = accuracy_assessment

    # reload sampling file status in accuracy assessment
    AcATaMa.dockwidget.set_sampling_file_in_analysis()
