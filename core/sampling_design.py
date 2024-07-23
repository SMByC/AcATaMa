# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2024 by Xavier C. Llano, SMByC
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
import math

from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsSpatialIndex, QgsFeature, Qgis, \
    QgsVectorFileWriter, QgsWkbTypes, QgsUnitTypes, QgsTask, QgsApplication

from AcATaMa.core.point import RandomPoint
from AcATaMa.core.map import Map
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.qgis_utils import load_layer, valid_file_selected_in
from AcATaMa.utils.system_utils import error_handler, output_file_is_OK


def do_simple_random_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # check if the sampling is processing
    if AcATaMa.dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if AcATaMa.dockwidget.QGBox_SimpRSwithCR.isChecked():
        if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_CategMap_SimpRS, "categorical map"):
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option is enabled but not configured",
                                           level=Qgis.Warning, duration=10)
            return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(AcATaMa.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    total_of_samples = int(AcATaMa.dockwidget.numberOfSamples_SimpRS.value())
    min_distance = float(AcATaMa.dockwidget.minDistance_SimpRS.value())

    # simple random sampling in categorical map
    if AcATaMa.dockwidget.QGBox_SimpRSwithCR.isChecked():
        categorical_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_CategMap_SimpRS,
                              band=int(AcATaMa.dockwidget.QCBox_band_CategMap_SimpRS.currentText()))
        try:
            classes_selected = [int(p) for p in AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SimpRS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option is enabled but none of the classes were selected",
                                           level=Qgis.Warning, duration=10)
            return
    else:
        categorical_map = None
        classes_selected = None

    # check neighbors aggregation
    if AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(AcATaMa.dockwidget.widget_generate_SimpRS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path),
                                      "simple {}sampling.gpkg".format("post-stratified " if categorical_map else ""))
    output_file, _ = QFileDialog.getSaveFileName(AcATaMa.dockwidget,
                                                 AcATaMa.dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 AcATaMa.dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if AcATaMa.dockwidget.widget_generate_SimpRS.with_random_seed_by_user.isChecked():
        random_seed = AcATaMa.dockwidget.widget_generate_SimpRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    AcATaMa.dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setText("FINISH")
    AcATaMa.dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setStyleSheet("background-color: red")
    AcATaMa.dockwidget.widget_RandomSampling.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_random_sampling_options.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("simple", thematic_map, categorical_map, output_file=output_file)
    sampling_conf = {"total_of_samples": total_of_samples, "min_distance": min_distance,
                     "classes_selected": classes_selected, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}
    globals()['sampling_task'] = QgsTask.fromFunction(
        "Simple random sampling", sampling.generate_sampling_points,
        on_finished=simple_random_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: AcATaMa.dockwidget.widget_generate_SimpRS.QPBar_GenerateSamples.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def simple_random_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # restoring
    AcATaMa.dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setText("Generate samples")
    AcATaMa.dockwidget.widget_generate_SimpRS.QPBtn_GenerateSamples.setStyleSheet("")
    AcATaMa.dockwidget.widget_RandomSampling.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_neighbour_aggregation.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SimpRS.QGBox_random_sampling_options.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SimpRS.QPBar_GenerateSamples.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sampling_conf["total_of_samples"] and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings",
                                       level=Qgis.Warning, duration=10)
        return

    # success
    if sampling.samples_generated == sampling_conf["total_of_samples"]:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful simple random sampling with {} samples generated"
                                       .format(sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling_conf["total_of_samples"] > sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa",
                                       "Simple random sampling successful, {} random points generated out of a total "
                                       "of {}, sampling process finished".format(
                                           sampling.samples_generated, sampling_conf["total_of_samples"]),
                                       level=Qgis.Info, duration=20)
    # check the thematic map unit to calculate the minimum distances
    if sampling_conf["min_distance"] > 0:
        if sampling.thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                                           "The thematic map \"{}\" does not have a valid map unit, AcATaMa is using "
                                           "\"{}\" as the base unit to calculate the minimum distances.".format(
                                               sampling.thematic_map.qgs_layer.name(),
                                               QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                                           level=Qgis.Warning, duration=20)
    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(0 if sampling.categorical_map is None else 1)

    # open the sampling report
    # TODO


def do_stratified_random_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # check if the sampling is processing
    if AcATaMa.dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_CategMap_StraRS, "categorical map"):
        return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(AcATaMa.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    categorical_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_CategMap_StraRS,
                          band=int(AcATaMa.dockwidget.QCBox_band_CategMap_StraRS.currentText()),
                          nodata=float(AcATaMa.dockwidget.nodata_CategMap_StraRS.text().strip() or "nan"))
    min_distance = float(AcATaMa.dockwidget.minDistance_StraRS.value())

    # get values from category table  #########
    classes_for_sampling = []
    total_of_samples_by_cat = []
    for row in range(AcATaMa.dockwidget.QTableW_StraRS.rowCount()):
        classes_for_sampling.append(int(AcATaMa.dockwidget.QTableW_StraRS.item(row, 0).text()))
        total_of_samples_by_cat.append(AcATaMa.dockwidget.QTableW_StraRS.item(row, 2).text())
    # convert and check if number of samples only positive integers
    try:
        total_of_samples_by_cat = [int(ns) for ns in total_of_samples_by_cat]
        if True in [ns < 0 for ns in total_of_samples_by_cat]:
            raise Exception
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, the number of samples should be only positive integers",
                                       level=Qgis.Warning, duration=10)
        return
    total_of_samples = sum(total_of_samples_by_cat)
    if total_of_samples == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, no number of samples configured!",
                                       level=Qgis.Warning, duration=10)
        return

    # check neighbors aggregation
    if AcATaMa.dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(AcATaMa.dockwidget.widget_generate_StraRS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(AcATaMa.dockwidget.widget_generate_StraRS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the method of stratified sampling and save StraRS config
    if AcATaMa.dockwidget.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        sampling_method = "fixed values"
        srs_config = None
    if AcATaMa.dockwidget.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        sampling_method = "area based proportion"
        srs_config = {}
        # save total expected std error
        srs_config["total_std_error"] = AcATaMa.dockwidget.TotalExpectedSE.value()
        # get ui from table
        srs_config["ui"] = []
        for row in range(AcATaMa.dockwidget.QTableW_StraRS.rowCount()):
            srs_config["ui"].append(float(AcATaMa.dockwidget.QTableW_StraRS.item(row, 3).text()))

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path), "stratified sampling.gpkg")
    output_file, _ = QFileDialog.getSaveFileName(AcATaMa.dockwidget,
                                                 AcATaMa.dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 AcATaMa.dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if AcATaMa.dockwidget.widget_generate_StraRS.with_random_seed_by_user.isChecked():
        random_seed = AcATaMa.dockwidget.widget_generate_StraRS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    AcATaMa.dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setText("FINISH")
    AcATaMa.dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setStyleSheet("background-color: red")
    AcATaMa.dockwidget.widget_StratifiedSampling.setEnabled(False)
    AcATaMa.dockwidget.widget_minDistance_StraRS.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_StraRS.QGBox_random_sampling_options.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("stratified", thematic_map, categorical_map, sampling_method,
                        srs_config=srs_config, output_file=output_file)
    sampling_conf = {"total_of_samples": total_of_samples_by_cat, "min_distance": min_distance,
                     "classes_selected": classes_for_sampling, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}
    globals()['sampling_task'] = QgsTask.fromFunction(
        "Stratified random sampling", sampling.generate_sampling_points,
        on_finished=stratified_random_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: AcATaMa.dockwidget.widget_generate_StraRS.QPBar_GenerateSamples.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def stratified_random_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # restoring
    AcATaMa.dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setText("Generate samples")
    AcATaMa.dockwidget.widget_generate_StraRS.QPBtn_GenerateSamples.setStyleSheet("")
    AcATaMa.dockwidget.widget_StratifiedSampling.setEnabled(True)
    AcATaMa.dockwidget.widget_minDistance_StraRS.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_StraRS.QGBox_neighbour_aggregation.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_StraRS.QGBox_random_sampling_options.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_StraRS.QPBar_GenerateSamples.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sum(sampling_conf["total_of_samples"]) and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any stratified random points with this settings",
                                                  level=Qgis.Warning, duration=10)
        return

    # success
    if sampling.samples_generated == sum(sampling_conf["total_of_samples"]):
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful stratified random sampling with {} samples generated"
                                       .format(sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling.samples_generated < sum(sampling_conf["total_of_samples"]) and sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa",
                                       "Stratified random sampling successful, {} random points generated out of a total "
                                       "of {}, sampling process finished".format(
                                        sampling.samples_generated, sum(sampling_conf["total_of_samples"])),
                                       level=Qgis.Info, duration=20)
    # check the thematic map unit to calculate the minimum distances
    if sampling_conf["min_distance"] > 0:
        if sampling.thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            iface.messageBar().pushMessage("AcATaMa",
                                           "The thematic map \"{}\" does not have a valid map unit, AcATaMa is using "
                                           "\"{}\" as the base unit to calculate the minimum distances.".format(
                                                sampling.thematic_map.qgs_layer.name(),
                                                QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                                           level=Qgis.Warning, duration=20)
    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(2)

    # open the sampling report
    # TODO


def do_systematic_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # check if the sampling is processing
    if AcATaMa.dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if AcATaMa.dockwidget.QGBox_SystSwithCR.isChecked():
        if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_CategMap_SystS, "categorical map"):
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option enabled but not configured",
                                           level=Qgis.Warning, duration=10)
            return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=float(AcATaMa.dockwidget.nodata_ThematicMap.text().strip() or "nan"))
    points_spacing = float(AcATaMa.dockwidget.PointsSpacing_SystS.value())
    max_xy_offset = float(AcATaMa.dockwidget.MaxXYoffset_SystS.value())
    total_of_samples = AcATaMa.dockwidget.widget_generate_SystS.QPBar_GenerateSamples.maximum()

    # systematic sampling in categorical map
    if AcATaMa.dockwidget.QGBox_SystSwithCR.isChecked():
        categorical_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_CategMap_SystS,
                              band=int(AcATaMa.dockwidget.QCBox_band_CategMap_SystS.currentText()))
        try:
            classes_selected = [int(p) for p in AcATaMa.dockwidget.QPBtn_CategMapClassesSelection_SystS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, post-stratify option is enabled but none of the classes were selected",
                                           level=Qgis.Warning, duration=10)
            return
    else:
        categorical_map = None
        classes_selected = None

    # check neighbors aggregation
    if AcATaMa.dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.isChecked():
        number_of_neighbors = int(AcATaMa.dockwidget.widget_generate_SystS.QCBox_NumberOfNeighbors.currentText())
        same_class_of_neighbors = int(AcATaMa.dockwidget.widget_generate_SystS.QCBox_SameClassOfNeighbors.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = os.path.join(os.path.dirname(thematic_map.file_path),
                                      "systematic {}sampling.gpkg".format("post-stratified " if categorical_map else ""))
    output_file, _ = QFileDialog.getSaveFileName(AcATaMa.dockwidget,
                                                 AcATaMa.dockwidget.tr("Select the output file to save the sampling"),
                                                 suggested_filename,
                                                 AcATaMa.dockwidget.tr("GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"))
    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if AcATaMa.dockwidget.widget_generate_SystS.with_random_seed_by_user.isChecked():
        random_seed = AcATaMa.dockwidget.widget_generate_SystS.random_seed_by_user.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # define the initial inset
    if AcATaMa.dockwidget.QCBox_InitialInsetMode_SystS.currentText() == "Random":
        random.seed(random_seed)
        initial_inset = random.uniform(0, points_spacing)
    else:
        initial_inset = float(AcATaMa.dockwidget.InitialInsetFixed_SystS.value())

    # before process
    AcATaMa.dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setText("FINISH")
    AcATaMa.dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setStyleSheet("background-color: red")
    AcATaMa.dockwidget.widget_SystS_step1.setEnabled(False)
    AcATaMa.dockwidget.widget_SystS_step2.setEnabled(False)
    AcATaMa.dockwidget.QGBox_SystSwithCR.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.setEnabled(False)
    AcATaMa.dockwidget.widget_generate_SystS.QGBox_random_sampling_options.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("systematic", thematic_map, categorical_map, "grid with random offset",
                        output_file=output_file)
    sampling_conf = {"total_of_samples": total_of_samples, "points_spacing": points_spacing,
                     "initial_inset": initial_inset, "max_xy_offset": max_xy_offset,
                     "classes_selected": classes_selected, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}
    globals()['sampling_task'] = QgsTask.fromFunction(
        "Systematic sampling", sampling.generate_systematic_sampling_points,
        on_finished=systematic_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: AcATaMa.dockwidget.widget_generate_SystS.QPBar_GenerateSamples.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def systematic_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

    # restoring
    AcATaMa.dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setText("Generate samples")
    AcATaMa.dockwidget.widget_generate_SystS.QPBtn_GenerateSamples.setStyleSheet("")
    AcATaMa.dockwidget.widget_SystS_step1.setEnabled(True)
    AcATaMa.dockwidget.widget_SystS_step2.setEnabled(True)
    AcATaMa.dockwidget.QGBox_SystSwithCR.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SystS.QGBox_neighbour_aggregation.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SystS.QGBox_random_sampling_options.setEnabled(True)
    AcATaMa.dockwidget.widget_generate_SystS.QPBar_GenerateSamples.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sampling_conf["total_of_samples"] and sampling.samples_generated == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings",
                                       level=Qgis.Warning, duration=10)
        return

    # success
    if sampling.samples_generated == sampling_conf["total_of_samples"]:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa", "Successful systematic sampling with {} samples generated".format(
                                        sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling_conf["total_of_samples"] > sampling.samples_generated > 0:
        sampling_layer_generated = load_layer(sampling.output_file)
        iface.messageBar().pushMessage("AcATaMa",
                                       "Systematic random sampling successful, {} random points generated out of a total "
                                       "of {}, sampling process finished".format(
                                        sampling.samples_generated, sampling_conf["total_of_samples"]),
                                       level=Qgis.Success, duration=20)

    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingFile_A.setLayer(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator_A.setCurrentIndex(0 if sampling.categorical_map is None else 1)

    # open the sampling report
    # TODO


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

    def generate_sampling_points(self, task, sampling_conf):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/release-2_18/python/plugins/processing/algs/qgis/RandomPointsExtent.py
        """
        self.total_of_samples = sampling_conf["total_of_samples"]  # desired
        self.samples_generated = None  # total generated
        self.min_distance = sampling_conf["min_distance"]
        self.classes_for_sampling = sampling_conf["classes_selected"]
        self.neighbor_aggregation = sampling_conf["neighbor_aggregation"]

        if self.sampling_design_type == "simple":
            total_of_samples = self.total_of_samples
        if self.sampling_design_type == "stratified":
            total_of_samples = sum(self.total_of_samples)
            self.samples_in_categories = [0] * len(self.total_of_samples)  # total generated by categories

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        self.index = QgsSpatialIndex()

        # init the random sampling seed
        self.random_seed = sampling_conf["random_seed"]
        random.seed(self.random_seed)

        points_generated = []
        while not task.isCanceled() and len(points_generated) < total_of_samples:

            random_sampling_point = RandomPoint.fromExtent(self.thematic_map.extent())

            # checks to the sampling point, else discard and continue
            if not self.check_sampling_point(random_sampling_point):
                continue

            if self.sampling_design_type == "stratified":
                self.samples_in_categories[random_sampling_point.index_pixel_value] += 1

            # it requires tmp save the point to check min distance for the next sample
            f = QgsFeature(len(points_generated))
            f.setGeometry(random_sampling_point.QgsGeom)
            self.index.insertFeature(f)
            self.points[len(points_generated)] = random_sampling_point.QgsPnt

            points_generated.append(random_sampling_point)
            # update task progress
            task.setProgress(len(points_generated)/total_of_samples*100)

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

        return self, sampling_conf

    def generate_systematic_sampling_points(self, task, sampling_conf):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/master/python/plugins/processing/algs/qgis/RegularPoints.py
        """
        self.points_spacing = sampling_conf["points_spacing"]
        self.initial_inset = sampling_conf["initial_inset"]
        self.max_xy_offset = sampling_conf["max_xy_offset"]
        self.classes_for_sampling = sampling_conf["classes_selected"]
        self.neighbor_aggregation = sampling_conf["neighbor_aggregation"]
        self.samples_generated = None  # total generated
        self.random_seed = sampling_conf["random_seed"]

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        # add an epsilon to accept sampling points on the edge of the map
        epsilon = 0.00001
        initial_inset = self.initial_inset + epsilon

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        y = self.thematic_map.extent().yMaximum() - initial_inset
        extent_geom = QgsGeometry.fromRect(self.thematic_map.extent())
        extent_engine = QgsGeometry.createGeometryEngine(extent_geom.constGet())
        extent_engine.prepareGeometry()

        # init the random sampling seed
        random.seed(self.random_seed)

        points_generated = []
        while y >= self.thematic_map.extent().yMinimum():
            x = self.thematic_map.extent().xMinimum() + initial_inset
            while x <= self.thematic_map.extent().xMaximum():
                attempts = 0
                while not task.isCanceled():
                    if attempts == 1000:
                        x += self.points_spacing
                        break
                    if self.max_xy_offset > 0:
                        # step 2: random offset
                        rx = random.uniform(x - self.max_xy_offset, x + self.max_xy_offset)
                        ry = random.uniform(y - self.max_xy_offset, y + self.max_xy_offset)
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

                    x += self.points_spacing
                    # update task progress
                    task.setProgress(len(points_generated)/sampling_conf["total_of_samples"]*100)
                    break

            y = y - self.points_spacing

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

        return self, sampling_conf

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
