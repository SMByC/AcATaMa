# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2018 by Xavier Corredor Llano, SMByC
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

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import NULL
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsVectorFileWriter, Qgis
from qgis.utils import iface

from AcATaMa.core.point import ClassificationPoint
from AcATaMa.core.raster import Raster
from AcATaMa.utils.qgis_utils import get_current_file_path_in, get_file_path_of_layer, load_and_select_filepath_in
from AcATaMa.utils.system_utils import wait_process


class Classification(object):
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
        # {N: {"view_name", "layer_name", "render_file_path", "render_activated", "scale_factor"}, ...}
        self.view_widgets_config = {}
        # classification dialog size
        self.dialog_size = None
        # if this classification was made with thematic classes
        self.with_thematic_classes = False
        # when all points are classified
        self.is_completed = False
        # for store the instance of the accuracy assessment results
        self.accuracy_assessment = None

        # shuffle the list items
        shuffle(self.points)
        # save instance
        Classification.instances[sampling_layer] = self

    def get_points_from_shapefile(self):
        points = []
        for qgs_feature in self.sampling_layer.getFeatures():
            geom = qgs_feature.geometry()
            # get the id from shape file
            idx = self.sampling_layer.fields().lookupField('id')
            shape_id = qgs_feature.attributes()[idx]

            x, y = geom.asPoint()
            points.append(ClassificationPoint(x, y, shape_id))
        return points

    @wait_process()
    def save_config(self, file_out):
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
        data["thematic_raster"] = \
            {"path": get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicRaster, show_message=False),
             "band": int(AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText())
                if AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText() else None,
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
            # thematic raster
            load_and_select_filepath_in(AcATaMa.dockwidget.QCBox_ThematicRaster,
                                        yaml_config["thematic_raster"]["path"], "raster")
            AcATaMa.dockwidget.select_thematic_raster()
            # nodata
            AcATaMa.dockwidget.nodata_ThematicRaster.setValue(yaml_config["thematic_raster"]["nodata"])
            # band number
            if "band" in yaml_config["thematic_raster"]:
                AcATaMa.dockwidget.QCBox_band_ThematicRaster.setCurrentIndex(yaml_config["thematic_raster"]["band"] - 1)

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

        # support load the old format of config file TODO: delete
        for x in self.view_widgets_config.values():
            if "render_file" in x:
                x["render_file_path"] = x["render_file"]
                del x["render_file"]
            if "name" in x:
                x["view_name"] = x["name"]
                del x["name"]

        # restore the samples order
        points_ordered = []
        for shape_id in yaml_config["points_order"]:
            # point saved exist in shape file
            if shape_id in [p.shape_id for p in self.points]:
                points_ordered.append([p for p in self.points if p.shape_id == shape_id][0])
        # added new point inside shape file that not exists in yaml config
        for new_point_id in set([p.shape_id for p in self.points]) - set(yaml_config["points_order"]):
            points_ordered.append([p for p in self.points if p.shape_id == new_point_id][0])
        # reassign points loaded and ordered
        self.points = points_ordered
        # restore point status classification
        for status in yaml_config["points"].values():
            if status["shape_id"] in [p.shape_id for p in self.points]:
                point_to_restore = [p for p in self.points if p.shape_id == status["shape_id"]][0]
                point_to_restore.classif_id = status["classif_id"]
                if point_to_restore.classif_id is not None:
                    point_to_restore.is_classified = True
        # update plugin
        self.update_plugin_after_reload_sampling()
        # define if this classification was made with thematic classes
        if self.buttons_config and True in [bc["thematic_class"] is not None and bc["thematic_class"] != "" for bc in
                                            self.buttons_config.values()]:
            self.with_thematic_classes = True

    @wait_process()
    def reload_sampling_file(self):
        # update all points from file and restore its status classification
        points_from_shapefile = self.get_points_from_shapefile()
        modified = 0
        for point in self.points:
            if point.shape_id in [p.shape_id for p in points_from_shapefile]:
                point_to_restore = [p for p in points_from_shapefile if p.shape_id == point.shape_id][0]
                point_to_restore.classif_id = point.classif_id
                if point_to_restore.classif_id is not None:
                    point_to_restore.is_classified = True
                if point.QgsPnt != point_to_restore.QgsPnt:
                    modified += 1
        # calc added/removed changes
        added = len(set([p.shape_id for p in points_from_shapefile]) - set([p.shape_id for p in self.points]))
        removed = len(set([p.shape_id for p in self.points]) - set([p.shape_id for p in points_from_shapefile]))
        # check if sampling has not changed
        if modified == 0 and added == 0 and removed == 0:
            iface.messageBar().pushMessage("AcATaMa", "The sampling file has not detected changes",
                                           level=Qgis.Success)
            return
        # reassign points
        self.points = points_from_shapefile
        # update plugin
        self.update_plugin_after_reload_sampling()
        # notify
        iface.messageBar().pushMessage("AcATaMa", "Sampling file reloaded successfully: {} modified,"
                                                  "{} added and {} removed".format(modified, added, removed),
                                       level=Qgis.Success)

    def update_plugin_after_reload_sampling(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # check the current_sample_idx after reload the sampling file
        if self.current_sample_idx >= len(self.points) - 1:
            self.current_sample_idx = len(self.points) - 1
        # update the total classified progress bar
        total_classified = sum(sample.is_classified for sample in self.points)
        total_not_classified = sum(not sample.is_classified for sample in self.points)
        AcATaMa.dockwidget.QPBar_ClassificationStatus.setMaximum(len(self.points))
        AcATaMa.dockwidget.QPBar_ClassificationStatus.setValue(total_classified)
        AcATaMa.dockwidget.QPBar_ClassificationStatus.setTextVisible(True)
        # check is the classification is completed and update in dockwidget status
        if total_not_classified == 0:
            self.is_completed = True
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: green;}')
        else:
            self.is_completed = False
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setText("Classification not completed")
            AcATaMa.dockwidget.QLabel_ClassificationStatus.setStyleSheet('QLabel {color: orange;}')
        # update state of sampling file selected for accuracy assessment tab
        AcATaMa.dockwidget.set_sampling_file_accuracy_assessment()

    @wait_process()
    def save_sampling_classification(self, file_out):
        crs = self.sampling_layer.crs().toWkt()
        # create layer
        vlayer = QgsVectorLayer("Point?crs=" + crs, "temporary_points", "memory")
        pr = vlayer.dataProvider()
        # add fields
        if self.with_thematic_classes:
            pr.addAttributes([QgsField("ID", QVariant.Int),
                              QgsField("Class Name", QVariant.String),
                              QgsField("Classified", QVariant.Int),
                              QgsField("thematic_raster", QVariant.Int),
                              QgsField("Match", QVariant.String)])
        else:
            pr.addAttributes([QgsField("ID", QVariant.Int),
                              QgsField("Class Name", QVariant.String),
                              QgsField("Classif ID", QVariant.Int)])
        vlayer.updateFields()  # tell the vector layer to fetch changes from the provider

        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        ThematicR = Raster(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicRaster,
                           band=int(AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText()),
                           nodata=int(AcATaMa.dockwidget.nodata_ThematicRaster.value()))

        points_ordered = sorted(self.points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # add a feature
            feature = QgsFeature()
            feature.setGeometry(point.QgsGeom)
            name = self.buttons_config[point.classif_id]["name"] if point.is_classified else NULL
            if self.with_thematic_classes:
                classified = int(
                    self.buttons_config[point.classif_id]["thematic_class"]) if point.is_classified else NULL
                thematic = int(ThematicR.get_pixel_value_from_pnt(point.QgsPnt)) \
                    if point.is_classified and ThematicR.get_pixel_value_from_pnt(point.QgsPnt) else NULL
                match = ('Yes' if thematic == classified else 'No') if point.is_classified else NULL
                feature.setAttributes([point.shape_id, name, classified, thematic, match])
            else:
                feature.setAttributes([point.shape_id, name, point.classif_id])
            pr.addFeatures([feature])

        vlayer.commitChanges()
        vlayer.updateExtents()

        QgsVectorFileWriter.writeAsVectorFormat(vlayer, file_out, "utf-8", self.sampling_layer.crs(), "ESRI Shapefile")
