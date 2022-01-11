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
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QWidget, QGridLayout, QFileDialog
from qgis.PyQt.QtCore import QSettings, pyqtSlot, QTimer, Qt
from qgis.core import QgsGeometry, QgsMapLayerProxyModel, QgsWkbTypes, QgsPoint
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsRubberBand, QgsVertexMarker
from qgis.utils import iface

from AcATaMa.utils.qgis_utils import load_and_select_filepath_in, StyleEditorDialog
from AcATaMa.utils.system_utils import block_signals_to


class PanAndZoomPointTool(QgsMapToolPan):
    def __init__(self, render_widget):
        QgsMapToolPan.__init__(self, render_widget.canvas)
        self.render_widget = render_widget

    def update_canvas(self):
        self.render_widget.parent_view.canvas_changed()

    def canvasReleaseEvent(self, event):
        QgsMapToolPan.canvasReleaseEvent(self, event)
        self.update_canvas()

    def wheelEvent(self, event):
        QgsMapToolPan.wheelEvent(self, event)
        QTimer.singleShot(10, self.update_canvas)

    def keyReleaseEvent(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Right, Qt.Key_Left, Qt.Key_PageUp, Qt.Key_PageDown]:
            QTimer.singleShot(10, self.update_canvas)


class Marker(object):
    def __init__(self, canvas):
        self.marker = None
        self.canvas = canvas

    def show(self, in_point):
        """Show marker for the respective view widget"""
        if self.marker is None:
            self.marker = QgsVertexMarker(self.canvas)
            self.marker.setIconSize(18)
            self.marker.setPenWidth(2)
            self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.marker.setCenter(in_point.QgsPnt)
        self.marker.updatePosition()

    def remove(self):
        """Remove marker for the respective view widget"""
        self.canvas.scene().removeItem(self.marker)
        self.marker = None

    def highlight(self):
        curr_ext = self.canvas.extent()

        left_point = QgsPoint(curr_ext.xMinimum(), curr_ext.center().y())
        right_point = QgsPoint(curr_ext.xMaximum(), curr_ext.center().y())

        top_point = QgsPoint(curr_ext.center().x(), curr_ext.yMaximum())
        bottom_point = QgsPoint(curr_ext.center().x(), curr_ext.yMinimum())

        horiz_line = QgsGeometry.fromPolyline([left_point, right_point])
        vert_line = QgsGeometry.fromPolyline([top_point, bottom_point])

        cross_rb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        cross_rb.setColor(QColor(255, 0, 0))
        cross_rb.reset(QgsWkbTypes.LineGeometry)
        cross_rb.addGeometry(horiz_line, None)
        cross_rb.addGeometry(vert_line, None)

        QTimer.singleShot(600, cross_rb.reset)
        self.canvas.refresh()


class RenderWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi()
        self.layer = None
        self.marker = Marker(self.canvas)

    def setupUi(self):
        gridLayout = QGridLayout(self)
        gridLayout.setContentsMargins(0, 0, 0, 0)
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(QColor(255, 255, 255))
        self.canvas.setStyleSheet("border: 0px;")
        settings = QSettings()
        self.canvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type=bool))
        self.setMinimumSize(15, 15)
        # mouse action pan and zoom
        self.pan_zoom_tool = PanAndZoomPointTool(self)
        self.canvas.setMapTool(self.pan_zoom_tool)

        gridLayout.addWidget(self.canvas)

    def render_layer(self, layer):
        with block_signals_to(self):
            # set the CRS of the canvas view based on sampling layer
            sampling_crs = self.parent_view.sampling_layer.crs()
            self.canvas.setDestinationCrs(sampling_crs)
            # set the sampling over the layer to view
            self.canvas.setLayers([self.parent_view.sampling_layer, layer])
            # set init extent from other view if any is activated else set layer extent
            from AcATaMa.gui.response_design_window import ResponseDesignWindow
            others_view = [(view_widget.render_widget.canvas.extent(), view_widget.current_scale_factor) for view_widget
                           in ResponseDesignWindow.view_widgets if not view_widget.render_widget.canvas.extent().isEmpty()]
            if others_view:
                extent, scale = others_view[0]
                extent.scale(1 / scale)
                self.set_extents_and_scalefactor(extent)
            elif ResponseDesignWindow.current_sample:
                ResponseDesignWindow.current_sample.fit_to(
                    self.parent_view, ResponseDesignWindow.instance.radiusFitToSample.value())

            self.canvas.refresh()
            self.layer = layer
            # show marker
            if ResponseDesignWindow.current_sample:
                self.marker.show(ResponseDesignWindow.current_sample)

    def set_extents_and_scalefactor(self, extent):
        with block_signals_to(self.canvas):
            self.canvas.setExtent(extent)
            self.canvas.zoomByFactor(self.parent_view.scaleFactor.value())
            if self.marker.marker:
                self.marker.marker.updatePosition()

    def layer_style_editor(self):
        style_editor_dlg = StyleEditorDialog(self.layer, self.canvas, self.parent_view)
        if style_editor_dlg.exec_():
            style_editor_dlg.apply()


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'response_design_view_widget.ui'))


