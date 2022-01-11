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
import configparser
import random

from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsSpatialIndex, \
    QgsFeature, Qgis, QgsVectorFileWriter, QgsWkbTypes, QgsUnitTypes

from AcATaMa.core.point import RandomPoint
from AcATaMa.core.raster import Raster
from AcATaMa.utils.qgis_utils import load_layer, valid_file_selected_in
from AcATaMa.utils.system_utils import wait_process, error_handler


@error_handler
def do_simple_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.QCBox_ThematicRaster, "thematic raster"):
        return
    if dockwidget.QGBox_SimpRSwithCR.isChecked():
        if not valid_file_selected_in(dockwidget.QCBox_CategRaster_SimpRS, "categorical raster"):
            return

    ThematicR = Raster(file_selected_combo_box=dockwidget.QCBox_ThematicRaster,
                       band=int(dockwidget.QCBox_band_ThematicRaster.currentText()),
                       nodata=int(dockwidget.nodata_ThematicRaster.value()))

    # get and define some variables
    number_of_samples = int(dockwidget.numberOfSamples_SimpRS.value())
    min_distance = float(dockwidget.minDistance_SimpRS.value())

    # simple random sampling in categorical raster
    if dockwidget.QGBox_SimpRSwithCR.isChecked():
        CategoricalR = Raster(file_selected_combo_box=dockwidget.QCBox_CategRaster_SimpRS,
                              band=int(dockwidget.QCBox_band_CategRaster_SimpRS.currentText()))
        try:
            pixel_values = [int(p) for p in dockwidget.pixelsValuesCategRaster.text().split(",")]
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, wrong pixel values, set only integers and separated by commas",
                                           level=Qgis.Warning)
            return
    else:
        CategoricalR = None
        pixel_values = None

    # check neighbors aggregation
    if dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the attempts_by_sampling
    if dockwidget.widget_generate_SimpRS.button_attempts_by_sampling.isChecked():
        attempts_by_sampling = int(dockwidget.widget_generate_SimpRS.attempts_by_sampling.value())
    else:
        attempts_by_sampling = None

    # first select the target dir for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(ThematicR.file_path), "random_sampling.gpkg")
    output_file, _ = QFileDialog.getSaveFileName(dockwidget,
                                                 dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if output_file == '':
        return

    # define the random seed
    if dockwidget.widget_generate_SimpRS.button_random_seed_by_user.isChecked():
        random_seed = dockwidget.widget_generate_SimpRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # process
    sampling = Sampling("simple", ThematicR, CategoricalR, output_file=output_file)
    sampling.generate_sampling_points(pixel_values, number_of_samples, min_distance,
                                      neighbor_aggregation, attempts_by_sampling,
                                      dockwidget.widget_generate_SimpRS.QPBar_GenerateSampling,
                                      random_seed)

    # zero points
    if sampling.total_of_samples < number_of_samples and sampling.total_of_samples == 0:
        # delete instance where storage all sampling generated
        Sampling.samplings.pop(sampling.filename, None)
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings, "
                                                  "attempts exceeded", level=Qgis.Warning, duration=-1)
        return

    # success
    if sampling.total_of_samples == number_of_samples:
        qgslayer = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Generate the simple random sampling, completed",
                                       level=Qgis.Success)
    # success but not completed
    if number_of_samples > sampling.total_of_samples > 0:
        qgslayer = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Generated the simple random sampling, but can not generate requested number of "
                                                  "random points {}/{}, attempts exceeded".format(sampling.total_of_samples, number_of_samples),
                                       level=Qgis.Warning, duration=-1)
    # check the thematic raster map unit to calculate the minimum distances
    if min_distance > 0:
        if ThematicR.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                "The thematic raster \"{}\" does not have a valid map unit, AcATaMa used \"{}\" as the base unit to "
                "calculate the minimum distances.".format(
                    ThematicR.qgs_layer.name(), QgsUnitTypes.toString(qgslayer.crs().mapUnits())),
                level=Qgis.Warning, duration=-1)


