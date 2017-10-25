# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017 by Xavier Corredor Llano, SMBYC
        email                : xcorredorl@ideam.gov.co
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
from collections import OrderedDict
from random import shuffle

from AcATaMa.core.dockwidget import get_current_file_path_in, get_file_path_of_layer, load_and_select_filepath_in
from AcATaMa.core.point import ClassificationPoint


class Classification:
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the classification buttons properties
        # {btn_id: {"name", "color", "thematic_class"}}
        self.buttons_config = None
        # get all points from the layer
        # [ClassificationPoint, ClassificationPoint, ...]
        self.points = self.get_points_from_shapefile()
        # save and init the current sample index
        self.current_sample_idx = 0
        # grid config
        self.grid_columns = 3
        self.grid_rows = 2
        # radius to sample
        self.fit_to_sample = 120
        # save views widget config
        # {N: {"name", "render_file", "scale_factor"}, ...}
        self.view_widgets_config = {}
        # when all points are classified
        self.is_completed = False

        # shuffle the list items
        shuffle(self.points)
        # save instance
        Classification.instances[sampling_layer] = self

    def get_points_from_shapefile(self):
        points = []
        for feature_id, qgs_feature in enumerate(self.sampling_layer.getFeatures()):
            geom = qgs_feature.geometry()
            x, y = geom.asPoint()
            points.append(ClassificationPoint(x, y, feature_id+1))
        return points

    def save_config(self, file_out):
        import yaml
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        def setup_yaml():
            """
            Keep dump ordered with orderedDict
            """
            represent_dict_order = lambda self, data: self.represent_mapping('tag:yaml.org,2002:map', data.items())
            yaml.add_representer(OrderedDict, represent_dict_order)
        setup_yaml()

        data = OrderedDict()
        data["thematic_raster"] = \
            {"path": get_current_file_path_in(AcATaMa.dockwidget.selectThematicRaster, show_message=False),
             "nodata": AcATaMa.dockwidget.nodata_ThematicRaster.value()}
        data["sampling_layer"] = get_file_path_of_layer(self.sampling_layer)
        data["fit_to_sample"] = self.fit_to_sample
        data["current_sample_idx"] = self.current_sample_idx
        data["is_completed"] = self.is_completed
        data["grid_view_widgets"] = {"columns": self.grid_columns, "rows": self.grid_rows}
        data["view_widgets_config"] = self.view_widgets_config
        data["classification_buttons"] = self.buttons_config

        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(self.points):
            if point.is_classified:
                points_config[pnt_idx] = {"btn_id": point.btn_id, "feature_id": point.feature_id}
        data["points"] = points_config
        # save the samples order
        data["points_order"] = [p.feature_id for p in self.points]

        with open(file_out, 'w') as yaml_file:
            yaml.dump(data, yaml_file)

    def load_config(self, yaml_config):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # restore the thematic raster
        if yaml_config["thematic_raster"]["path"]:
            load_and_select_filepath_in(AcATaMa.dockwidget.selectThematicRaster,
                                        yaml_config["thematic_raster"]["path"], "raster")
            AcATaMa.dockwidget.nodata_ThematicRaster.setValue(yaml_config["thematic_raster"]["nodata"])
        # restore the classification settings
        AcATaMa.dockwidget.grid_columns.setValue(yaml_config["grid_view_widgets"]["columns"])
        AcATaMa.dockwidget.grid_rows.setValue(yaml_config["grid_view_widgets"]["rows"])
        self.grid_columns = yaml_config["grid_view_widgets"]["columns"]
        self.grid_rows = yaml_config["grid_view_widgets"]["rows"]
        self.current_sample_idx = yaml_config["current_sample_idx"]
        self.fit_to_sample = yaml_config["fit_to_sample"]
        self.is_completed = yaml_config["is_completed"]
        # restore the buttons config
        self.buttons_config = yaml_config["classification_buttons"]
        # restore the view widget config
        self.view_widgets_config = yaml_config["view_widgets_config"]
        # restore the samples order
        points_ordered = []
        for feature_id in yaml_config["points_order"]:
            points_ordered.append([p for p in self.points if p.feature_id == feature_id][0])
        self.points = points_ordered
        # restore point status classification
        for idx, status in yaml_config["points"].items():
            self.points[idx].btn_id = status["btn_id"]
            if self.points[idx].btn_id is not None:
                self.points[idx].is_classified = True
        # update the total classified progress bar
        total_classified = sum(sample.is_classified for sample in self.points)
        total_not_classified = sum(not sample.is_classified for sample in self.points)
        AcATaMa.dockwidget.ClassificationStatusPB.setValue(total_classified)
        # check is the classification is completed and update in dockwidget status
        if total_not_classified == 0:
            self.is_completed = True
            AcATaMa.dockwidget.ClassificationStatusLabel.setText("Classification completed")
            AcATaMa.dockwidget.ClassificationStatusLabel.setStyleSheet('QLabel {color: green;}')
        else:
            AcATaMa.dockwidget.ClassificationStatusLabel.setText("Classification not completed")
            AcATaMa.dockwidget.ClassificationStatusLabel.setStyleSheet('QLabel {color: orange;}')


