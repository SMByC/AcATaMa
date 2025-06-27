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

import numpy as np
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsSpatialIndex, QgsFeature, Qgis, \
    QgsVectorFileWriter, QgsWkbTypes, QgsUnitTypes, QgsTask, QgsApplication

from AcATaMa.core.point import RandomPoint
from AcATaMa.core.map import Map
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.utils.qgis_utils import load_layer, valid_file_selected_in, get_file_path_of_layer
from AcATaMa.utils.system_utils import error_handler, output_file_is_OK, get_save_file_name
from AcATaMa.gui.sampling_report import SamplingReport
from AcATaMa.utils.others_utils import get_nodata_format, get_epsilon


def do_simple_random_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # check if the sampling is processing
    if sampling_design.QPBtn_GenerateSamples_SimpRS.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if sampling_design.QGBox_SimpRSwithPS.isChecked():
        if not valid_file_selected_in(sampling_design.QCBox_PostStratMap_SimpRS, "post-stratification map"):
            sampling_design.MsgBar.pushMessage("Error, post-stratification option is enabled but not configured",
                                               level=Qgis.Warning, duration=10)
            return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()))
    total_of_samples = int(sampling_design.numberOfSamples_SimpRS.value())
    min_distance = float(sampling_design.minDistance_SimpRS.value())

    # post-stratification of the simple random sampling
    if sampling_design.QGBox_SimpRSwithPS.isChecked():
        post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_PostStratMap_SimpRS,
                                      band=int(sampling_design.QCBox_band_PostStratMap_SimpRS.currentText()),
                                      nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SimpRS.text()))
        try:
            classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SimpRS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            sampling_design.MsgBar.pushMessage("Error, post-stratification option is enabled but none of the classes were selected",
                                               level=Qgis.Warning, duration=10)
            return
    else:
        post_stratification_map = None
        classes_selected = None

    # check neighbors aggregation
    if sampling_design.QGBox_neighbour_aggregation_SimpRS.isChecked():
        number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SimpRS.currentText())
        same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SimpRS.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = get_file_path_of_layer(AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()) or \
                         os.path.join(os.path.dirname(thematic_map.file_path), "simple {}sampling.gpkg"
                                      .format("post-stratified " if post_stratification_map else ""))

    output_file = get_save_file_name(
        sampling_design,
        "Select the output file to save the sampling",
        suggested_filename,
        "GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"
    )

    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if sampling_design.QGBox_random_sampling_options_SimpRS.isChecked() and sampling_design.with_random_seed_by_user_SimpRS.isChecked():
        random_seed = sampling_design.random_seed_by_user_SimpRS.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    sampling_design.QPBtn_GenerateSamples_SimpRS.setText("FINISH")
    sampling_design.QPBtn_GenerateSamples_SimpRS.setStyleSheet("background-color: red")
    sampling_design.widget_RandomSampling.setEnabled(False)
    sampling_design.QGBox_neighbour_aggregation_SimpRS.setEnabled(False)
    sampling_design.QGBox_random_sampling_options_SimpRS.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("simple", thematic_map, post_stratification_map=post_stratification_map, output_file=output_file)
    sampling_conf = {"sampling_type": "simple", "total_of_samples": total_of_samples, "min_distance": min_distance,
                     "classes_selected": classes_selected, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}
    globals()['sampling_task'] = QgsTask.fromFunction(
        "Simple random sampling", sampling.generate_sampling_points,
        on_finished=simple_random_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: sampling_design.QPBar_GenerateSamples_SimpRS.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def simple_random_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # restoring
    sampling_design.QPBtn_GenerateSamples_SimpRS.setText("Generate samples")
    sampling_design.QPBtn_GenerateSamples_SimpRS.setStyleSheet("")
    sampling_design.widget_RandomSampling.setEnabled(True)
    sampling_design.QGBox_neighbour_aggregation_SimpRS.setEnabled(True)
    sampling_design.QGBox_random_sampling_options_SimpRS.setEnabled(True)
    sampling_design.QPBar_GenerateSamples_SimpRS.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sampling_conf["total_of_samples"] and sampling.samples_generated == 0:
        sampling_design.MsgBar.pushMessage("Error, could not generate any random points with this settings",
                                           level=Qgis.Warning, duration=10)
        return

    sampling_layer_generated = load_layer(sampling.output_file)

    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(0 if sampling.post_stratification_map is None else 1)

    ### sampling report
    sampling_report = SamplingReport(sampling_layer_generated, sampling, sampling_conf)
    sampling_report.show()
    AcATaMa.dockwidget.QPBtn_openSamplingReport.setEnabled(True)

    # success
    if sampling.samples_generated == sampling_conf["total_of_samples"]:
        sampling_report.MsgBar.pushMessage("Simple random sampling successful: {} samples generated"
                                           .format(sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling_conf["total_of_samples"] > sampling.samples_generated > 0:
        sampling_report.MsgBar.pushMessage("Simple random sampling successful: {} samples generated from {}".format(
                                           sampling.samples_generated, sampling_conf["total_of_samples"]),
                                           level=Qgis.Info, duration=20)
    # check the thematic map unit to calculate the minimum distances
    if sampling_conf["min_distance"] > 0:
        if sampling.thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            sampling_report.MsgBar.pushMessage("The thematic map \"{}\" does not have a valid map unit, AcATaMa is using "
                                               "\"{}\" as the base unit to calculate the minimum distances".format(
                                               sampling.thematic_map.qgs_layer.name(),
                                               QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                                               level=Qgis.Warning, duration=20)


def do_stratified_random_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # check if the sampling is processing
    if sampling_design.QPBtn_GenerateSamples_StraRS.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if not valid_file_selected_in(sampling_design.QCBox_SamplingMap_StraRS, "sampling map"):
        return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text().strip()))
    sampling_map = Map(file_selected_combo_box=sampling_design.QCBox_SamplingMap_StraRS,
                       band=int(sampling_design.QCBox_band_SamplingMap_StraRS.currentText()),
                       nodata=get_nodata_format(sampling_design.nodata_SamplingMap_StraRS.text()))
    min_distance = float(sampling_design.minDistance_StraRS.value())

    # get values from category table  #########
    classes_for_sampling = []
    total_of_samples_by_stratum = []
    for row in range(sampling_design.QTableW_StraRS.rowCount()):
        classes_for_sampling.append(int(sampling_design.QTableW_StraRS.item(row, 0).text()))
        total_of_samples_by_stratum.append(sampling_design.QTableW_StraRS.item(row, 2).text())
    # convert and check if number of samples only positive integers
    try:
        total_of_samples_by_stratum = [int(ns) for ns in total_of_samples_by_stratum]
        if True in [ns < 0 for ns in total_of_samples_by_stratum]:
            raise Exception
    except:
        sampling_design.MsgBar.pushMessage("Error, the number of samples should be only positive integers",
                                           level=Qgis.Warning, duration=10)
        return
    total_of_samples = sum(total_of_samples_by_stratum)
    if total_of_samples == 0:
        sampling_design.MsgBar.pushMessage("Error, no number of samples configured!",
                                           level=Qgis.Warning, duration=10)
        return

    # check neighbors aggregation
    if sampling_design.QGBox_neighbour_aggregation_StraRS.isChecked():
        number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_StraRS.currentText())
        same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_StraRS.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # set the method of stratified sampling and save StraRS config
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Fixed values"):
        sampling_method = "fixed values"
        srs_config = None
    if sampling_design.QCBox_StraRS_Method.currentText().startswith("Area based proportion"):
        sampling_method = "area based proportion"
        srs_config = {}
        # save total expected std error
        srs_config["total_std_error"] = sampling_design.TotalExpectedSE.value()
        # get ui from table
        srs_config["ui"] = []
        for row in range(sampling_design.QTableW_StraRS.rowCount()):
            srs_config["ui"].append(float(sampling_design.QTableW_StraRS.item(row, 3).text()))

    # first select the target file for save the sampling file
    suggested_filename = get_file_path_of_layer(AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()) or \
                         os.path.join(os.path.dirname(thematic_map.file_path), "stratified sampling.gpkg")

    output_file = get_save_file_name(
        sampling_design,
        "Select the output file to save the sampling",
        suggested_filename,
        "GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"
    )

    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if sampling_design.QGBox_random_sampling_options_StraRS.isChecked() and sampling_design.with_random_seed_by_user_StraRS.isChecked():
        random_seed = sampling_design.random_seed_by_user_StraRS.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # before process
    sampling_design.QPBtn_GenerateSamples_StraRS.setText("FINISH")
    sampling_design.QPBtn_GenerateSamples_StraRS.setStyleSheet("background-color: red")
    sampling_design.widget_StratifiedSampling.setEnabled(False)
    sampling_design.widget_minDistance_StraRS.setEnabled(False)
    sampling_design.QGBox_neighbour_aggregation_StraRS.setEnabled(False)
    sampling_design.QGBox_random_sampling_options_StraRS.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("stratified", thematic_map, sampling_map=sampling_map,
                        sampling_method=sampling_method, srs_config=srs_config, output_file=output_file)
    sampling_conf = {"sampling_type": "stratified", "total_of_samples": total_of_samples_by_stratum, "min_distance": min_distance,
                     "classes_selected": classes_for_sampling, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}
    globals()['sampling_task'] = QgsTask.fromFunction(
        "Stratified random sampling", sampling.generate_sampling_points,
        on_finished=stratified_random_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: sampling_design.QPBar_GenerateSamples_StraRS.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def stratified_random_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # restoring
    sampling_design.QPBtn_GenerateSamples_StraRS.setText("Generate samples")
    sampling_design.QPBtn_GenerateSamples_StraRS.setStyleSheet("")
    sampling_design.widget_StratifiedSampling.setEnabled(True)
    sampling_design.widget_minDistance_StraRS.setEnabled(True)
    sampling_design.QGBox_neighbour_aggregation_StraRS.setEnabled(True)
    sampling_design.QGBox_random_sampling_options_StraRS.setEnabled(True)
    sampling_design.QPBar_GenerateSamples_StraRS.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sum(sampling_conf["total_of_samples"]) and sampling.samples_generated == 0:
        sampling_design.MsgBar.pushMessage("Error, could not generate any stratified random points with this settings",
                                           level=Qgis.Warning, duration=10)
        return

    sampling_layer_generated = load_layer(sampling.output_file)

    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(2)

    ### sampling report
    sampling_report = SamplingReport(sampling_layer_generated, sampling, sampling_conf)
    sampling_report.show()
    AcATaMa.dockwidget.QPBtn_openSamplingReport.setEnabled(True)

    # success
    if sampling.samples_generated == sum(sampling_conf["total_of_samples"]):
        sampling_report.MsgBar.pushMessage("Stratified random sampling successful: {} samples generated"
                                           .format(sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling.samples_generated < sum(sampling_conf["total_of_samples"]) and sampling.samples_generated > 0:
        sampling_report.MsgBar.pushMessage("Stratified random sampling successful: {} samples generated from {}".format(
                                           sampling.samples_generated, sum(sampling_conf["total_of_samples"])),
                                           level=Qgis.Info, duration=20)
    # check the thematic map unit to calculate the minimum distances
    if sampling_conf["min_distance"] > 0:
        if sampling.thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
            sampling_report.MsgBar.pushMessage("The thematic map \"{}\" does not have a valid map unit, AcATaMa is using "
                                               "\"{}\" as the base unit to calculate the minimum distances".format(
                                               sampling.thematic_map.qgs_layer.name(),
                                                QgsUnitTypes.toString(sampling_layer_generated.crs().mapUnits())),
                                               level=Qgis.Warning, duration=20)


def do_systematic_sampling():
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # check if the sampling is processing
    if sampling_design.QPBtn_GenerateSamples_SystS.text() == "FINISH":
        globals()['sampling_task'].cancel()
        return

    # first check input files requirements
    if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap, "thematic map"):
        return
    if sampling_design.QGBox_SystSwithPS.isChecked():
        if not valid_file_selected_in(sampling_design.QCBox_PostStratMap_SystS, "post-stratification map"):
            sampling_design.MsgBar.pushMessage("Error, post-stratification option enabled but not configured",
                                               level=Qgis.Warning, duration=10)
            return

    # get and define some variables
    thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                       band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText()),
                       nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()))
    points_spacing = float(sampling_design.PointSpacing_SystS.value())
    max_xy_offset = float(sampling_design.MaxXYoffset_SystS.value())
    total_of_samples = sampling_design.QPBar_GenerateSamples_SystS.maximum()
    systematic_sampling_unit = sampling_design.QCBox_Systematic_Sampling_Unit.currentText()

    # post-stratification of the systematic sampling
    if sampling_design.QGBox_SystSwithPS.isChecked():
        post_stratification_map = Map(file_selected_combo_box=sampling_design.QCBox_PostStratMap_SystS,
                                      band=int(sampling_design.QCBox_band_PostStratMap_SystS.currentText()),
                                      nodata=get_nodata_format(sampling_design.nodata_PostStratMap_SystS.text()))
        try:
            classes_selected = [int(p) for p in sampling_design.QPBtn_PostStratMapClasses_SystS.text().split(",")]
            if not classes_selected:
                raise Exception
        except:
            sampling_design.MsgBar.pushMessage("Error, post-stratification option is enabled but none of the classes were selected",
                                               level=Qgis.Warning, duration=10)
            return
    else:
        post_stratification_map = None
        classes_selected = None

    # check neighbors aggregation
    if sampling_design.QGBox_neighbour_aggregation_SystS.isChecked():
        number_of_neighbors = int(sampling_design.QCBox_NumberOfNeighbors_SystS.currentText())
        same_class_of_neighbors = int(sampling_design.QCBox_SameClassOfNeighbors_SystS.currentText())
        neighbor_aggregation = (number_of_neighbors, same_class_of_neighbors)
    else:
        neighbor_aggregation = None

    # first select the target file for save the sampling file
    suggested_filename = get_file_path_of_layer(AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()) or \
                         os.path.join(os.path.dirname(thematic_map.file_path), "systematic {}sampling.gpkg"
                                      .format("post-stratified " if post_stratification_map else ""))

    output_file = get_save_file_name(
        sampling_design,
        "Select the output file to save the sampling",
        suggested_filename,
        "GeoPackage files (*.gpkg);;Shape files (*.shp);;All files (*.*)"
    )

    if not output_file_is_OK(output_file):
        return

    # define the random seed
    if sampling_design.QGBox_random_sampling_options_SystS.isChecked() and sampling_design.with_random_seed_by_user_SystS.isChecked():
        random_seed = sampling_design.random_seed_by_user_SystS.text()
        try:
            random_seed = int(random_seed)
        except:
            pass
    else:
        random_seed = None

    # define the initial inset
    if sampling_design.QCBox_InitialInsetMode_SystS.currentText() == "Random":
        random.seed(random_seed)
        initial_inset = random.uniform(0, points_spacing)
    else:
        initial_inset = float(sampling_design.InitialInsetFixed_SystS.value())

    # before process
    sampling_design.QPBtn_GenerateSamples_SystS.setText("FINISH")
    sampling_design.QPBtn_GenerateSamples_SystS.setStyleSheet("background-color: red")
    sampling_design.widget_SystS_step0.setEnabled(False)
    sampling_design.widget_SystS_step1.setEnabled(False)
    sampling_design.widget_SystS_step2.setEnabled(False)
    sampling_design.QGBox_SystSwithPS.setEnabled(False)
    sampling_design.QGBox_neighbour_aggregation_SystS.setEnabled(False)
    sampling_design.QGBox_random_sampling_options_SystS.setEnabled(False)

    # process the sampling in a QGIS task
    sampling = Sampling("systematic", thematic_map, post_stratification_map=post_stratification_map,
                        sampling_method="grid with random offset", output_file=output_file)
    sampling_conf = {"sampling_type": "systematic", "total_of_samples": total_of_samples, "points_spacing": points_spacing,
                     "initial_inset": initial_inset, "max_xy_offset": max_xy_offset,
                     "classes_selected": classes_selected, "neighbor_aggregation": neighbor_aggregation,
                     "random_seed": random_seed}

    if systematic_sampling_unit == "Distance":
        systematic_sampling_function = sampling.generate_systematic_sampling_points_by_distance
    if systematic_sampling_unit == "Pixels":
        systematic_sampling_function = sampling.generate_systematic_sampling_points_by_pixels

    globals()['sampling_task'] = QgsTask.fromFunction(
        "Systematic sampling", systematic_sampling_function,
        on_finished=systematic_sampling_finished, sampling_conf=sampling_conf)

    globals()['sampling_task'].progressChanged.connect(
        lambda value: sampling_design.QPBar_GenerateSamples_SystS.setValue(math.ceil(total_of_samples * value / 100)))

    QgsApplication.taskManager().addTask(globals()['sampling_task'])