@error_handler
def do_stratified_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.QCBox_ThematicRaster, "thematic raster"):
        return
    if not valid_file_selected_in(dockwidget.QCBox_CategRaster_StraRS, "categorical raster"):
        return
    # get and define some variables
    min_distance = float(dockwidget.minDistance_StraRS.value())
    ThematicR = Raster(file_selected_combo_box=dockwidget.QCBox_ThematicRaster,
                       band=int(dockwidget.QCBox_band_ThematicRaster.currentText()),
                       nodata=int(dockwidget.nodata_ThematicRaster.value()))
    CategoricalR = Raster(file_selected_combo_box=dockwidget.QCBox_CategRaster_StraRS,
                          band=int(dockwidget.QCBox_band_CategRaster_StraRS.currentText()),
                          nodata=int(dockwidget.nodata_CategRaster_StraRS.value()))

    # get values from category table  #########
    pixel_values = []
    number_of_samples = []
    for row in range(dockwidget.QTableW_StraRS.rowCount()):
        pixel_values.append(int(dockwidget.QTableW_StraRS.item(row, 0).text()))
        number_of_samples.append(dockwidget.QTableW_StraRS.item(row, 2).text())
    # convert and check if number of samples only positive integers
    try:
        number_of_samples = [int(ns) for ns in number_of_samples]
        if True in [ns < 0 for ns in number_of_samples]:
            raise Exception
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, the number of samples should be only positive integers",
                                       level=Qgis.Warning)
        return
    total_of_samples = sum(number_of_samples)
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

    # set the attempts_by_sampling
    if dockwidget.widget_generate_StraRS.button_attempts_by_sampling.isChecked():
        attempts_by_sampling = int(dockwidget.widget_generate_StraRS.attempts_by_sampling.value())
    else:
        attempts_by_sampling = None

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

    # first select the target dir for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(ThematicR.file_path), "stratified_random_sampling.gpkg")
    output_file, _ = QFileDialog.getSaveFileName(dockwidget,
                                                 dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if output_file == '':
        return

    # define the random seed
    if dockwidget.widget_generate_StraRS.button_random_seed_by_user.isChecked():
        random_seed = dockwidget.widget_generate_StraRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # process
    sampling = Sampling("stratified", ThematicR, CategoricalR, sampling_method,
                        srs_config=srs_config, output_file=output_file)
    sampling.generate_sampling_points(pixel_values, number_of_samples, min_distance,
                                      neighbor_aggregation, attempts_by_sampling,
                                      dockwidget.widget_generate_StraRS.QPBar_GenerateSampling,
                                      random_seed)

    # zero points
    if sampling.total_of_samples < total_of_samples and sampling.total_of_samples == 0:
        # delete instance where storage all sampling generated
        Sampling.samplings.pop(sampling.filename, None)
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any stratified random points with this settings, "
                                                  "attempts exceeded", level=Qgis.Warning, duration=-1)
        return

    # success
    if sampling.total_of_samples == total_of_samples:
        qgslayer = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Generate the stratified random sampling, completed",
                                       level=Qgis.Success)
    # success but not completed
    if sampling.total_of_samples < total_of_samples and sampling.total_of_samples > 0:
        qgslayer = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Generated the stratified random sampling, but can not generate requested number of "
                                                  "random points {}/{}, attempts exceeded".format(sampling.total_of_samples, total_of_samples),
                                       level=Qgis.Warning, duration=-1)
    # check the thematic raster map unit to calculate the minimum distances
    if min_distance > 0:
        if ThematicR.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                "The thematic raster \"{}\" does not have a valid map unit, AcATaMa used \"{}\" as the base unit to "
                "calculate the minimum distances.".format(
                    ThematicR.qgs_layer.name(), QgsUnitTypes.toString(qgslayer.crs().mapUnits())),
                level=Qgis.Warning, duration=-1)



