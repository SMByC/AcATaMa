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
import os
import random

from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsSpatialIndex, QgsFeature, Qgis, \
    QgsVectorFileWriter, QgsWkbTypes, QgsUnitTypes

from AcATaMa.core.point import RandomPoint
from AcATaMa.core.map import Map
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.qgis_utils import load_layer, valid_file_selected_in
from AcATaMa.utils.system_utils import wait_process, error_handler


@error_handler
def do_simple_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if dockwidget.QGBox_SimpRSwithCR.isChecked():
        if not valid_file_selected_in(dockwidget.QCBox_CategMap_SimpRS, "categorical map"):
            return

    thematic_map = Map(file_selected_combo_box=dockwidget.QCBox_ThematicMap,
                       band=int(dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(dockwidget.nodata_ThematicMap.text().strip() or "nan"))

    # get and define some variables
    total_of_samples = int(dockwidget.numberOfSamples_SimpRS.value())
    min_distance = float(dockwidget.minDistance_SimpRS.value())

    # simple random sampling in categorical map
    if dockwidget.QGBox_SimpRSwithCR.isChecked():
        categorical_map = Map(file_selected_combo_box=dockwidget.QCBox_CategMap_SimpRS,
                              band=int(dockwidget.QCBox_band_CategMap_SimpRS.currentText()))
        try:
            classes_selected = [int(p) for p in dockwidget.QPBtn_CategMapClassesSelection_SimpRS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option enabled but none of the classes were selected",
                                           level=Qgis.Warning, duration=5)
            return
    else:
        categorical_map = None
        classes_selected = None

    # check neighbors aggregation
    if dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path),
                                      "simple {}sampling.gpkg".format("post-stratified " if categorical_map else ""))
    output_file, _ = QFileDialog.getSaveFileName(dockwidget,
                                                 dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if output_file == '':
        return

    # define the random seed
    if dockwidget.widget_generate_SimpRS.with_random_seed_by_user.isChecked():
        random_seed = dockwidget.widget_generate_SimpRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setText("Generating...")

    # process
    sampling = Sampling("simple", thematic_map, categorical_map, output_file=output_file)
    sampling.generate_sampling_points(total_of_samples, min_distance, classes_selected, neighbor_aggregation,
                                      random_seed, dockwidget.widget_generate_SimpRS.QPBar_GenerateSamples)

    # restoring
    dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setText("Generate samples")

    # zero points
    if sampling.samples_generated < total_of_samples and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings",
                                       level=Qgis.Warning, duration=-1)
        return

    # success
    if sampling.samples_generated == total_of_samples:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful simple random sampling with {} samples generated"
                                       .format(sampling.samples_generated), level=Qgis.Success)
    # success but not completed
    if total_of_samples > sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful simple random sampling, but could not generate the requested number of "
                                                  "random points {}/{}, sampling process aborted".format(sampling.samples_generated, total_of_samples),
                                       level=Qgis.Warning)
    # check the thematic map unit to calculate the minimum distances
    if min_distance > 0:
        if thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                "The thematic map \"{}\" does not have a valid map unit, AcATaMa used \"{}\" as the base unit to "
                "calculate the minimum distances.".format(
                    thematic_map.qgs_layer.name(), QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                level=Qgis.Warning, duration=-1)
    # select the sampling file generated in respond design and analysis tab
    dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(0 if categorical_map is None else 1)


