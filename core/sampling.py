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
import os
import ConfigParser
from datetime import datetime

from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsRectangle, QgsSpatialIndex, \
    QgsFeature, QGis
from processing.tools import vector

from AcATaMa.core.point import RandomPoint
from AcATaMa.core.raster import Raster
from AcATaMa.core.dockwidget import load_layer_in_qgis, valid_file_selected_in
from AcATaMa.core.utils import wait_process, error_handler


@error_handler()
@wait_process('widget_generate_RS.buttonGenerateSampling')
def do_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.selectThematicRaster, "thematic raster"):
        return
    if dockwidget.groupBox_RSwithCR.isChecked():
        if not valid_file_selected_in(dockwidget.selectCategRaster_RS, "categorical raster"):
            return
    # get and define some variables
    number_of_samples = int(dockwidget.numberOfSamples_RS.value())
    min_distance = int(dockwidget.minDistance_RS.value())

    ThematicR = Raster(file_selected_combo_box=dockwidget.selectThematicRaster,
                       nodata=int(dockwidget.nodata_ThematicRaster.value()))

    # random sampling in categorical raster
    if dockwidget.groupBox_RSwithCR.isChecked():
        CategoricalR = Raster(file_selected_combo_box=dockwidget.selectCategRaster_RS)
        try:
            pixel_values = [int(p) for p in dockwidget.pixelsValuesCategRaster.text().split(",")]
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, wrong pixel values, set only integers and separated by commas",
                                           level=QgsMessageBar.WARNING)
            return
    else:
        CategoricalR = None
        pixel_values = None

    # check neighbors aggregation
    if dockwidget.widget_generate_RS.groupBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_RS.number_of_neighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_RS.same_class_of_neighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the attempts_by_sampling
    if dockwidget.widget_generate_RS.button_attempts_by_sampling.isChecked():
        attempts_by_sampling = int(dockwidget.widget_generate_RS.attempts_by_sampling.value())
    else:
        attempts_by_sampling = None

    # process
    sampling = Sampling("RS", ThematicR, CategoricalR, out_dir=dockwidget.tmp_dir)
    sampling.generate_sampling_points(pixel_values, number_of_samples, min_distance,
                                      neighbor_aggregation, attempts_by_sampling,
                                      dockwidget.widget_generate_RS.progressGenerateSampling)

    # success
    if sampling.total_of_samples == number_of_samples:
        load_layer_in_qgis(sampling.output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generate the random sampling, completed",
                                       level=QgsMessageBar.SUCCESS)
    # success but not completed
    if sampling.total_of_samples < number_of_samples and sampling.total_of_samples > 0:
        load_layer_in_qgis(sampling.output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generated the random sampling, but can not generate requested number of "
                                                  "random points {}/{}, attempts exceeded".format(sampling.total_of_samples, number_of_samples),
                                       level=QgsMessageBar.INFO, duration=10)
    # zero points
    if sampling.total_of_samples < number_of_samples and sampling.total_of_samples == 0:
        # delete instance where storage all sampling generated
        Sampling.samplings.pop(sampling.sampling_name, None)
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings, "
                                                  "attempts exceeded", level=QgsMessageBar.WARNING, duration=10)


