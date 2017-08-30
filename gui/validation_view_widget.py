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
from PyQt4.QtCore import QSettings
from qgis.gui import QgsMapCanvas, QgsMapCanvasLayer, QgsMapToolPan
from qgis.utils import iface

from AcATaMa.core.dockwidget import update_layers_list, get_current_layer_in


class RenderWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi()

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
            return
        self.canvas.setExtent(layer.extent())
        self.canvas.setLayerSet([QgsMapCanvasLayer(layer)])

        self.extents_changed()

    def extents_changed(self):
        self.canvas.setExtent(iface.mapCanvas().extent())
        self.canvas.zoomByFactor(self.parent().scaleFactor.value())

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'validation_view_widget.ui'))


class ValidationViewWidget(QtGui.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.canvas = iface.mapCanvas()
        self.setupUi(self)
        self.is_active = False

        # render layer actions
        update_layers_list(self.selectRenderFile, "any")
        # handle connect when the list of layers changed
        self.canvas.layersChanged.connect(lambda: update_layers_list(self.selectRenderFile, "any"))
        self.selectRenderFile.currentIndexChanged.connect(
            lambda: self.render_widget.render_layer(get_current_layer_in(self.selectRenderFile)))

        # zoom factor
        self.scaleFactor.valueChanged.connect(self.render_widget.extents_changed)