class Sampling(object):
    # for save all instances
    samplings = dict()  # {name_in_qgis: class instance}

    def __init__(self, sampling_type, ThematicR, CategoricalR, sampling_method=None, srs_config=None, output_file=None):
        # set and init variables
        # sampling_type => "simple" (simple random sampling),
        #                  "stratified" (stratified random sampling)
        self.sampling_type = sampling_type
        self.ThematicR = ThematicR
        self.CategoricalR = CategoricalR
        # for stratified sampling
        self.sampling_method = sampling_method
        # save some stratified sampling configuration
        self.srs_config = srs_config
        # set the output dir for save sampling
        self.output_file = output_file
        # save instance
        self.filename = os.path.splitext(os.path.basename(output_file))[0]  # without extension
        Sampling.samplings[self.filename] = self
        # for save all sampling points
        self.points = dict()

    @wait_process
    def generate_sampling_points(self, pixel_values, number_of_samples, min_distance,
                                 neighbor_aggregation, attempts_by_sampling, progress_bar, random_seed):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/release-2_18/python/plugins/processing/algs/qgis/RandomPointsExtent.py
        """
        self.pixel_values = pixel_values
        self.number_of_samples = number_of_samples  # desired
        self.total_of_samples = None  # total generated
        self.min_distance = min_distance
        self.neighbor_aggregation = neighbor_aggregation
        progress_bar.setValue(0)  # init progress bar

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.ThematicR.extent())

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.ThematicR.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        if self.sampling_type == "simple":
            total_of_samples = self.number_of_samples
        if self.sampling_type == "stratified":
            total_of_samples = sum(self.number_of_samples)
            self.samples_in_categories = [0] * len(self.number_of_samples)  # total generated by categories

        nPoints = 0
        nIterations = 0
        self.index = QgsSpatialIndex()
        if attempts_by_sampling:
            maxIterations = total_of_samples * attempts_by_sampling
        else:
            maxIterations = float('Inf')

        # init the random sampling seed
        self.random_seed = random_seed
        random.seed(self.random_seed)

        points_generated = []
        while nIterations < maxIterations and nPoints < total_of_samples:

            random_sampling_point = RandomPoint(self.ThematicR.extent())

            # checks to the sampling point, else discard and continue
            if not self.check_sampling_point(random_sampling_point):
                nIterations += 1
                continue

            if self.sampling_type == "stratified":
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
        self.total_of_samples = len(points_generated)
        del writer, self.index

    def check_sampling_point(self, sampling_point):
        """Make several checks to the sampling point, else discard
        """
        if not sampling_point.in_valid_data(self.ThematicR):
            return False

        if not sampling_point.in_extent(self.ThematicR_boundaries):
            return False

        if not sampling_point.in_mim_distance(self.index, self.min_distance, self.points):
            return False

        if self.sampling_type == "simple":
            if not sampling_point.in_categorical_raster_SimpRS(self.pixel_values, self.CategoricalR):
                return False
        if self.sampling_type == "stratified":
            if not sampling_point.in_categorical_raster_StraRS(self.pixel_values, self.number_of_samples,
                                                               self.CategoricalR, self.samples_in_categories):
                return False

        if self.neighbor_aggregation and \
                not sampling_point.check_neighbors_aggregation(self.ThematicR, *self.neighbor_aggregation):
            return False

        return True

    def save_config(self, file_out):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        config = configparser.RawConfigParser()

        config.add_section('thematic')
        config.set('thematic', 'thematic_raster', self.ThematicR.file_path)
        config.set('thematic', 'thematic_raster_band', str(self.ThematicR.band))
        config.set('thematic', 'thematic_raster_nodata', str(self.ThematicR.nodata))

        config.add_section('sampling')
        config.set('sampling', 'type', '{} random sampling'.format(self.sampling_type))
        if self.sampling_type == "simple":
            config.add_section('sampling options')
            config.set('sampling options', 'total_of_samples', self.total_of_samples)
            config.set('sampling options', 'min_distance', self.min_distance)

            config.add_section('sampling in categorical raster')
            if isinstance(self.CategoricalR, Raster):
                config.set('sampling in categorical raster', 'categorical_raster', self.CategoricalR.file_path)
                config.set('sampling in categorical raster', 'categorical_raster_band', self.CategoricalR.band)
            else:
                config.set('sampling in categorical raster', 'categorical_raster', 'None')
                config.set('sampling in categorical raster', 'categorical_raster_band', 'None')
            config.set('sampling in categorical raster', 'set_pixel_values',
                       ','.join(map(str, self.pixel_values)) if self.pixel_values is not None else 'None')

        if self.sampling_type == "stratified":
            config.add_section('categorical raster')
            if isinstance(self.CategoricalR, Raster):
                config.set('categorical raster', 'categorical_raster', self.CategoricalR.file_path)
                config.set('categorical raster', 'categorical_raster_band', self.CategoricalR.band)
                config.set('categorical raster', 'categorical_raster_nodata', self.CategoricalR.nodata)
            else:
                config.set('categorical raster', 'categorical_raster', 'None')
                config.set('categorical raster', 'categorical_raster_band', 'None')
                config.set('categorical raster', 'categorical_raster_nodata', 'None')

            config.add_section('stratified random sampling method')
            config.set('stratified random sampling method', 'sampling_method', self.sampling_method)
            if self.sampling_method == "area based proportion":
                config.set('stratified random sampling method', 'total_expected_std_error', self.srs_config["total_std_error"])
            config.set('stratified random sampling method', 'total_of_samples', self.total_of_samples)

            config.add_section('num_samples')
            for pixel, count in zip(self.pixel_values, self.samples_in_categories):
                if count > 0:
                    config.set('num_samples', 'pix_val_'+str(pixel), str(count))

            if self.sampling_method == "area based proportion":
                config.set('stratified random sampling method', 'total_expected_std_error', self.srs_config["total_std_error"])
                config.add_section('std_dev')
                for pixel, count, std_dev in zip(self.pixel_values, self.samples_in_categories, self.srs_config["std_dev"]):
                    if count > 0:
                        config.set('std_dev', 'pix_val_' + str(pixel), str(std_dev))

            config.add_section('sampling options')
            config.set('sampling options', 'min_distance', self.min_distance)

        config.add_section('with neighbors aggregation')
        config.set('with neighbors aggregation', 'min_neighbors_with_the_same_class',
                   '{1}/{0}'.format(
                       *self.neighbor_aggregation) if self.neighbor_aggregation is not None else 'None')

        config.add_section('generation')
        if AcATaMa.dockwidget.widget_generate_SimpRS.button_attempts_by_sampling.isChecked():
            config.set('generation', 'maximum_attempts_by_sampling', AcATaMa.dockwidget.widget_generate_SimpRS.attempts_by_sampling.value())
        else:
            config.set('generation', 'maximum_attempts_by_sampling', "until reaching the set sampling numbers")
        config.set('generation', 'random_seed', self.random_seed if self.random_seed is not None else "automatic")

        with open(file_out, 'w') as configfile:
            config.write(configfile)