@error_handler
def systematic_sampling_finished(exception, result=None):
    from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
    sampling_design = AcATaMa.dockwidget.sampling_design_window

    # restoring
    sampling_design.QPBtn_GenerateSamples_SystS.setText("Generate samples")
    sampling_design.QPBtn_GenerateSamples_SystS.setStyleSheet("")
    sampling_design.widget_SystS_step0.setEnabled(True)
    sampling_design.widget_SystS_step1.setEnabled(True)
    sampling_design.widget_SystS_step2.setEnabled(True)
    sampling_design.QGBox_SystSwithPS.setEnabled(True)
    sampling_design.QGBox_neighbour_aggregation_SystS.setEnabled(True)
    sampling_design.QGBox_random_sampling_options_SystS.setEnabled(True)
    sampling_design.QPBar_GenerateSamples_SystS.setValue(0)

    if exception is not None or result is None:
        raise Exception("Error in sampling process: {}".format(exception))

    # sampling completed successfully
    sampling, sampling_conf = result

    # zero points
    if sampling.samples_generated < sampling_conf["total_of_samples"] and sampling.samples_generated == 0:
        sampling_design.MsgBar.pushMessage("Error, could not generate any random points with this settings",
                                           level=Qgis.Warning, duration=10)
        return

    sampling_layer_generated = load_layer(sampling.output_file)

    # select the sampling file generated in respond design and analysis tab
    AcATaMa.dockwidget.QCBox_SamplingFile.setLayer(sampling_layer_generated)
    if sampling_layer_generated not in ResponseDesign.instances:
        ResponseDesign(sampling_layer_generated)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(-1)
    AcATaMa.dockwidget.QCBox_SamplingEstimator.setCurrentIndex(0 if sampling.post_stratification_map is None else 1)

    ### sampling report
    sampling_report = SamplingReport(sampling_layer_generated, sampling, sampling_conf)
    sampling_report.show()
    AcATaMa.dockwidget.QPBtn_openSamplingReport.setEnabled(True)

    # success
    if sampling.samples_generated == sampling_conf["total_of_samples"]:
        sampling_report.MsgBar.pushMessage("Systematic random sampling successful: {} samples generated".format(
                                           sampling.samples_generated), level=Qgis.Success, duration=20)
    # success but not completed
    if sampling_conf["total_of_samples"] > sampling.samples_generated > 0:
        sampling_report.MsgBar.pushMessage("Systematic random sampling successful: {} samples generated from {}".format(
                                           sampling.samples_generated, sampling_conf["total_of_samples"]),
                                           level=Qgis.Success, duration=20)


