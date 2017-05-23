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
from PyQt4.QtCore import pyqtSignal, Qt, pyqtSlot
from qgis.utils import iface
from qgis.core import QgsMapLayerRegistry, QgsMapLayer, QgsRasterLayer

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

    def setup_gui(self):
        # plugin info #########
        # load thematic raster image #########
        self.updateLayersList(self.selectThematicRaster, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: self.updateLayersList(self.selectThematicRaster, "raster"))
        # call to search shape area selector file
        self.browseThematicRaster.clicked.connect(self.fileDialog_browseThematicRaster)

    def updateLayersList(self, combo_box, layer_type="any"):
        if not QgsMapLayerRegistry:
            return
        save_selected = combo_box.currentText()
        combo_box.clear()

        # list of layers loaded in qgis filter by type
        if layer_type == "raster":
            layers = [layer for layer in QgsMapLayerRegistry.instance().mapLayers().values()
                      if layer.type() == QgsMapLayer.RasterLayer]
        if layer_type == "vector":
            layers = [layer for layer in QgsMapLayerRegistry.instance().mapLayers().values()
                      if layer.type() == QgsMapLayer.VectorLayer]
        if layer_type == "any":
            layers = QgsMapLayerRegistry.instance().mapLayers().values()
        # added list to combobox
        if layers:
            [combo_box.addItem(layer.name()) for layer in layers]

        selected_index = combo_box.findText(save_selected, Qt.MatchFixedString)
        combo_box.setCurrentIndex(selected_index)

    @pyqtSlot()
    def fileDialog_browseThematicRaster(self):
        tri_path = \
            str(QtGui.QFileDialog.getOpenFileName(self, self.tr(u"Select the thematic raster image to evaluate"),
                                                  "", self.tr(u"Raster files (*.tif *.img);;All files (*.*)")))
        if tri_path != '' and os.path.isfile(tri_path):
            # Open in QGIS
            tri_filename = os.path.splitext(os.path.basename(tri_path))[0]
            tri_layer = QgsRasterLayer(tri_path, tri_filename)
            if tri_layer.isValid():
                QgsMapLayerRegistry.instance().addMapLayer(tri_layer)
            else:
                self.iface.messageBar().pushMessage("Error",
                                                    "{} is not a valid raster file!".format(os.path.basename(tri_path)))
            # add to layers list
            self.updateLayersList(self.selectThematicRaster, "raster")
            selected_index = self.selectThematicRaster.findText(tri_filename, Qt.MatchFixedString)
            self.selectThematicRaster.setCurrentIndex(selected_index)