@error_handler()
@wait_process('widget_generate_SRS.buttonGenerateSampling')
def do_stratified_random_sampling(dockwidget):
    # first check input files requirements
    if not valid_file_selected_in(dockwidget.selectThematicRaster, "thematic raster"):
        return
    if not valid_file_selected_in(dockwidget.selectCategRaster_SRS, "categorical raster"):
        return
    # get and define some variables
    min_distance = int(dockwidget.minDistance_SRS.value())
    ThematicR = Raster(file_selected_combo_box=dockwidget.selectThematicRaster,
                       nodata=int(dockwidget.nodata_ThematicRaster.value()))
    CategoricalR = Raster(file_selected_combo_box=dockwidget.selectCategRaster_SRS,
                          nodata=int(dockwidget.nodata_CategRaster_SRS.value()))

    # get values from category table  #########
    pixel_values = []
    number_of_samples = []
    for row in range(dockwidget.TableWidget_SRS.rowCount()):
        pixel_values.append(int(dockwidget.TableWidget_SRS.item(row, 0).text()))
        number_of_samples.append(dockwidget.TableWidget_SRS.item(row, 2).text())
    # convert and check if number of samples only positive integers
    try:
        number_of_samples = [int(ns) for ns in number_of_samples]
        if True in [ns < 0 for ns in number_of_samples]:
            raise
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, the number of samples should be only positive integers",
                                       level=QgsMessageBar.WARNING)
        return
    total_of_samples = sum(number_of_samples)
    if total_of_samples == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, no number of samples configured!",
                                       level=QgsMessageBar.WARNING)
        return

    # check neighbors aggregation
    if dockwidget.widget_generate_SRS.groupBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(dockwidget.widget_generate_SRS.number_of_neighbors.currentText())
        same_class_of_neighbors = int(dockwidget.widget_generate_SRS.same_class_of_neighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the attempts_by_sampling
    if dockwidget.widget_generate_SRS.button_attempts_by_sampling.isChecked():
        attempts_by_sampling = int(dockwidget.widget_generate_SRS.attempts_by_sampling.value())
    else:
        attempts_by_sampling = None

    # set the method of stratified sampling and save SRS config
    if dockwidget.StratifieSamplingMethod.currentText().startswith("Fixed values"):
        sampling_method = "fixed values"
        srs_config = None
    if dockwidget.StratifieSamplingMethod.currentText().startswith("Area based proportion"):
        sampling_method = "area based proportion"
        srs_config = {}
        # save total expected std error
        srs_config["total_std_error"] = dockwidget.TotalExpectedSE.value()
        # get std_error from table
        srs_config["std_error"] = []
        for row in range(dockwidget.TableWidget_SRS.rowCount()):
            srs_config["std_error"].append(float(dockwidget.TableWidget_SRS.item(row, 3).text()))

    # process
    sampling = Sampling("SRS", ThematicR, CategoricalR, sampling_method,
                        srs_config=srs_config, out_dir=dockwidget.tmp_dir)
    sampling.generate_sampling_points(pixel_values, number_of_samples, min_distance,
                                      neighbor_aggregation, attempts_by_sampling,
                                      dockwidget.widget_generate_SRS.progressGenerateSampling)

    # success
    if sampling.total_of_samples == total_of_samples:
        load_layer_in_qgis(sampling.output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generate the stratified random sampling, completed",
                                       level=QgsMessageBar.SUCCESS)
    # success but not completed
    if sampling.total_of_samples < total_of_samples and sampling.total_of_samples > 0:
        load_layer_in_qgis(sampling.output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generated the stratified random sampling, but can not generate requested number of "
                                                  "random points {}/{}, attempts exceeded".format(sampling.total_of_samples, total_of_samples),
                                       level=QgsMessageBar.INFO, duration=10)
    # zero points
    if sampling.total_of_samples < total_of_samples and sampling.total_of_samples == 0:
        # delete instance where storage all sampling generated
        Sampling.samplings.pop(sampling.sampling_name, None)
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any stratified random points with this settings, "
                                                  "attempts exceeded", level=QgsMessageBar.WARNING, duration=10)