@error_handler
def do_stratified_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if not valid_file_selected_in(dockwidget.QCBox_CategMap_StraRS, "categorical map"):
        return
    # get and define some variables
    min_distance = float(dockwidget.minDistance_StraRS.value())
    thematic_map = Map(file_selected_combo_box=dockwidget.QCBox_ThematicMap,
                       band=int(dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    categorical_map = Map(file_selected_combo_box=dockwidget.QCBox_CategMap_StraRS,
                          band=int(dockwidget.QCBox_band_CategMap_StraRS.currentText()),
                          nodata=float(dockwidget.nodata_CategMap_StraRS.text().strip() or "nan"))

    # get values from category table  #########
    classes_for_sampling = []
    total_of_samples_by_cat = []
    for row in range(dockwidget.QTableW_StraRS.rowCount()):
        classes_for_sampling.append(int(dockwidget.QTableW_StraRS.item(row, 0).text()))
        total_of_samples_by_cat.append(dockwidget.QTableW_StraRS.item(row, 2).text())
    # convert and check if number of samples only positive integers
    try:
        total_of_samples_by_cat = [int(ns) for ns in total_of_samples_by_cat]
        if True in [ns < 0 for ns in total_of_samples_by_cat]:
            raise Exception
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, the number of samples should be only positive integers",
                                       level=Qgis.Warning)
        return
    total_of_samples = sum(total_of_samples_by_cat)
    if total_of_samples == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, no number of samples configured!",
                                       level=Qgis.Warning)
        return

    # check neighbors aggregation
    if dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_StraRS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_StraRS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the method of stratified sampling and save StraRS config
    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        sampling_method = "fixed values"
        srs_config = None
    if dockwidget.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        sampling_method = "area based proportion"
        srs_config = {}
        # save total expected std error
        srs_config["total_std_error"] = dockwidget.TotalExpectedSE.value()
        # get std_dev from table
        srs_config["std_dev"] = []
        for row in range(dockwidget.QTableW_StraRS.rowCount()):
            srs_config["std_dev"].append(float(dockwidget.QTableW_StraRS.item(row, 3).text()))

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path), "stratified sampling.gpkg")
    output_file, _ = QFileDialog.getSaveFileName(dockwidget,
                                                 dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if output_file == '':
        return

    # define the random seed
    if dockwidget.widget_generate_StraRS.with_random_seed_by_user.isChecked():
        random_seed = dockwidget.widget_generate_StraRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setText("Generating...")

    # process
    sampling = Sampling("stratified", thematic_map, categorical_map, sampling_method,
                        srs_config=srs_config, output_file=output_file)
    sampling.generate_sampling_points(total_of_samples_by_cat, min_distance, classes_for_sampling, neighbor_aggregation,
                                      random_seed, dockwidget.widget_generate_StraRS.QPBar_GenerateSamples)

    # before process
    dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setText("Generate samples")

    # zero points
    if sampling.samples_generated < total_of_samples and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any stratified random points with this settings",
                                                  level=Qgis.Warning, duration=-1)
        return

    # success
    if sampling.samples_generated == total_of_samples:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful stratified random sampling with {} samples generated"
                                       .format(sampling.samples_generated), level=Qgis.Success)
    # success but not completed
    if sampling.samples_generated < total_of_samples and sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful stratified random sampling, but could not generate the requested number of "
                                                  "random points {}/{}, sampling process aborted".format(sampling.samples_generated, total_of_samples),
                                       level=Qgis.Warning)
    # check the thematic map unit to calculate the minimum distances
    if min_distance > 0:
        if thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                "The thematic map \"{}\" does not have a valid map unit, AcATaMa used \"{}\" as the base unit to "
                "calculate the minimum distances.".format(
                    thematic_map.qgs_layer.name(), QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                level=Qgis.Warning, duration=-1)
    # select the sampling file generated in respond design and analysis tab
    dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(2)


