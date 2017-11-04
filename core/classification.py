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

from PyQt4.QtCore import QVariant
from qgis.PyQt.QtCore import NULL
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsVectorFileWriter

from AcATaMa.core.dockwidget import get_current_file_path_in, get_file_path_of_layer, load_and_select_filepath_in
from AcATaMa.core.point import ClassificationPoint
from AcATaMa.core.utils import wait_process


class Classification:
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the classification buttons properties
        # {classif_id: {"name", "color", "thematic_class"}}
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
        # {N: {"name", "render_file", "render_activated", "scale_factor"}, ...}
        self.view_widgets_config = {}
        # classification dialog size
        self.dialog_size = None
        # when all points are classified
        self.is_completed = False
        # instance of accuracy assessment result
        self.accuracy_assessment = None

        # shuffle the list items
        shuffle(self.points)
        # save instance
        Classification.instances[sampling_layer] = self

    def get_points_from_shapefile(self):
        points = []
        for shape_id, qgs_feature in enumerate(self.sampling_layer.getFeatures()):
            geom = qgs_feature.geometry()
            x, y = geom.asPoint()
            points.append(ClassificationPoint(x, y, shape_id+1))
        return points

    @wait_process()
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
            {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicRaster, show_message=False),
             "nodata": AcATaMa.dockwidget.nodata_ThematicRaster.value()}
        data["sampling_layer"] = get_file_path_of_layer(self.sampling_layer)
        data["dialog_size"] = self.dialog_size
        data["grid_view_widgets"] = {"columns": self.grid_columns, "rows": self.grid_rows}
        data["current_sample_idx"] = self.current_sample_idx
        data["fit_to_sample"] = self.fit_to_sample
        data["is_completed"] = self.is_completed
        data["view_widgets_config"] = self.view_widgets_config
        data["classification_buttons"] = self.buttons_config

        # save samples status
        points_config = {}
        for pnt_idx, point in enumerate(self.points):
            if point.is_classified:
                points_config[pnt_idx] = {"classif_id": point.classif_id, "shape_id": point.shape_id}
        data["points"] = points_config
        # save the samples order
        data["points_order"] = [p.shape_id for p in self.points]

        with open(file_out, 'w') as yaml_file:
            yaml.dump(data, yaml_file)

    @wait_process()
    def load_config(self, yaml_config):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # restore the thematic raster
        if yaml_config["thematic_raster"]["path"]:
            load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_ThematicRaster,
                                        yaml_config["thematic_raster"]["path"], "raster")
            AcATaMa.dockwidget.nodata_ThematicRaster.setValue(yaml_config["thematic_raster"]["nodata"])
        # restore the classification settings
        AcATaMa.dockwidget.grid_columns.setValue(yaml_config["grid_view_widgets"]["columns"])
        AcATaMa.dockwidget.grid_rows.setValue(yaml_config["grid_view_widgets"]["rows"])
        self.dialog_size = yaml_config["dialog_size"]
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
        for shape_id in yaml_config["points_order"]:
            points_ordered.append([p for p in self.points if p.shape_id == shape_id][0])
        self.points = points_ordered
        # restore point status classification
        for idx, status in yaml_config["points"].items():
            self.points[idx].classif_id = status["classif_id"]
            if self.points[idx].classif_id is not None:
                self.points[idx].is_classified = True
        # update the total classified progress bar
        total_classified = sum(sample.is_classified for sample in self.points)
        total_not_classified = sum(not sample.is_classified for sample in self.points)
        AcATaMa.dockwidget.QPBar_ClassificationStatus.setValue(total_classified)
        # check is the classification is completed and update in dockwidget status
        if total_not_classified == 0:
            self.is_completed = True
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: green;}')
        else:
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification not completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: orange;}')
        # updated state of sampling file selected for accuracy assessment tab
        AcATaMa.dockwidget.set_sampling_file_accuracy_assessment()

    @wait_process()
    def save_sampling_classification(self, file_out):
        crs = self.sampling_layer.crs().toWkt()
        # create layer
        vlayer = QgsVectorLayer("Point?crs=" + crs, "temporary_points", "memory")
        pr = vlayer.dataProvider()
        # add fields
        pr.addAttributes([QgsField("ID", QVariant.Int),
                          QgsField("ClassID", QVariant.Int),
                          QgsField("ClassName", QVariant.String),
                          QgsField("ThematicID", QVariant.Int)])
        vlayer.updateFields()  # tell the vector layer to fetch changes from the provider

        points_ordered = sorted(self.points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # add a feature
            feature = QgsFeature()
            feature.setGeometry(point.QgsGeom)
            name = self.buttons_config[point.classif_id]["name"] if point.classif_id else None
            thematic_class = self.buttons_config[point.classif_id]["thematic_class"] if point.classif_id else None
            feature.setAttributes([point.shape_id, point.classif_id,
                                   name if name is not None else NULL,
                                   thematic_class if thematic_class is not None else NULL])
            pr.addFeatures([feature])

        vlayer.commitChanges()
        vlayer.updateExtents()

        QgsVectorFileWriter.writeAsVectorFormat(vlayer, file_out, "utf-8", self.sampling_layer.crs(), "ESRI Shapefile")