class Sampling:
    # for save all instances
    samplings = dict()  # {name_in_qgis: class instance}

    def __init__(self, sampling_type, ThematicR, CategoricalR, sampling_method=None, srs_config=None, out_dir=None):
        # set and init variables
        # sampling_type => "RS" (random sampling),
        #                  "SRS" (stratified random sampling)
        self.sampling_type = sampling_type
        self.ThematicR = ThematicR
        self.CategoricalR = CategoricalR
        # set the name and output file
        if self.sampling_type == "RS":
            self.sampling_name = "random_sampling_{}".format(datetime.now().strftime('%H-%M-%S'))
        if self.sampling_type == "SRS":
            self.sampling_name = "stratified_random_sampling_{}".format(datetime.now().strftime('%H-%M-%S'))
        # for stratified sampling
        self.sampling_method = sampling_method
        # save some SRS sampling configuration
        self.srs_config = srs_config
        # set the output dir for save sampling
        if out_dir is None:
            out_dir = os.path.dirname(ThematicR.file_path)
        self.output_file = os.path.join(out_dir, self.sampling_name)
        # save instance
        Sampling.samplings[self.sampling_name] = self
        # for save all sampling points
        self.points = dict()

    def generate_sampling_points(self, pixel_values, number_of_samples, min_distance,
                                 neighbor_aggregation, attempts_by_sampling, progress_bar):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/release-2_18/python/plugins/processing/algs/qgis/RandomPointsExtent.py
        """
        self.pixel_values = pixel_values
        self.number_of_samples = number_of_samples  # desired
        self.total_of_samples = None  # total generated
        self.min_distance = min_distance
        self.neighbor_aggregation = neighbor_aggregation
        progress_bar.setValue(0)  # init progress bar

        xMin, yMax, xMax, yMin = self.ThematicR.extent()
        self.ThematicR_boundaries = QgsGeometry().fromRect(QgsRectangle(xMin, yMin, xMax, yMax))

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        mapCRS = iface.mapCanvas().mapSettings().destinationCrs()
        writer = vector.VectorWriter(self.output_file, None, fields, QGis.WKBPoint, mapCRS)

        if self.sampling_type == "RS":
            total_of_samples = self.number_of_samples
        if self.sampling_type == "SRS":
            total_of_samples = sum(self.number_of_samples)
            self.samples_in_categories = [0] * len(self.number_of_samples)  # total generated by categories

        nPoints = 0
        nIterations = 0
        self.index = QgsSpatialIndex()
        if attempts_by_sampling:
            maxIterations = total_of_samples * attempts_by_sampling
        else:
            maxIterations = float('Inf')

        while nIterations < maxIterations and nPoints < total_of_samples:

            random_sampling_point = RandomPoint(xMin, yMax, xMax, yMin)

            # checks to the sampling point, else discard and continue
            if not self.check_sampling_point(random_sampling_point):
                nIterations += 1
                continue

            # random sampling point passed the checks, save it
            f = QgsFeature(nPoints)
            f.initAttributes(1)
            f.setFields(fields)
            f.setAttribute('id', nPoints)
            f.setGeometry(random_sampling_point.QgsGeom)
            writer.addFeature(f)
            self.index.insertFeature(f)
            self.points[nPoints] = random_sampling_point.QgsPnt
            nPoints += 1
            nIterations += 1
            if self.sampling_type == "SRS":
                self.samples_in_categories[random_sampling_point.index_pixel_value] += 1
            # update progress bar
            progress_bar.setValue(int(nPoints))
        # save the total point generated
        self.total_of_samples = nPoints
        del writer

    def check_sampling_point(self, sampling_point):
        """Make several checks to the sampling point, else discard
        """
        if not sampling_point.in_valid_data(self.ThematicR):
            return False

        if not sampling_point.in_extent(self.ThematicR_boundaries):
            return False

        if not sampling_point.in_mim_distance(self.index, self.min_distance, self.points):
            return False

        if self.sampling_type == "RS":
            if not sampling_point.in_categorical_raster(self.pixel_values, self.CategoricalR):
                return False
        if self.sampling_type == "SRS":
            if not sampling_point.in_stratified_raster(self.pixel_values, self.number_of_samples,
                                                       self.CategoricalR, self.samples_in_categories):
                return False

        if self.neighbor_aggregation and \
                not sampling_point.check_neighbors_aggregation(self.ThematicR, *self.neighbor_aggregation):
            return False

        return True

    def save_config(self, file_out):
        config = ConfigParser.RawConfigParser()

        config.add_section('general')
        if self.sampling_type == "RS":
            config.set('general', 'sampling_type', 'random sampling')
        if self.sampling_type == "SRS":
            config.set('general', 'sampling_type', 'stratified random sampling')
        config.set('general', 'thematic_raster', self.ThematicR.file_path)
        config.set('general', 'thematic_raster_nodata', str(self.ThematicR.nodata))
        if isinstance(self.CategoricalR, Raster):
            config.set('general', 'categorical_raster', self.CategoricalR.file_path)
            config.set('general', 'categorical_raster_nodata', self.CategoricalR.nodata)
        else:
            config.set('general', 'categorical_raster', 'None')
            config.set('general', 'categorical_raster_nodata', 'None')

        config.add_section('sampling')
        if self.sampling_type == "RS":
            config.set('sampling', 'total_of_samples', self.total_of_samples)
            config.set('sampling', 'min_distance', self.min_distance)
            config.set('sampling', 'in_categorical_raster',
                       ','.join(map(str, self.pixel_values)) if self.pixel_values is not None else 'None')
            config.set('sampling', 'with_neighbors_aggregation',
                       '{1}/{0}'.format(*self.neighbor_aggregation) if self.neighbor_aggregation is not None else 'None')
        if self.sampling_type == "SRS":
            config.set('sampling', 'sampling_method', self.sampling_method)
            config.set('sampling', 'total_of_samples', self.total_of_samples)
            config.set('sampling', 'min_distance', self.min_distance)
            config.set('sampling', 'with_neighbors_aggregation',
                       '{1}/{0}'.format(
                           *self.neighbor_aggregation) if self.neighbor_aggregation is not None else 'None')

            config.add_section('num_samples')
            for pixel, count in zip(self.pixel_values, self.samples_in_categories):
                if count > 0:
                    config.set('num_samples', 'pix_val_'+str(pixel), str(count))

            if self.sampling_method == "area based proportion":
                config.set('sampling', 'total_expected_std_error', self.srs_config["total_std_error"])
                config.add_section('std_error')
                for pixel, count, std_error in zip(self.pixel_values, self.samples_in_categories, self.srs_config["std_error"]):
                    if count > 0:
                        config.set('std_error', 'pix_val_' + str(pixel), str(std_error))

        with open(file_out, 'wb') as configfile:
            config.write(configfile)

