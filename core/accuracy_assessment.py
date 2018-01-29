# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2018 by Xavier Corredor Llano, SMBYC
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
from PyQt4 import QtGui, uic
from PyQt4.QtGui import QApplication
from qgis.gui import QgsMessageBar

from AcATaMa.core.classification import Classification
from AcATaMa.core.dockwidget import get_current_layer_in, get_current_file_path_in
from AcATaMa.core.raster import Raster
from AcATaMa.core.utils import wait_process
from AcATaMa.gui import accuracy_assessment_results


class AccuracyAssessment:

    def __init__(self, classification):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        self.classification = classification
        self.ThematicR = Raster(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicRaster,
                                nodata=int(AcATaMa.dockwidget.nodata_ThematicRaster.value()))
        self.thematic_pixels_count = {}

    @wait_process()
    def compute(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText(u"Processing, please wait ...")
        QApplication.processEvents()

        # get labels from classification buttons
        labels = {}
        for button_config in self.classification.buttons_config.values():
            labels[button_config["thematic_class"]] = button_config["name"]

        # get the classified and thematic map values
        thematic_map_values = []
        classified_values = []
        classification_points = [point for point in self.classification.points if point.is_classified]
        points_ordered = sorted(classification_points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # classification from the pixel values in the thematic map
            thematic_map_value = self.ThematicR.get_pixel_value_from_pnt(point.QgsPnt)
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
        # set area by pixel
        self.pixel_area = self.ThematicR.qgs_layer.rasterUnitsPerPixelX() * self.ThematicR.qgs_layer.rasterUnitsPerPixelY()
        self.pixel_area_ha = self.pixel_area / 10000.0  # hectare


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'accuracy_assessment_dialog.ui'))


class AccuracyAssessmentDialog(QtGui.QDialog, FORM_CLASS):
    is_opened = False

    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        # dialog buttons box
        self.DialogButtons.rejected.connect(self.closing)
        self.DialogButtons.button(QtGui.QDialogButtonBox.Save).setText("Export to CSV")
        self.DialogButtons.button(QtGui.QDialogButtonBox.Save).clicked.connect(self.export_to_csv)

        self.reloadButton.clicked.connect(self.reload)
        self.SettingsGroupBox.setVisible(False)
        self.z_score.valueChanged.connect(self.reload)

        # get AccuracyAssessment or init new instance
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        sampling_layer = get_current_layer_in(AcATaMa.dockwidget.QCBox_SamplingFile_AA)
        if sampling_layer:
            # sampling file valid
            if sampling_layer in Classification.instances:
                # classification exists for this file
                classification = Classification.instances[sampling_layer]
                if classification.accuracy_assessment:
                    self.accuracy_assessment = classification.accuracy_assessment
                else:
                    self.accuracy_assessment = AccuracyAssessment(classification)
                    classification.accuracy_assessment = self.accuracy_assessment

    def show(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # first check
        classification_points = [point for point in self.accuracy_assessment.classification.points if point.is_classified]
        if len(classification_points) == 0:
            AcATaMa.dockwidget.iface.messageBar().pushMessage("AcATaMa",
                  "The accuracy assessment needs at least one sample classified",
                  level=QgsMessageBar.WARNING)
            return

        AccuracyAssessmentDialog.is_opened = True
        # set adjust variables from dialog
        self.accuracy_assessment.z_score = self.z_score.value()
        # first compute the accuracy assessment
        self.accuracy_assessment.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.accuracy_assessment))

        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText(u"Accuracy assessment is opened, click to show")
        super(AccuracyAssessmentDialog, self).show()

    def reload(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        # set adjust variables from dialog
        self.accuracy_assessment.z_score = self.z_score.value()
        # first compute the accuracy assessment
        self.accuracy_assessment.compute()
        # set content results in HTML
        self.ResultsHTML.setHtml(accuracy_assessment_results.get_html(self.accuracy_assessment))
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText(u"Accuracy assessment is opened, click to show")

    def export_to_csv(self):
        # get file path to suggest to save but not in tmp directory
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        path, filename = os.path.split(get_current_file_path_in(AcATaMa.dockwidget.QCBox_SamplingFile_AA))
        if AcATaMa.dockwidget.tmp_dir in path:
            path = os.path.split(get_current_file_path_in(AcATaMa.dockwidget.QCBox_ThematicRaster))[0]
        suggested_filename = os.path.splitext(os.path.join(path, filename))[0] + "_results.csv"

        file_out = QtGui.QFileDialog.getSaveFileName(self, self.tr(u"Export accuracy assessment results to csv"),
                                                     suggested_filename,
                                                     self.tr(u"CSV files (*.csv);;All files (*.*)"))
        if file_out != '':
            try:
                csv_separator = self.CSV_separator.text()
                csv_decimal_separator = self.CSV_decimal_sep.text()
                accuracy_assessment_results.export_to_csv(self.accuracy_assessment, file_out,
                                                          csv_separator, csv_decimal_separator)
                AcATaMa.dockwidget.iface.messageBar().pushMessage("AcATaMa", "File saved successfully",
                                                                  level=QgsMessageBar.SUCCESS)
            except:
                AcATaMa.dockwidget.iface.messageBar().pushMessage("AcATaMa", "Failed export results in csv file",
                                                                  level=QgsMessageBar.WARNING)

    def closeEvent(self, event):
        self.closing()
        event.ignore()

    def closing(self):
        """
        Do this before close the classification dialog
        """
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        AccuracyAssessmentDialog.is_opened = False
        AcATaMa.dockwidget.QPBtn_ComputeViewAccurasyAssessment.setText(u"Open the accuracy assessment results")
        self.reject(is_ok_to_close=True)

    def reject(self, is_ok_to_close=False):
        if is_ok_to_close:
            super(AccuracyAssessmentDialog, self).reject()