@error_handler
def do_systematic_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.QCBox_ThematicMap, "thematic map"):
        return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=dockwidget.QCBox_ThematicMap,
                       band=int(dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    points_spacing = float(dockwidget.PointsSpacing_SystS.value())
    initial_inset = float(dockwidget.InitialInset_SystS.value())
    max_xy_offset = float(dockwidget.MaxXYoffset_SystS.value())
    total_of_samples = dockwidget.widget_generate_SystS.QPBar_GenerateSamples.maximum()

    # systematic sampling in categorical map
    if dockwidget.QGBox_SystSwithCR.isChecked():
        categorical_map = Map(file_selected_combo_box=dockwidget.QCBox_CategMap_SystS,
                              band=int(dockwidget.QCBox_band_CategMap_SystS.currentText()))
        try:
            classes_selected = [int(p) for p in dockwidget.QPBtn_CategMapClassesSelection_SystS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option enabled but none of the classes were selected",
                                           level=Qgis.Warning, duration=5)
            return
    else:
        categorical_map = None
        classes_selected = None

    # check neighbors aggregation
    if dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_SystS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_SystS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path),
                                      "systematic {}sampling.gpkg".format("post-stratified " if categorical_map else ""))
    output_file, _ = QFileDialog.getSaveFileName(dockwidget,
                                                 dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if output_file == '':
        return

    # define the random seed
    if dockwidget.widget_generate_SystS.with_random_seed_by_user.isChecked():
        random_seed = dockwidget.widget_generate_SystS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setText("Generating...")

    # process
    sampling = Sampling("systematic", thematic_map, categorical_map, "grid with random offset", output_file=output_file)
    sampling.generate_systematic_sampling_points(points_spacing, initial_inset, max_xy_offset,
                                                 classes_selected, neighbor_aggregation, random_seed,
                                                 dockwidget.widget_generate_SystS.QPBar_GenerateSamples)

    # restoring
    dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setText("Generate samples")

    # zero points
    if sampling.samples_generated < total_of_samples and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings",
                                       level=Qgis.Warning, duration=-1)
        return

    # success
    if sampling.samples_generated == total_of_samples:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful systematic sampling with {} samples generated"
                                       .format(sampling.samples_generated), level=Qgis.Success)
    # success but not completed
    if total_of_samples > sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa",
                                       "Successful systematic sampling with {} samples generated, filtered from a max of {}"
                                       .format(sampling.samples_generated, total_of_samples), level=Qgis.Success)

    # select the sampling file generated in respond design and analysis tab
    dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(0 if categorical_map is None else 1)


