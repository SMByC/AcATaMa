# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2025 by Xavier C. Llano, SMByC
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

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QApplication, QDialogButtonBox, QDialog
from qgis.core import Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.map import Map
from AcATaMa.core.response_design import ResponseDesign
from AcATaMa.gui import accuracy_assessment_results
from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import wait_process, output_file_is_OK, get_save_file_name
from AcATaMa.utils.others_utils import get_nodata_format


class Analysis(object):

    def __init__(self, response_design):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        self.values = None
        self.labels = None
        self.error_matrix = None
        self.samples_outside_the_thematic = None
        self.pixel_area_base = None
        self.pixel_area_value = None
        self.pixel_area_unit = None

        self.response_design = response_design
        self.thematic_map = Map(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicMap,
                                band=int(AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText())
                                     if AcATaMa.dockwidget.QCBox_band_ThematicMap.currentText() else None,
                                nodata=get_nodata_format(AcATaMa.dockwidget.nodata_ThematicMap.text()))
        self.thematic_pixels_count = {}
        # dialog settings
        self.area_unit = None
        self.z_score = 1.96
        self.csv_separator = ";"
        self.csv_decimal = "."
        # define the base area unit based on the thematic map distance unit
        self.dist_unit = self.thematic_map.qgs_layer.crs().mapUnits()
        if self.dist_unit == QgsUnitTypes.DistanceUnknownUnit:
            # thematic map with unknown map unit
            self.dist_unit = QgsUnitTypes.DistanceMeters
        self.base_area_unit = QgsUnitTypes.distanceToAreaUnit(self.dist_unit)

    @wait_process
    def compute(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Processing, please wait ...")
        QApplication.processEvents()

        # get labels from labeling buttons
        labels = {}
        for button_config in self.response_design.buttons_config.values():
            labels[button_config["thematic_class"]] = button_config["name"]

        # get the labeled thematic map classes and validation values
        thematic_map = []  # map values for the sampling points
        validation = []  # user validation - labeling
        samples_outside_the_thematic = []
        points_labeled = [point for point in self.response_design.points if point.is_labeled]
        points_ordered = sorted(points_labeled, key=lambda p: p.sample_id)
        for point in points_ordered:
            # response design labeling from the pixel values in the thematic map
            thematic_map_in_sample = self.thematic_map.get_pixel_value_from_pnt(point.QgsPnt)
            if thematic_map_in_sample is None:
                samples_outside_the_thematic.append(point)
                continue
            thematic_map.append(int(thematic_map_in_sample))
            # thematic classes used in buttons
            validation_in_sample = self.response_design.buttons_config[point.label_id]["thematic_class"]
            validation.append(int(validation_in_sample))

        # all unique and sorted values
        values = sorted(set(thematic_map + validation))
        # Construct a value->index dictionary
        indices = dict((val, i) for (i, val) in enumerate(values))

        # calculate the error/confusion matrix
        # https://github.com/nltk/nltk/blob/develop/nltk/metrics/confusionmatrix.py
        #
        #                validation
        #     |    | L1 | L2 | L3 | L4 |
        #   m | L1 |    |    |    |    |
        #   a | L2 |    |    |    |    |
        #   p | L3 |    |    |    |    |
        #     | L4 |    |    |    |    |
        #
        error_matrix = [[0 for column in values] for row in values]
        for thematic_map_in_sample, validation_in_sample in zip(thematic_map, validation):
            error_matrix[indices[thematic_map_in_sample]][indices[validation_in_sample]] += 1

        # calculate the total number of pixels in the thematic map
        # by each thematic map class used in the label buttons
        for thematic_map_in_sample in values:
            if thematic_map_in_sample not in self.thematic_pixels_count:
                self.thematic_pixels_count[thematic_map_in_sample] = self.thematic_map.get_total_pixels_by_value(thematic_map_in_sample)
                if self.thematic_pixels_count[thematic_map_in_sample] is None:
                    # this happens when pixel value to count is nodata in thematic map
                    self.thematic_pixels_count[thematic_map_in_sample] = 0

        # values necessary for results
        self.values = values
        self.labels = labels
        self.error_matrix = error_matrix
        self.samples_outside_the_thematic = samples_outside_the_thematic
        # set area by pixel
        self.pixel_area_base = self.thematic_map.qgs_layer.rasterUnitsPerPixelX() * self.thematic_map.qgs_layer.rasterUnitsPerPixelY()
        self.pixel_area_value = self.pixel_area_base * QgsUnitTypes.fromUnitToUnitFactor(self.base_area_unit, self.area_unit)
        self.pixel_area_unit = QgsUnitTypes.toAbbreviatedString(self.area_unit)


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'accuracy_assessment_window.ui'))


