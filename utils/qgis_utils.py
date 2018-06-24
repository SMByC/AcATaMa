# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2018 by Xavier Corredor Llano, SMByC
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

from PyQt4.QtCore import Qt
from qgis.core import QgsMapLayerRegistry, QgsRasterLayer, QgsVectorLayer
from qgis.gui import QgsMessageBar
from qgis.utils import iface


def valid_file_selected_in(combo_box, combobox_name=False):
    try:
        combo_box.currentLayer().dataProvider().dataSourceUri()
        return True
    except:
        # if not empty (valid selected) and combobox name given
        if combo_box.currentText() and combobox_name:
            iface.messageBar().pushMessage("AcATaMa", "Error, please browse/select a valid file in "
                                           + combobox_name, level=QgsMessageBar.WARNING)

        combo_box.setCurrentIndex(-1)
        return False


def get_layer_by_name(layer_name):
    layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)
    if layer:
        return layer[0]


def get_file_path_of_layer(layer):
    try:
        return unicode(layer.dataProvider().dataSourceUri().split('|layerid')[0])
    except:
        return None


def get_current_file_path_in(combo_box, show_message=True):
    try:
        file_path = unicode(combo_box.currentLayer().dataProvider().dataSourceUri().split('|layerid')[0])
        if os.path.isfile(file_path):
            return file_path
    except:
        if show_message:
            iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid file",
                                           level=QgsMessageBar.WARNING)
    return None


def load_and_select_filepath_in(combo_box, file_path, layer_type="any"):
    filename = os.path.splitext(os.path.basename(file_path))[0]
    layer = get_layer_by_name(filename)
    if not layer:
        # load to qgis and update combobox list
        load_layer_in_qgis(file_path, layer_type)
    # select the sampling file in combobox
    selected_index = combo_box.findText(filename, Qt.MatchFixedString)
    combo_box.setCurrentIndex(selected_index)

    return get_layer_by_name(filename)


def load_layer_in_qgis(file_path, layer_type):
    # first unload layer from qgis if exists
    unload_layer_in_qgis(file_path)
    # create layer
    filename = os.path.splitext(os.path.basename(file_path))[0]
    if layer_type == "raster":
        layer = QgsRasterLayer(file_path, filename)
    if layer_type == "vector":
        layer = QgsVectorLayer(file_path, filename, "ogr")
    if layer_type == "any":
        if file_path.endswith((".tif", ".TIF", ".img", ".IMG")):
            layer = QgsRasterLayer(file_path, filename)
        if file_path.endswith((".gpkg", ".GPKG", ".shp", ".SHP")):
            layer = QgsVectorLayer(file_path, filename, "ogr")
    # load
    if layer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(layer)
    else:
        iface.messageBar().pushMessage("AcATaMa", "Error, {} is not a valid {} file!"
                                       .format(os.path.basename(file_path), layer_type))
    return filename


def unload_layer_in_qgis(layer_path):
    layers_loaded = QgsMapLayerRegistry.instance().mapLayers().values()
    for layer_loaded in layers_loaded:
        if hasattr(layer_loaded, "dataProvider"):
            if layer_path == layer_loaded.dataProvider().dataSourceUri().split('|layerid')[0]:
                QgsMapLayerRegistry.instance().removeMapLayer(layer_loaded)


