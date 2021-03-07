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

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QApplication, QDialogButtonBox, QDialog, QFileDialog
from qgis.core import Qgis, QgsUnitTypes
from qgis.utils import iface

from AcATaMa.core.raster import Raster
from AcATaMa.core.classification import Classification
from AcATaMa.gui import accuracy_assessment_results
from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import wait_process


class AccuracyAssessment(object):

    def __init__(self, classification):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        self.classification = classification
        self.ThematicR = Raster(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicRaster,
                                band=int(AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText())
                                if AcATaMa.dockwidget.QCBox_band_ThematicRaster.currentText() else None,
                                nodata=int(AcATaMa.dockwidget.nodata_ThematicRaster.value()))
        self.thematic_pixels_count = {}
        # dialog settings
        self.area_unit = None
        self.z_score = 1.96
        self.csv_separator = ";"
        self.csv_decimal = "."
        # define the base area unit based on the thematic raster distance unit
        self.dist_unit = self.ThematicR.qgs_layer.crs().mapUnits()
        if self.dist_unit == QgsUnitTypes.DistanceUnknownUnit:
            # thematic raster with unknown map unit
            self.dist_unit = QgsUnitTypes.DistanceMeters
        self.base_area_unit = QgsUnitTypes.distanceToAreaUnit(self.dist_unit)

    @wait_process
    def compute(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText("Processing, please wait ...")
        QApplication.processEvents()

        # get labels from classification buttons
        labels = {}
        for button_config in self.classification.buttons_config.values():
            labels[button_config["thematic_class"]] = button_config["name"]

        # get the classified and thematic map values
        thematic_map_values = []
        classified_values = []
        samples_outside_the_thematic = []
        classification_points = [point for point in self.classification.points if point.is_classified]
        points_ordered = sorted(classification_points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # classification from the pixel values in the thematic map
            thematic_map_value = self.ThematicR.get_pixel_value_from_pnt(point.QgsPnt)
            if not thematic_map_value:
                samples_outside_the_thematic.append(point)
                continue
            thematic_map_values.append(int(thematic_map_value))
            # classified value made/checked by user with classification buttons
            classified_value = self.classification.buttons_config[point.classif_id]["thematic_class"]
            classified_values.append(int(classified_value))

        # all unique and sorted values
        values = sorted(set(thematic_map_values + classified_values))
        # Construct a value->index dictionary
        indices = dict((val, i) for (i, val) in enumerate(values))

        # calculate the error/confusion matrix
        # https://github.com/nltk/nltk/blob/develop/nltk/metrics/confusionmatrix.py
        #
        #             classified
        #   t |    | L1 | L2 | L3 | L4 |
        #   h | L1 |    |    |    |    |
        #   e | L2 |    |    |    |    |
        #   m | L3 |    |    |    |    |
        #   a | L4 |    |    |    |    |
        #
        error_matrix = [[0 for column in values] for row in values]
        for thematic, classified in zip(thematic_map_values, classified_values):
            error_matrix[indices[thematic]][indices[classified]] += 1

        # calculate the total number of pixel in the thematic raster
        # by each thematic raster class used in the classification buttons
        for thematic_map_value in values:
            if thematic_map_value not in self.thematic_pixels_count:
                self.thematic_pixels_count[thematic_map_value] = self.ThematicR.get_total_pixels_by_value(thematic_map_value)

        # values necessary for results
        self.values = values
        self.labels = labels
        self.error_matrix = error_matrix
        self.samples_outside_the_thematic = samples_outside_the_thematic
        # set area by pixel
        self.pixel_area_base = self.ThematicR.qgs_layer.rasterUnitsPerPixelX() * self.ThematicR.qgs_layer.rasterUnitsPerPixelY()
        self.pixel_area_value = self.pixel_area_base * QgsUnitTypes.fromUnitToUnitFactor(self.base_area_unit, self.area_unit)
        self.pixel_area_unit = QgsUnitTypes.toAbbreviatedString(self.area_unit)


# Qgis 3 ares units, int values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
AREA_UNITS = [QgsUnitTypes.AreaSquareMeters, QgsUnitTypes.AreaSquareKilometers, QgsUnitTypes.AreaSquareFeet,
              QgsUnitTypes.AreaSquareYards, QgsUnitTypes.AreaSquareMiles, QgsUnitTypes.AreaHectares,
              QgsUnitTypes.AreaAcres, QgsUnitTypes.AreaSquareNauticalMiles, QgsUnitTypes.AreaSquareDegrees,
              QgsUnitTypes.AreaSquareCentimeters, QgsUnitTypes.AreaSquareMillimeters]

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'accuracy_assessment_dialog.ui'))


