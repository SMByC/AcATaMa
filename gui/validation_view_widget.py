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
from PyQt4.QtCore import QSettings, Qt, pyqtSlot
from qgis.gui import QgsMapCanvas, QgsMapCanvasLayer, QgsMapToolPan
from qgis.utils import iface

from AcATaMa.core.dockwidget import update_layers_list, get_current_layer_in, load_layer_in_qgis


class RenderWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi()

        self.sampling_layer = self.parent().sampling_layer
        self.layer = None

    def setupUi(self):

        gridLayout = QtGui.QGridLayout(self)
        gridLayout.setContentsMargins(0, 0, 0, 0)
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(QtGui.QColor(255, 255, 255))
        settings = QSettings()
        self.canvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type=bool))
        self.canvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type=bool))
        # action zoom
        action = settings.value("/qgis/wheel_action", 0, type=int)
        zoomFactor = settings.value("/qgis/zoom_factor", 2.0, type=float)
        self.canvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        # action pan
        self.toolPan = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(self.toolPan)

        gridLayout.addWidget(self.canvas)

    def render_layer(self, layer):
        if not layer:
            self.canvas.clear()
            self.canvas.refreshAllLayers()
            self.layer = None
            return
        self.canvas.setLayerSet([QgsMapCanvasLayer(self.sampling_layer), QgsMapCanvasLayer(layer)])
        self.update_crs()
        self.canvas.setExtent(layer.extent())
        self.canvas.refresh()
        self.layer = layer

    def update_crs(self):
        renderer = iface.mapCanvas().mapRenderer()
        self.canvas.mapRenderer().setDestinationCrs(renderer.destinationCrs())
        self.canvas.mapRenderer().setMapUnits(renderer.mapUnits())
        # transform enable
        self.canvas.mapRenderer().setProjectionsEnabled(True)

    def extents_changed(self):
        #self.canvas.setExtent(iface.mapCanvas().extent())
        self.canvas.zoomByFactor(self.parent().scaleFactor.value())

    def layer_properties(self):
        if not self.layer:
            return
        # call properties dialog
        iface.showLayerProperties(self.layer)

        self.parent().activateWindow()
        self.canvas.refresh()

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'validation_view_widget.ui'))


class ValidationViewWidget(QtGui.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        # import the sampling layer to validate
        from AcATaMa.gui.validation_dialog import ValidationDialog
        self.sampling_layer = ValidationDialog.sampling_layer
        self.canvas = iface.mapCanvas()
        self.setupUi(self)
        self.is_active = False

        # render layer actions
        update_layers_list(self.selectRenderFile, "any", ignore_layers=[self.sampling_layer])
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(
            lambda: update_layers_list(self.selectRenderFile, "any", ignore_layers=[self.sampling_layer]))
        self.selectRenderFile.currentIndexChanged.connect(
            lambda: self.render_widget.render_layer(get_current_layer_in(self.selectRenderFile)))
        # call to browse the render file
        self.browseRenderFile.clicked.connect(lambda: self.fileDialog_browse(
            self.selectRenderFile,
            dialog_title=self.tr(u"Select the file for this view"),
            dialog_types=self.tr(u"Raster or vector files (*.tif *.img *.shp);;All files (*.*)"),
            layer_type="any"))

        # zoom factor
        self.scaleFactor.valueChanged.connect(self.render_widget.extents_changed)

        # edit layer properties
        self.layerProperties.clicked.connect(self.render_widget.layer_properties)

    @pyqtSlot()
    def fileDialog_browse(self, combo_box, dialog_title, dialog_types, layer_type):
        file_path = QtGui.QFileDialog.getOpenFileName(self, dialog_title, "", dialog_types)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            filename = load_layer_in_qgis(file_path, layer_type)
            update_layers_list(combo_box, layer_type, ignore_layers=[self.sampling_layer])
            selected_index = combo_box.findText(filename, Qt.MatchFixedString)
            combo_box.setCurrentIndex(selected_index)

            self.render_widget.canvas.setExtent(get_current_layer_in(combo_box).extent())
            self.render_widget.canvas.refresh()