class Sampling(object):

    def __init__(self, sampling_design_type, thematic_map, categorical_map, sampling_method=None, srs_config=None, output_file=None):
        self.sampling_design_type = sampling_design_type
        self.thematic_map = thematic_map
        self.categorical_map = categorical_map
        # for stratified sampling
        self.sampling_method = sampling_method
        # save some stratified sampling configuration
        self.srs_config = srs_config
        # set the output dir for save sampling
        self.output_file = output_file
        # for save all sampling points
        self.points = dict()

    @wait_process
    def generate_sampling_points(self, total_of_samples, min_distance, classes_for_sampling,
                                 neighbor_aggregation, random_seed, progress_bar):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/release-2_18/python/plugins/processing/algs/qgis/RandomPointsExtent.py
        """
        self.total_of_samples = total_of_samples  # desired
        self.samples_generated = None  # total generated
        self.min_distance = min_distance
        self.classes_for_sampling = classes_for_sampling
        self.neighbor_aggregation = neighbor_aggregation
        progress_bar.setValue(0)  # init progress bar

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        if self.sampling_design_type == "simple":
            total_of_samples = self.total_of_samples
        if self.sampling_design_type == "stratified":
            total_of_samples = sum(self.total_of_samples)
            self.samples_in_categories = [0] * len(self.total_of_samples)  # total generated by categories

        nPoints = 0
        nIterations = 0
        self.index = QgsSpatialIndex()

        # init the random sampling seed
        self.random_seed = random_seed
        random.seed(self.random_seed)

        points_generated = []
        while nPoints < total_of_samples:

            random_sampling_point = RandomPoint.fromExtent(self.thematic_map.extent())

            # checks to the sampling point, else discard and continue
            if not self.check_sampling_point(random_sampling_point):
                if nIterations == 150000:
                    nPoints20k = nPoints
                if nIterations == 200000 and nPoints <= nPoints20k+2:
                    quit_msg = "The sampling process seems stuck due to sampling conditions. Do you want to continue " \
                               "this sampling process and never ask this again? or cancel it?"
                    reply = QMessageBox.question(None, "Continue sampling process", quit_msg, QMessageBox.Yes,
                                                 QMessageBox.Cancel)
                    if reply == QMessageBox.Cancel:
                        break
                nIterations += 1
                continue

            if self.sampling_design_type == "stratified":
                self.samples_in_categories[random_sampling_point.index_pixel_value] += 1

            points_generated.append(random_sampling_point)

            # it requires tmp save the point to check min distance for the next sample
            f = QgsFeature(nPoints)
            f.setGeometry(random_sampling_point.QgsGeom)
            self.index.insertFeature(f)
            self.points[nPoints] = random_sampling_point.QgsPnt

            nPoints += 1
            nIterations += 1
            # update progress bar
            progress_bar.setValue(int(nPoints))

        # guarantee the random order for response design process
        random.shuffle(points_generated)
        self.points = dict()  # restart

        for num_point, point_generated in enumerate(points_generated):
            # random sampling point passed the checks, save it
            f = QgsFeature()
            f.initAttributes(1)
            f.setFields(fields)
            f.setAttribute('id', num_point+1)
            f.setGeometry(point_generated.QgsGeom)
            writer.addFeature(f)
            self.points[num_point] = point_generated.QgsPnt

        # save the total point generated
        self.samples_generated = len(points_generated)
        del writer, self.index

    @wait_process
    def generate_systematic_sampling_points(self, points_spacing, initial_inset, max_xy_offset,
                                            classes_for_sampling, neighbor_aggregation, random_seed, progress_bar):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/master/python/plugins/processing/algs/qgis/RegularPoints.py
        """
        self.points_spacing = points_spacing
        self.initial_inset = initial_inset
        self.max_xy_offset = max_xy_offset
        self.classes_for_sampling = classes_for_sampling
        self.neighbor_aggregation = neighbor_aggregation
        self.samples_generated = None  # total generated
        progress_bar.setValue(0)  # init progress bar

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        # add an epsilon to accept sampling points on the edge of the map
        epsilon = 0.00001
        initial_inset += epsilon

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        nPoints = 0
        y = self.thematic_map.extent().yMaximum() - initial_inset
        extent_geom = QgsGeometry.fromRect(self.thematic_map.extent())
        extent_engine = QgsGeometry.createGeometryEngine(extent_geom.constGet())
        extent_engine.prepareGeometry()

        # init the random sampling seed
        self.random_seed = random_seed
        random.seed(self.random_seed)

        points_generated = []
        while y >= self.thematic_map.extent().yMinimum():
            x = self.thematic_map.extent().xMinimum() + initial_inset
            while x <= self.thematic_map.extent().xMaximum():
                attempts = 0
                while True:
                    if attempts == 1000:
                        x += points_spacing
                        break
                    if max_xy_offset > 0:
                        # step 2: random offset
                        rx = random.uniform(x - max_xy_offset, x + max_xy_offset)
                        ry = random.uniform(y - max_xy_offset, y + max_xy_offset)
                        random_sampling_point = RandomPoint(rx, ry)
                    else:
                        # systematic sampling aligned with the grid, offset = 0
                        random_sampling_point = RandomPoint(x, y)

                    if not extent_engine.intersects(random_sampling_point.QgsGeom.constGet()):
                        attempts += 1
                        continue

                    # checks to the sampling point, else discard and continue
                    if not self.check_sampling_point(random_sampling_point):
                        attempts += 1
                        continue

                    points_generated.append(random_sampling_point)

                    x += points_spacing
                    nPoints += 1
                    # update progress bar
                    progress_bar.setValue(int(nPoints))
                    break

            y = y - points_spacing

        # guarantee the random order for response design process
        random.shuffle(points_generated)
        self.points = dict()  # restart

        for num_point, point_generated in enumerate(points_generated):
            # random sampling point passed the checks, save it
            f = QgsFeature()
            f.initAttributes(1)
            f.setFields(fields)
            f.setAttribute('id', num_point+1)
            f.setGeometry(point_generated.QgsGeom)
            writer.addFeature(f)
            self.points[num_point] = point_generated.QgsPnt

        # save the total point generated
        self.samples_generated = len(points_generated)
        del writer

    def check_sampling_point(self, sampling_point):
        """Make several checks to the sampling point, else discard
        """
        if not sampling_point.in_valid_data(self.thematic_map):
            return False

        if not sampling_point.in_extent(self.ThematicR_boundaries):
            return False

        if self.sampling_design_type in ["simple", "stratified"]:
            if not sampling_point.in_mim_distance(self.index, self.min_distance, self.points):
                return False

        if self.sampling_design_type in ["simple", "systematic"]:
            if not sampling_point.in_categorical_map_post_stratify(self.classes_for_sampling, self.categorical_map):
                return False

        if self.sampling_design_type == "stratified":
            if not sampling_point.in_categorical_map_StraRS(self.classes_for_sampling, self.total_of_samples,
                                                            self.categorical_map, self.samples_in_categories):
                return False

        if self.neighbor_aggregation and \
                not sampling_point.check_neighbors_aggregation(self.thematic_map, *self.neighbor_aggregation):
            return False

        return True
