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
from qgis.core import QgsMapLayerRegistry, QgsMapLayer, QgsRasterLayer, QgsVectorLayer

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
        # call to browse the thematic raster file
        self.browseThematicRaster.clicked.connect(lambda: self.fileDialog_browse(
            self.selectThematicRaster,
            dialog_title=self.tr(u"Select the thematic raster image to evaluate"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))

        # shape study area #########
        self.widget_ShapeArea.setHidden(True)
        self.updateLayersList(self.selectShapeArea, "vector")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: self.updateLayersList(self.selectShapeArea, "vector"))
        # call to browse the shape area
        self.browseShapeArea.clicked.connect(lambda: self.fileDialog_browse(
            self.selectShapeArea,
            dialog_title=self.tr(u"Select the shape file"),
            dialog_types=self.tr(u"Shape files (*.shp);;All files (*.*)"),
            layer_type="vector"))

        # categorical raster #########
        self.widget_CategRaster.setHidden(True)
        self.updateLayersList(self.selectCategRaster, "raster")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: self.updateLayersList(self.selectCategRaster, "raster"))
        # call to browse the categorical raster
        self.browseCategRaster.clicked.connect(lambda: self.fileDialog_browse(
            self.selectCategRaster,
            dialog_title=self.tr(u"Select the categorical raster file"),
            dialog_types=self.tr(u"Raster files (*.tif *.img);;All files (*.*)"),
            layer_type="raster"))

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
    def fileDialog_browse(self, combo_box, dialog_title, dialog_types, layer_type):
        file_path = str(QtGui.QFileDialog.getOpenFileName(self, dialog_title, "", dialog_types))
        if file_path != '' and os.path.isfile(file_path):
            # Open in QGIS
            filename = os.path.splitext(os.path.basename(file_path))[0]
            if layer_type == "raster":
                layer = QgsRasterLayer(file_path, filename)
            if layer_type == "vector":
                layer = QgsVectorLayer(file_path, filename, "ogr")
            if layer.isValid():
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            else:
                iface.messageBar().pushMessage(self.tr("Error"), self.tr("{} is not a valid {} file!")
                                                    .format(os.path.basename(file_path), layer_type))
            # add to layers list
            self.updateLayersList(combo_box, layer_type)
            selected_index = combo_box.findText(filename, Qt.MatchFixedString)
            combo_box.setCurrentIndex(selected_index)
