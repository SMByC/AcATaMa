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
from random import shuffle

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import NULL
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsVectorFileWriter, Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.point import LabelingPoint
from AcATaMa.core.map import Map
from AcATaMa.utils.system_utils import wait_process


class ResponseDesign(object):
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the label buttons properties
        # {label_id: {"name", "color", "thematic_class"}}
        self.buttons_config = None
        # get all points from the layer
        self.num_points = None
        self.points = self.get_points_from_shapefile()
        # save and init the current sample index
        self.current_sample_idx = 0
        # grid config
        self.grid_columns = 2
        self.grid_rows = 1
        # sampling unit
        self.sampling_unit_pixel_buffer = 0
        self.sampling_unit_color = QColor("red")
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
        # estimator needs for accuracy assessment results
        # -1 = None
        #  0 = Simple estimator
        #  1 = Simple post-stratified estimator
        #  2 = Stratified estimator
        self.estimator = -1
        # for store the instance of the analysis results
        self.analysis = None

        # shuffle the list items
        shuffle(self.points)
        # save instance
        ResponseDesign.instances[sampling_layer] = self

    def label_the_current_sample(self, label_id):
        current_sample = self.points[self.current_sample_idx]
        if label_id:  # label with valid integer class
            if current_sample.is_labeled is False:  # only when the label is changed
                self.total_labeled += 1
                self.total_unlabel -= 1 if self.total_unlabel > 0 else 0
            current_sample.label_id = label_id
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
                sample_id = qgs_feature.attributes()[attr_id]
            else:
                sample_id = enum_id
            x, y = geom.asPoint()
            points.append(LabelingPoint(x, y, sample_id))
        self.num_points = len(points)
        return points

    @wait_process
    def reload_sampling_file(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # update all points from file and restore its labels
        points_from_shapefile = self.get_points_from_shapefile()
        modified = 0
        for point in self.points:
            if point.sample_id in [p.sample_id for p in points_from_shapefile]:
                point_to_restore = [p for p in points_from_shapefile if p.sample_id == point.sample_id][0]
                point_to_restore.label_id = point.label_id
                if point_to_restore.label_id is not None:
                    point_to_restore.is_labeled = True
                if point.QgsPnt != point_to_restore.QgsPnt:
                    modified += 1
        # calc added/removed changes
        added = len(set([p.sample_id for p in points_from_shapefile]) - set([p.sample_id for p in self.points]))
        removed = len(set([p.sample_id for p in self.points]) - set([p.sample_id for p in points_from_shapefile]))
        # adjust the current sample id if some points are eliminated and its located before it
        for rm_sample_id in set([p.sample_id for p in self.points]) - set([p.sample_id for p in points_from_shapefile]):
            if [p.sample_id for p in self.points].index(rm_sample_id) <= self.current_sample_idx:
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
                              QgsField("Label ID", QVariant.Int)])
        vlayer.updateFields()  # tell the vector layer to fetch changes from the provider

        if self.with_thematic_classes:
            from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
            thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                               band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                               nodata=float(AcATaMa.dockwidget.nodata_ThematicMap.text().strip() or "nan"))

        points_ordered = sorted(self.points, key=lambda p: p.sample_id)
        for point in points_ordered:
            # add a feature
            feature = QgsFeature()
            feature.setGeometry(point.QgsGeom)
            name = self.buttons_config[point.label_id]["name"] if point.is_labeled else NULL
            if self.with_thematic_classes:
                validation_in_sample = int(
                    self.buttons_config[point.label_id]["thematic_class"]) if point.is_labeled else NULL
                thematic_map_in_sample = int(thematic_map.get_pixel_value_from_pnt(point.QgsPnt)) \
                    if point.is_labeled and thematic_map.get_pixel_value_from_pnt(point.QgsPnt) else NULL
                match = ('Yes' if thematic_map_in_sample == validation_in_sample else 'No') if point.is_labeled else NULL
                feature.setAttributes([point.sample_id, name, validation_in_sample, thematic_map_in_sample, match])
            else:
                feature.setAttributes([point.sample_id, name, point.label_id])
            pr.addFeatures([feature])

        vlayer.commitChanges()
        vlayer.updateExtents()

        file_format = \
            "GPKG" if file_out.endswith(".gpkg") else "ESRI Shapefile" if file_out.endswith(".shp") else None
        QgsVectorFileWriter.writeAsVectorFormat(vlayer, file_out, "System", self.sampling_layer.crs(), file_format)
