# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2019 by Xavier Corredor Llano, SMByC
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

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsRendererPropertiesDialog, QgsRendererRasterPropertiesWidget
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, Qgis, QgsStyle, QgsMapLayer
from qgis.utils import iface


def get_file_path_of_layer(layer):
    if layer and layer.isValid():
        return os.path.realpath(layer.source().split("|layername")[0])
    return ""


def valid_file_selected_in(combo_box, combobox_name=False):
    if combo_box.currentLayer() is None:
        return False
    if combo_box.currentLayer().isValid():
        return True
    else:
        if combobox_name:
            iface.messageBar().pushMessage("AcATaMa", "Error, please browse/select a valid file in "
                                           + combobox_name, level=Qgis.Warning)
        combo_box.setCurrentIndex(-1)
        return False


def get_layer_by_name(layer_name):
    layer = QgsProject.instance().mapLayersByName(layer_name)
    if layer:
        return layer[0]


def get_current_file_path_in(combo_box, show_message=True):
    file_path = get_file_path_of_layer(combo_box.currentLayer())
    if os.path.isfile(file_path):
        return file_path
    elif show_message:
        iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid file", level=Qgis.Warning)
    return None


def load_and_select_filepath_in(combo_box, file_path, layer_name=None):
    if not layer_name:
        layer_name = os.path.splitext(os.path.basename(file_path))[0]
    layer = get_layer_by_name(layer_name)
    # load
    if not layer:
        load_layer(file_path, name=layer_name)
    # select the sampling file in combobox
    selected_index = combo_box.findText(layer_name, Qt.MatchFixedString)
    combo_box.setCurrentIndex(selected_index)

    return get_layer_by_name(layer_name)


def add_layer(layer, add_to_legend=True):
    QgsProject.instance().addMapLayer(layer, add_to_legend)


def load_layer(file_path, name=None, add_to_legend=True):
    # first unload layer from qgis if exists
    unload_layer(file_path)

    name = name or os.path.splitext(os.path.basename(file_path))[0]
    # vector
    qgslayer = QgsVectorLayer(file_path, name, "ogr")
    if not qgslayer.isValid():
        # raster
        qgslayer = QgsRasterLayer(file_path, name, "gdal")

    # load
    if qgslayer.isValid():
        add_layer(qgslayer, add_to_legend)
    else:
        iface.messageBar().pushMessage("AcATaMa", "Could not load layer: {}".format(file_path))

    return qgslayer


def unload_layer(layer_path):
    layers_loaded = QgsProject.instance().mapLayers().values()
    for layer_loaded in layers_loaded:
        if layer_path == get_file_path_of_layer(layer_loaded):
            QgsProject.instance().removeMapLayer(layer_loaded.id())


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'classification_style_editor.ui'))


class StyleEditorDialog(QDialog, FORM_CLASS):
    def __init__(self, layer, canvas, parent=None):
        QDialog.__init__(self)
        self.setupUi(self)
        self.layer = layer

        self.setWindowTitle("{} - style editor".format(self.layer.name()))

        if self.layer.type() == QgsMapLayer.VectorLayer:
            self.StyleEditorWidget = QgsRendererPropertiesDialog(self.layer, QgsStyle(), True, parent)

        if self.layer.type() == QgsMapLayer.RasterLayer:
            self.StyleEditorWidget = QgsRendererRasterPropertiesWidget(self.layer, canvas, parent)

        self.scrollArea.setWidget(self.StyleEditorWidget)

        self.DialogButtons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.DialogButtons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.DialogButtons.button(QDialogButtonBox.Apply).clicked.connect(self.apply)

    def apply(self):
        self.StyleEditorWidget.apply()
        self.layer.triggerRepaint()
