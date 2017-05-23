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

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal, Qt
from qgis.utils import iface
from qgis.core import QgsMapLayerRegistry, QgsMapLayer

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'acatama_dockwidget_base.ui'))


class AcATaMaDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(AcATaMaDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.canvas = iface.mapCanvas()
        self.setupUi(self)
        self.setup_gui()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def updateLayersList_ThematicRaster(self):
        save_selected = self.select_TRI.currentText()
        self.select_TRI.clear()

        # list of only raster layer loaded in qgis
        layers = [layer for layer in QgsMapLayerRegistry.instance().mapLayers().values()
                  if layer.type() == QgsMapLayer.RasterLayer]
        # added list to combobox
        [self.select_TRI.addItem(layer.name()) for layer in layers]

        selected_index = self.select_TRI.findText(save_selected, Qt.MatchFixedString)
        self.select_TRI.setCurrentIndex(selected_index)

    def setup_gui(self):
        # plugin info #########
        # load thematic raster image #########
        self.updateLayersList_ThematicRaster()
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(self.updateLayersList_ThematicRaster)

