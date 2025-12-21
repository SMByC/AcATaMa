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
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import pyqtSlot

from AcATaMa.core.response_design import ResponseDesign

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'response_design_grid_settings.ui'))


class ResponseDesignGridSettings(QDialog, FORM_CLASS):
    is_first_open = True

    def __init__(self, parent=None):
        """Constructor."""
        super(ResponseDesignGridSettings, self).__init__(parent)
        self.setupUi(self)


    @pyqtSlot()
    def on_buttonBox_accepted(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
        if sampling_layer in ResponseDesign.instances:
            response_design = ResponseDesign.instances[sampling_layer]
            response_design.grid_columns = self.columns.value()
            response_design.grid_rows = self.rows.value()

        if ResponseDesignGridSettings.is_first_open:
            ResponseDesignGridSettings.is_first_open = False

        self.accept()

    @pyqtSlot()
    def on_buttonBox_rejected(self):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        sampling_layer = AcATaMa.dockwidget.QCBox_SamplingFile.currentLayer()
        if sampling_layer in ResponseDesign.instances:
            response_design = ResponseDesign.instances[sampling_layer]
            self.columns.setValue(response_design.grid_columns)
            self.rows.setValue(response_design.grid_rows)

        self.reject()