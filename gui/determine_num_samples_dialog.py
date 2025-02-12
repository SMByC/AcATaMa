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

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import pyqtSlot

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'determine_num_samples_simple.ui'))


class DetermineNumberSamplesDialog(QDialog, FORM_CLASS):

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        # connect signals
        self.OverallAccuracy.valueChanged.connect(self.get_n)
        self.HalfWidthCI.valueChanged.connect(self.get_n)
        self.ConfidenceInterval.currentIndexChanged.connect(self.get_n)
        # initialize
        self.get_n()

    @staticmethod
    def get_z_value(confidence_interval):
        z_values = {
            0.80: 1.282,
            0.85: 1.440,
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        return z_values[confidence_interval]

    @pyqtSlot()
    def get_n(self):
        """
        Determine the number of samples
        """
        overall_accuracy = self.OverallAccuracy.value()/100
        half_width_ci = self.HalfWidthCI.value()/100
        confidence_interval = float(self.ConfidenceInterval.currentText().replace('%', ''))/100

        z = self.get_z_value(confidence_interval)
        n = (z**2 * overall_accuracy * (1 - overall_accuracy)) / (half_width_ci**2)

        self.NumberOfSamples.setText(str(round(n)))

        if n < 300:
            self.NoteMinSamples.setVisible(True)
        else:
            self.NoteMinSamples.setVisible(False)