class AccuracyAssessmentDialog(QDialog, FORM_CLASS):
    is_opened = False

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        # dialog buttons box
        self.DialogButtons.rejected.connect(self.closing)
        self.DialogButtons.button(QDialogButtonBox.Save).setText("Export to CSV")
        self.DialogButtons.button(QDialogButtonBox.Save).clicked.connect(self.export_to_csv)

        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile_AA.currentLayer()

        # get AccuracyAssessment or init new instance
        if sampling_layer:
            # sampling file valid
            if sampling_layer in Classification.instances:
                # classification exists for this file
                classification = Classification.instances[sampling_layer]
                if classification.accuracy_assessment:
                    self.accuracy_assessment = classification.accuracy_assessment
                    # restore config to dialog
                    self.z_score.setValue(self.accuracy_assessment.z_score)
                    self.CSV_separator.setText(self.accuracy_assessment.csv_separator)
                    self.CSV_decimal_sep.setText(self.accuracy_assessment.csv_decimal)
                else:
                    self.accuracy_assessment = AccuracyAssessment(classification)
                    classification.accuracy_assessment = self.accuracy_assessment

        # fill the area units
        self.area_unit.clear()
        for area_unit in AREA_UNITS:
            self.area_unit.addItem("{} ({})".format(QgsUnitTypes.toString(area_unit),
                                                    QgsUnitTypes.toAbbreviatedString(area_unit)))
        # set the area unit saved or based on the sampling file by default
        if self.accuracy_assessment.area_unit is not None:
            self.area_unit.setCurrentIndex(self.accuracy_assessment.area_unit)
        else:
            self.accuracy_assessment.area_unit = QgsUnitTypes.distanceToAreaUnit(self.accuracy_assessment.dist_unit)
            self.area_unit.setCurrentIndex(self.accuracy_assessment.area_unit)
            # thematic raster with unknown map unit
            if self.accuracy_assessment.ThematicR.qgs_layer.crs().mapUnits() == QgsUnitTypes.DistanceUnknownUnit:
                self.MsgBar.pushMessage(
                    "The thematic raster \"{}\" does not have a valid map unit, considering \"{}\" as the base unit!".format(
                        self.accuracy_assessment.ThematicR.qgs_layer.name(),
                        QgsUnitTypes.toString(self.accuracy_assessment.dist_unit)),
                    level=Qgis.Warning, duration=-1)

        self.area_unit.currentIndexChanged.connect(lambda: self.reload(msg_bar=False))
        self.z_score.valueChanged.connect(lambda: self.reload(msg_bar=False))
        self.CSV_separator.textChanged.connect(lambda value: setattr(self.accuracy_assessment, "csv_separator", value))
        self.CSV_decimal_sep.textChanged.connect(lambda value: setattr(self.accuracy_assessment, "csv_decimal", value))
        self.reloadButton.clicked.connect(lambda: self.reload(msg_bar=True))

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # first check
        if self.accuracy_assessment.classification.total_classified == 0:
            iface.messageBar().pushMessage("AcATaMa",
                                           "The accuracy assessment needs at least one sample classified",
                                           level=Qgis.Warning)
            return

        AccuracyAssessmentDialog.is_opened = True
        # first compute the accuracy assessment
        self.accuracy_assessment.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.accuracy_assessment))
        self.ResultsHTML.zoomOut()

        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        AcATaMa.dockwidget.QGBox_SamplingSelection_AA.setDisabled(True)
        super(AccuracyAssessmentDialog, self).show()

    def reload(self, msg_bar=True):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # set adjust variables from dialog
        self.accuracy_assessment.z_score = self.z_score.value()
        self.accuracy_assessment.area_unit = AREA_UNITS[self.area_unit.currentIndex()]
        # first compute the accuracy assessment
        self.accuracy_assessment.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.accuracy_assessment))
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText("Accuracy assessment is opened, click to show")
        if msg_bar:
            self.MsgBar.pushMessage(
                "Reload successfully from classification status of \"{}\"".format(
                    AcATaMa.dockwidget.QCBox_SamplingFile_AA.currentText()), level=Qgis.Success)

    def export_to_csv(self):
        # get file path to suggest to save but not in tmp directory
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        file_path = get_file_path_of_layer(AcATaMa.dockwidget.QCBox_SamplingFile_AA.currentLayer())
        path, filename = os.path.split(file_path)
        if AcATaMa.dockwidget.tmp_dir in path:
            path = os.path.split(get_file_path_of_layer(AcATaMa.dockwidget.QCBox_ThematicRaster.currentLayer()))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_results.csv" if filename else ""

        file_out, _ = QFileDialog.getSaveFileName(self, self.tr("Export accuracy assessment results to csv"),
                                                  suggested_filename,
                                                  self.tr("CSV files (*.csv);;All files (*.*)"))
        if file_out != '':
            try:
                accuracy_assessment_results.export_to_csv(self.accuracy_assessment, file_out,
                                                          self.accuracy_assessment.csv_separator,
                                                          self.accuracy_assessment.csv_decimal)
                self.MsgBar.pushMessage(
                    "File saved successfully \"{}\"".format(os.path.basename(file_out)), level=Qgis.Success)
            except Exception as err:
                self.MsgBar.pushMessage(
                    "Failed saving the csv file: {}".format(err), level=Qgis.Critical, duration=-1)

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the classification dialog
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AccuracyAssessmentDialog.is_opened = False
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText("Open the accuracy assessment results")
        AcATaMa.dockwidget.QGBox_SamplingSelection_AA.setEnabled(True)
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(AccuracyAssessmentDialog, self).reject()