class LabelingViewWidget(QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.id = None
        self.is_active = False
        self.current_scale_factor = 1.0
        self.qgs_main_canvas = iface.mapCanvas()
        self.setupUi(self)
        # init as unactivated render widget for new instances
        self.disable()

    def setup_view_widget(self, sampling_layer):
        self.sampling_layer = sampling_layer
        self.render_widget.parent_view = self
        # set properties to QgsMapLayerComboBox
        self.QCBox_RenderFile.setCurrentIndex(-1)
        self.QCBox_RenderFile.setFilters(QgsMapLayerProxyModel.All)
        # ignore and not show the sampling layer
        self.QCBox_RenderFile.setExceptedLayerList([self.sampling_layer])
        # handle connect layer selection with render canvas
        self.QCBox_RenderFile.currentIndexChanged.connect(lambda: self.set_render_layer(self.QCBox_RenderFile.currentLayer()))
        # call to browse the render file
        self.QCBox_browseRenderFile.clicked.connect(lambda: self.browser_dialog_to_load_file(
            self.QCBox_RenderFile,
            dialog_title=self.tr("Select the file for this view"),
            file_filters=self.tr("Raster or vector files (*.tif *.img *.gpkg *.shp);;All files (*.*)")))
        # zoom scale factor
        self.scaleFactor.valueChanged.connect(self.scalefactor_changed)
        # edit layer properties
        self.layerStyleEditor.clicked.connect(self.render_widget.layer_style_editor)

    def enable(self):
        with block_signals_to(self.render_widget):
            # activate some parts of this view
            self.QLabel_ViewName.setEnabled(True)
            self.render_widget.setEnabled(True)
            self.scaleFactorLabel.setEnabled(True)
            self.scaleFactor.setEnabled(True)
            self.layerStyleEditor.setEnabled(True)
            self.render_widget.canvas.setCanvasColor(QColor(255, 255, 255))
            # set status for view widget
            self.is_active = True

    def disable(self):
        with block_signals_to(self.render_widget):
            self.render_widget.canvas.setLayers([])
            self.render_widget.marker.remove()
            self.render_widget.canvas.clearCache()
            self.render_widget.canvas.refresh()
            self.render_widget.layer = None
            # deactivate some parts of this view
            self.QLabel_ViewName.setDisabled(True)
            self.render_widget.setDisabled(True)
            self.scaleFactorLabel.setDisabled(True)
            self.scaleFactor.setDisabled(True)
            self.layerStyleEditor.setDisabled(True)
            self.render_widget.canvas.setCanvasColor(QColor(245, 245, 245))
            # set status for view widget
            self.is_active = False

    def set_render_layer(self, layer):
        if not layer:
            self.disable()
            return

        self.enable()
        self.render_widget.render_layer(layer)

    @pyqtSlot()
    def browser_dialog_to_load_file(self, combo_box, dialog_title, file_filters):
        file_path, _ = QFileDialog.getOpenFileName(self, dialog_title, "", file_filters)
        if file_path != '' and os.path.isfile(file_path):
            # load to qgis and update combobox list
            load_and_select_filepath_in(combo_box, file_path)

            self.set_render_layer(combo_box.currentLayer())

    @pyqtSlot()
    def canvas_changed(self):
        if self.is_active:
            from AcATaMa.gui.response_design_window import ResponseDesignWindow
            view_extent = self.render_widget.canvas.extent()
            view_extent.scale(1/self.current_scale_factor)

            # set extent and scale factor for all view activated except this view
            for view_widget in ResponseDesignWindow.view_widgets:
                if view_widget.is_active and view_widget != self:
                    view_widget.render_widget.set_extents_and_scalefactor(view_extent)

    @pyqtSlot()
    def scalefactor_changed(self):
        # adjust view with the original extent (scale factor=1)
        # and with the new scale factor
        view_extent = self.render_widget.canvas.extent()
        view_extent.scale(1 / self.current_scale_factor)
        self.render_widget.set_extents_and_scalefactor(view_extent)
        # save the new scale factor
        self.current_scale_factor = self.scaleFactor.value()