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
from random import shuffle

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import NULL
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsVectorFileWriter, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.point import LabelingPoint
from AcATaMa.core.raster import Raster
from AcATaMa.utils.system_utils import wait_process


class ResponseDesign(object):
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the label buttons properties
        # {classif_id: {"name", "color", "thematic_class"}}  # TODO migration
        self.buttons_config = None
        # get all points from the layer
        # [ClassificationPoint, ClassificationPoint, ...]  # TODO migration
        self.num_points = None
        self.points = self.get_points_from_shapefile()
        # save and init the current sample index
        self.current_sample_idx = 0
        # grid config
        self.grid_columns = 2
        self.grid_rows = 1
        # default radius to fit the sample based on the units of the sampling file selected
        layer_dist_unit = self.sampling_layer.crs().mapUnits()
        fit_to_sample_list = {QgsUnitTypes.DistanceMeters: 120, QgsUnitTypes.DistanceKilometers: 0.120,
                              QgsUnitTypes.DistanceFeet: 393, QgsUnitTypes.DistanceNauticalMiles: 0.065,
                              QgsUnitTypes.DistanceYards: 132, QgsUnitTypes.DistanceMiles: 0.075,
                              QgsUnitTypes.DistanceDegrees: 0.0011, QgsUnitTypes.DistanceCentimeters: 12000,
                              QgsUnitTypes.DistanceMillimeters: 120000}
        self.fit_to_sample = fit_to_sample_list[layer_dist_unit]
        # save views widget config
        # {N: {"view_name", "layer_name", "render_file_path", "render_activated", "scale_factor"}, ...}
        self.view_widgets_config = {}
        # response design dialog size
        self.dialog_size = None
        # if this response design was made with thematic classes
        self.with_thematic_classes = False
        # init label status
        self.total_labeled = 0
        self.total_unlabel = self.num_points
        # when all points are labeled
        self.is_completed = False
        # sampling type needs for accuracy assessment results
        # -1 = None
        #  0 = Simple random sampling
        #  1 = Simple random sampling post-stratified
        #  2 = Stratified random sampling
        self.sampling_type = -1
        # for store the instance of the accuracy assessment results
        self.accuracy_assessment = None

        # shuffle the list items
        shuffle(self.points)
        # save instance
        ResponseDesign.instances[sampling_layer] = self

    def label_the_current_sample(self, classif_id):
        current_sample = self.points[self.current_sample_idx]
        if classif_id:  # label with valid integer class
            if current_sample.is_labeled is False:  # only when the label is changed
                self.total_labeled += 1
                self.total_unlabel -= 1 if self.total_unlabel > 0 else 0
            current_sample.label_id = classif_id
            current_sample.is_labeled = True
        else:  # unlabel the sample
            if current_sample.is_labeled is True:  # only when the sample label is changed
                self.total_labeled -= 1 if self.total_labeled > 0 else 0
                self.total_unlabel += 1
            current_sample.label_id = None
            current_sample.is_labeled = False
        self.is_completed = True if self.total_unlabel == 0 else False

    def reload_labeling_status(self):
        self.total_labeled = sum(sample.is_labeled for sample in self.points)
        self.total_unlabel = sum(not sample.is_labeled for sample in self.points)
        self.is_completed = True if self.total_unlabel == 0 else False

    def get_points_from_shapefile(self):
        points = []
        for enum_id, qgs_feature in enumerate(self.sampling_layer.getFeatures(), start=1):
            geom = qgs_feature.geometry()
            # get the id from shape file using column name "id" else use auto-enumeration
            attr_id = self.sampling_layer.fields().lookupField('id')
            if attr_id != -1:
                shape_id = qgs_feature.attributes()[attr_id]
            else:
                shape_id = enum_id
            x, y = geom.asPoint()
            points.append(LabelingPoint(x, y, shape_id))
        self.num_points = len(points)
        return points

    @wait_process
    def reload_sampling_file(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # update all points from file and restore its labels
        points_from_shapefile = self.get_points_from_shapefile()
        modified = 0
        for point in self.points:
            if point.shape_id in [p.shape_id for p in points_from_shapefile]:
                point_to_restore = [p for p in points_from_shapefile if p.shape_id == point.shape_id][0]
                point_to_restore.label_id = point.label_id
                if point_to_restore.label_id is not None:
                    point_to_restore.is_labeled = True
                if point.QgsPnt != point_to_restore.QgsPnt:
                    modified += 1
        # calc added/removed changes
        added = len(set([p.shape_id for p in points_from_shapefile]) - set([p.shape_id for p in self.points]))
        removed = len(set([p.shape_id for p in self.points]) - set([p.shape_id for p in points_from_shapefile]))
        # adjust the current sample id if some points are eliminated and its located before it
        for rm_shape_id in set([p.shape_id for p in self.points]) - set([p.shape_id for p in points_from_shapefile]):
            if [p.shape_id for p in self.points].index(rm_shape_id) <= self.current_sample_idx:
                self.current_sample_idx -= 1
        # check if sampling has not changed
        if modified == 0 and added == 0 and removed == 0:
            iface.messageBar().pushMessage("AcATaMa", "The sampling file has not detected changes",
                                           level=Qgis.Success)
            return
        # reassign points
        self.points = points_from_shapefile
        # update the status and labels for the current sampling file
        self.reload_labeling_status()
        AcATaMa.dockwidget.update_response_design_state()
        # notify
        iface.messageBar().pushMessage("AcATaMa", "Sampling file reloaded successfully: {} modified,"
                                                  "{} added and {} removed".format(modified, added, removed),
                                       level=Qgis.Success)

    @wait_process
    def save_sampling_labeled(self, file_out):
        crs = self.sampling_layer.crs().toWkt()
        # create layer
        vlayer = QgsVectorLayer("Point?crs=" + crs, "temporary_points", "memory")
        pr = vlayer.dataProvider()
        # add fields
        if self.with_thematic_classes:
            pr.addAttributes([QgsField("ID", QVariant.Int),
                              QgsField("Label", QVariant.String),
                              QgsField("Is labeled", QVariant.Int),
                              QgsField("Thematic Class", QVariant.Int),
                              QgsField("Match", QVariant.String)])
        else:
            pr.addAttributes([QgsField("ID", QVariant.Int),
                              QgsField("Label", QVariant.String),
                              QgsField("Classif ID", QVariant.Int)])  # TODO migration
        vlayer.updateFields()  # tell the vector layer to fetch changes from the provider

        if self.with_thematic_classes:
            from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
            ThematicR = Raster(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicRaster,
                               band=int(AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText()),
                               nodata=int(AcATaMa.dockwidget.nodata_ThematicRaster.value()))

        points_ordered = sorted(self.points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # add a feature
            feature = QgsFeature()
            feature.setGeometry(point.QgsGeom)
            name = self.buttons_config[point.label_id]["name"] if point.is_labeled else NULL
            if self.with_thematic_classes:
                thematic_class = int(
                    self.buttons_config[point.label_id]["thematic_class"]) if point.is_labeled else NULL
                thematic_map_value = int(ThematicR.get_pixel_value_from_pnt(point.QgsPnt)) \
                    if point.is_labeled and ThematicR.get_pixel_value_from_pnt(point.QgsPnt) else NULL
                match = ('Yes' if thematic_map_value == thematic_class else 'No') if point.is_labeled else NULL
                feature.setAttributes([point.shape_id, name, thematic_class, thematic_map_value, match])
            else:
                feature.setAttributes([point.shape_id, name, point.label_id])
            pr.addFeatures([feature])

        vlayer.commitChanges()
        vlayer.updateExtents()

        file_format = \
            "GPKG" if file_out.endswith(".gpkg") else "ESRI Shapefile" if file_out.endswith(".shp") else None
        QgsVectorFileWriter.writeAsVectorFormat(vlayer, file_out, "System", self.sampling_layer.crs(), file_format)