class AccuracyAssessmentWindow(QDialog, FORM_CLASS):
    is_opened = False

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        # dialog buttons box
        self.DialogButtons.rejected.connect(self.closing)
        self.DialogButtons.button(QDialogButtonBox.Save).setText("Export to CSV")
        self.DialogButtons.button(QDialogButtonBox.Save).clicked.connect(self.export_to_csv)

        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()

        # get AccuracyAssessment or init new instance
        if sampling_layer:
            # sampling file valid
            if sampling_layer in ResponseDesign.instances:
                # response design exists for this file
                response_design = ResponseDesign.instances[sampling_layer]
                if response_design.analysis:
                    self.analysis = response_design.analysis
                    # restore config to window
                    self.z_score.setValue(self.analysis.z_score)
                    self.CSV_separator.setText(self.analysis.csv_separator)
                    self.CSV_decimal_sep.setText(self.analysis.csv_decimal)
                else:
                    self.analysis = Analysis(response_design)
                    response_design.analysis = self.analysis

        # fill the area units
        self.area_unit.clear()
        for area_unit in sorted(QgsUnitTypes.AreaUnit, key=lambda x: x.value):
            self.area_unit.addItem("{} ({})".format(QgsUnitTypes.toString(area_unit),
                                                    QgsUnitTypes.toAbbreviatedString(area_unit)))
        # set the area unit saved or based on the sampling file by default
        if self.analysis.area_unit is not None:
            self.area_unit.setCurrentIndex(self.analysis.area_unit)
        else:
            self.analysis.area_unit = QgsUnitTypes.distanceToAreaUnit(self.analysis.dist_unit)
            self.area_unit.setCurrentIndex(self.analysis.area_unit)
            # thematic map with unknown map unit
            if self.analysis.thematic_map.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
                self.MsgBar.pushMessage(
                    "The thematic map \"{}\" does not have a valid map unit, considering \"{}\" as the base unit!".format(
                        self.analysis.thematic_map.qgs_layer.name(),
                        QgsUnitTypes.toString(self.analysis.dist_unit)),
                    level=Qgis.Warning, duration=0)

        self.area_unit.currentIndexChanged.connect(lambda: self.reload(msg_bar=False))
        self.z_score.valueChanged.connect(lambda: self.reload(msg_bar=False))
        self.CSV_separator.textChanged.connect(lambda value: setattr(self.analysis, "csv_separator", value))
        self.CSV_decimal_sep.textChanged.connect(lambda value: setattr(self.analysis, "csv_decimal", value))
        self.reloadButton.clicked.connect(lambda: self.reload(msg_bar=True))

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # first check
        if self.analysis.response_design.total_labeled == 0:
            iface.messageBar().pushMessage("AcATaMa",
                                           "The accuracy assessment needs at least one sample labeled",
                                           level=Qgis.Warning, duration=10)
            return

        AccuracyAssessmentWindow.is_opened = True
        # first, set the estimator for accuracy assessment from dropdown selected
        self.analysis.estimator = AcATaMa.dockwidget.QCBox_SamplingEstimator.currentText()
        # second, compute the accuracy assessment
        self.analysis.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.analysis))
        self.ResultsHTML.zoomOut()

        AcATaMa.dockwidget.QGBox_ThematicMap.setDisabled(True)
        AcATaMa.dockwidget.QGBox_SamplingDesign.setDisabled(True)
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        super(AccuracyAssessmentWindow, self).show()

    def reload(self, msg_bar=True):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # set adjust variables from window
        self.analysis.z_score = self.z_score.value()
        self.analysis.area_unit = QgsUnitTypes.AreaUnit(self.area_unit.currentIndex())
        # first compute the accuracy assessment
        self.analysis.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.analysis))
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        if msg_bar:
            self.MsgBar.pushMessage(
                "Reload successfully from response design state for \"{}\"".format(
                    AcATaMa.dockwidget.QCBox_SamplingFile.currentText()), level=Qgis.Success, duration=10)

    def export_to_csv(self):
        # get file path to suggest where to save but not in tmp directory
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        file_path = get_file_path_of_layer(AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer())
        path, filename = os.path.split(file_path)
        if AcATaMa.dockwidget.tmp_dir in path:
            path = os.path.split(get_file_path_of_layer(AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer()))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + " - results.csv" if filename else "acatama results.csv"

        output_file = get_save_file_name(self, "Export accuracy assessment results to csv",
                                         suggested_filename, "CSV files (*.csv);;All files (*.*)")

        if output_file_is_OK(output_file):
            try:
                accuracy_assessment_results.export_to_csv(self.analysis, output_file,
                                                          self.analysis.csv_separator,
                                                          self.analysis.csv_decimal)
                self.MsgBar.pushMessage(
                    "File saved successfully \"{}\"".format(os.path.basename(output_file)), level=Qgis.Success, duration=10)
            except Exception as err:
                self.MsgBar.pushMessage(
                    "Failed saving the csv file: {}".format(err), level=Qgis.Critical, duration=10)

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the accuracy assessment windows
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        from AcATaMa.gui.response_design_window import ResponseDesignWindow
        from AcATaMa.gui.sampling_design_window import SamplingDesignWindow
        if not SamplingDesignWindow.is_opened and not ResponseDesignWindow.is_opened:
            AcATaMa.dockwidget.QGBox_ThematicMap.setEnabled(True)
        if not ResponseDesignWindow.is_opened:
            AcATaMa.dockwidget.QGBox_SamplingDesign.setEnabled(True)
        AccuracyAssessmentWindow.is_opened = False
        AcATaMa.dockwidget.QPBtn_ComputeTheAccurasyAssessment.setText("Compute the accuracy assessment")
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(AccuracyAssessmentWindow, self).reject()