class Sampling(object):

    def __init__(self, sampling_design_type, thematic_map, sampling_map=None, post_stratification_map=None, sampling_method=None, srs_config=None, output_file=None):
        self.sampling_design_type = sampling_design_type
        self.thematic_map = thematic_map
        self.sampling_map = sampling_map
        self.post_stratification_map = post_stratification_map
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
            self.samples_in_strata = [0] * len(self.total_of_samples)  # total generated by categories

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
                self.samples_in_strata[random_sampling_point.index_pixel_value] += 1

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

    def generate_systematic_sampling_points_by_distance(self, task, sampling_conf):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/main/python/plugins/processing/algs/qgis/RegularPoints.py
        """
        self.points_spacing = sampling_conf["points_spacing"]
        self.initial_inset = sampling_conf["initial_inset"]
        self.max_xy_offset = sampling_conf["max_xy_offset"]
        self.classes_for_sampling = sampling_conf["classes_selected"]
        self.neighbor_aggregation = sampling_conf["neighbor_aggregation"]
        self.samples_generated = None  # total generated
        self.random_seed = sampling_conf["random_seed"]

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        # add an epsilon to accept sampling points on the edge of the offset area or map
        epsilon = get_epsilon(for_crs=self.thematic_map.qgs_layer.crs())
        initial_inset = self.initial_inset + epsilon

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        pixel_size_x = self.thematic_map.qgs_layer.rasterUnitsPerPixelX()
        pixel_size_y = self.thematic_map.qgs_layer.rasterUnitsPerPixelY()

        # init the random sampling seed
        random.seed(self.random_seed)

        points_generated = []
        pixels_sampled = []  # to check and avoid duplicate sampled pixels

        y = self.thematic_map.extent().yMaximum() - initial_inset
        while not task.isCanceled() and y >= self.thematic_map.extent().yMinimum() - self.points_spacing:
            x = self.thematic_map.extent().xMinimum() + initial_inset
            while not task.isCanceled() and x <= self.thematic_map.extent().xMaximum() + self.points_spacing:

                ### aligned sampling without offset
                if self.max_xy_offset == 0:
                    random_sampling_point = RandomPoint(x, y)
                    _x_centroid, _y_centroid = self.thematic_map.get_pixel_centroid(x, y)

                    # check if the pixel is not already sampled
                    if (_x_centroid, _y_centroid) in pixels_sampled:
                        x += self.points_spacing
                        continue

                    # do multi-checks to the sampling point, else discard and continue
                    if not self.check_sampling_point(random_sampling_point):
                        x += self.points_spacing
                        continue

                    points_generated.append(random_sampling_point)
                    pixels_sampled.append((_x_centroid, _y_centroid))

                    x += self.points_spacing
                    # update task progress
                    task.setProgress(len(points_generated) / sampling_conf["total_of_samples"] * 100)
                    continue

                ### with random offset
                # define the offset grid area by each aligning grid point
                x_offset_grid = np.arange(x - self.max_xy_offset, x + self.max_xy_offset, pixel_size_x)
                y_offset_grid = np.arange(y - self.max_xy_offset + 2 * epsilon, y + self.max_xy_offset, pixel_size_y)
                # add border points
                x_offset_grid = np.append(x_offset_grid, x + self.max_xy_offset - 2 * epsilon)
                y_offset_grid = np.append(y_offset_grid, y + self.max_xy_offset)

                # gather all the valid thematic pixels centroids in the offset area
                pixels_in_offset_grid = []
                for x_offset in x_offset_grid:
                    for y_offset in y_offset_grid:

                        x_centroid, y_centroid = self.thematic_map.get_pixel_centroid(x_offset, y_offset)
                        if x_centroid is None or y_centroid is None:
                            continue

                        pixel_value = self.thematic_map.get_pixel_value_from_xy(x_centroid, y_centroid)
                        if pixel_value is None or pixel_value == self.thematic_map.nodata:
                            continue

                        if (x_centroid, y_centroid) in pixels_in_offset_grid:
                            continue

                        pixels_in_offset_grid.append((x_centroid, y_centroid))

                # if all pixels in the offset grid are None
                if not pixels_in_offset_grid:
                    x += self.points_spacing
                    continue

                while not task.isCanceled():
                    if not pixels_in_offset_grid:
                        x += self.points_spacing
                        break

                    # generate a random point inside the offset area
                    _x = random.uniform(x - self.max_xy_offset, x + self.max_xy_offset)
                    _y = random.uniform(y - self.max_xy_offset, y + self.max_xy_offset)
                    random_sampling_point = RandomPoint(_x, _y)
                    # get the pixel centroid of the random point
                    _x_centroid, _y_centroid = self.thematic_map.get_pixel_centroid(_x, _y)

                    # check if the random point centroid is in the pixel_in_offset_grid
                    if (_x_centroid, _y_centroid) not in pixels_in_offset_grid:
                        continue

                    # check if the pixel is not already sampled
                    if (_x_centroid, _y_centroid) in pixels_sampled:
                        pixels_in_offset_grid.remove((_x_centroid, _y_centroid))
                        continue

                    # do multi-checks to the sampling point, else discard and continue
                    if not self.check_sampling_point(random_sampling_point):
                        pixels_in_offset_grid.remove((_x_centroid, _y_centroid))
                        continue

                    points_generated.append(random_sampling_point)
                    pixels_sampled.append((_x_centroid, _y_centroid))

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

    def generate_systematic_sampling_points_by_pixels(self, task, sampling_conf):
        """Some code base from (by Alexander Bruy):
        https://github.com/qgis/QGIS/blob/master/python/plugins/processing/algs/qgis/RegularPoints.py
        """
        self.points_spacing = int(sampling_conf["points_spacing"])
        self.initial_inset = int(sampling_conf["initial_inset"])
        self.max_xy_offset = int(sampling_conf["max_xy_offset"])
        self.classes_for_sampling = sampling_conf["classes_selected"]
        self.neighbor_aggregation = sampling_conf["neighbor_aggregation"]
        self.samples_generated = None  # total generated
        self.random_seed = sampling_conf["random_seed"]

        self.ThematicR_boundaries = QgsGeometry().fromRect(self.thematic_map.extent())

        initial_inset = self.initial_inset

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int, '', 10, 0))
        thematic_CRS = self.thematic_map.qgs_layer.crs()
        file_format = \
            "GPKG" if self.output_file.endswith(".gpkg") else "ESRI Shapefile" if self.output_file.endswith(".shp") else None
        writer = QgsVectorFileWriter(self.output_file, "System", fields, QgsWkbTypes.Point, thematic_CRS, file_format)

        pixel_size_x = self.thematic_map.qgs_layer.rasterUnitsPerPixelX()
        pixel_size_y = self.thematic_map.qgs_layer.rasterUnitsPerPixelY()

        # init the random sampling seed
        random.seed(self.random_seed)

        points_generated = []
        pixels_sampled = []  # to check and avoid duplicate sampled pixels

        y = self.thematic_map.extent().yMaximum() - pixel_size_y * initial_inset
        while not task.isCanceled() and y >= self.thematic_map.extent().yMinimum() - pixel_size_y * self.points_spacing:
            x = self.thematic_map.extent().xMinimum() + pixel_size_x * initial_inset
            while not task.isCanceled() and x <= self.thematic_map.extent().xMaximum() + pixel_size_x * self.points_spacing:

                ### aligned sampling without offset
                if self.max_xy_offset == 0:
                    # select the pixel where the aligned grid is in the top-left corner
                    _x, _y = self.thematic_map.get_pixel_centroid(x + pixel_size_x/2, y - pixel_size_y/2)

                    random_sampling_point = RandomPoint(_x, _y)

                    # check if the pixel is not already sampled
                    if (_x, _y) in pixels_sampled:
                        x += pixel_size_x * self.points_spacing
                        continue

                    # do multi-checks to the sampling point, else discard and continue
                    if not self.check_sampling_point(random_sampling_point):
                        x += pixel_size_x * self.points_spacing
                        continue

                    points_generated.append(random_sampling_point)
                    pixels_sampled.append((_x, _y))

                    x += pixel_size_x * self.points_spacing
                    # update task progress
                    task.setProgress(len(points_generated) / sampling_conf["total_of_samples"] * 100)
                    continue

                ### with random offset
                # define the offset grid area by each aligning grid point
                x_offset_grid = np.arange(x - pixel_size_x * self.max_xy_offset, x + pixel_size_x * self.max_xy_offset - pixel_size_x/2, pixel_size_x)
                y_offset_grid = np.arange(y - pixel_size_y * self.max_xy_offset + pixel_size_y, y + pixel_size_y * self.max_xy_offset + pixel_size_y/2, pixel_size_y)

                # gather all the valid thematic pixels centroids in the offset area
                pixels_in_offset_grid = []
                for x_offset in x_offset_grid:
                    for y_offset in y_offset_grid:

                        # select the pixel where the offset grid is in the top-left corner
                        _x, _y = self.thematic_map.get_pixel_centroid(x_offset + pixel_size_x / 2, y_offset - pixel_size_y / 2)

                        if _x is None or _y is None:
                            continue

                        pixel_value = self.thematic_map.get_pixel_value_from_xy(_x, _y)
                        if pixel_value is None or pixel_value == self.thematic_map.nodata:
                            continue

                        if (_x, _y) in pixels_in_offset_grid:
                            continue

                        pixels_in_offset_grid.append((_x, _y))

                # if all pixels in the offset grid are None
                if not pixels_in_offset_grid:
                    x += pixel_size_x * self.points_spacing
                    continue

                while not task.isCanceled():
                    if not pixels_in_offset_grid:
                        x += pixel_size_x * self.points_spacing
                        break

                    _x, _y = random.choice(pixels_in_offset_grid)

                    random_sampling_point = RandomPoint(_x, _y)

                    # check if the pixel is not already sampled
                    if (_x, _y) in pixels_sampled:
                        pixels_in_offset_grid.remove((_x, _y))
                        continue

                    # do multi-checks to the sampling point, else discard and continue
                    if not self.check_sampling_point(random_sampling_point):
                        pixels_in_offset_grid.remove((_x, _y))
                        continue

                    points_generated.append(random_sampling_point)
                    pixels_sampled.append((_x, _y))

                    x += pixel_size_x * self.points_spacing
                    # update task progress
                    task.setProgress(len(points_generated)/sampling_conf["total_of_samples"]*100)
                    break

            y -= pixel_size_y * self.points_spacing

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
            if not sampling_point.in_post_stratification_map(self.classes_for_sampling, self.post_stratification_map):
                return False

        if self.sampling_design_type == "stratified":
            if not sampling_point.in_max_samples_in_stratum(self.classes_for_sampling, self.total_of_samples,
                                                            self.sampling_map, self.samples_in_strata):
                return False

        if self.neighbor_aggregation and \
                not sampling_point.check_neighbors_aggregation(self.thematic_map, *self.neighbor_aggregation):
            return False

        return True
