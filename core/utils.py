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
import gdal
import traceback
from subprocess import call

from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtCore import Qt
from qgis.gui import QgsMessageBar
from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QgsRasterLayer, QgsVectorLayer, QgsMapLayer
from qgis.utils import iface


def error_handler():
    def decorate(f):
        def applicator(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception as e:
                # restore mouse
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
                # message in status bar
                msg_error = "An error has occurred in AcATaMa plugin. " \
                            "See more in Qgis log messages panel."
                iface.messageBar().pushMessage("Error", msg_error,
                                                    level=QgsMessageBar.CRITICAL, duration=0)
                # message in log
                msg_error = "\n################## ERROR IN ACATAMA PLUGIN:\n"
                msg_error += traceback.format_exc()
                msg_error += "\nPlease report the error in:\n" \
                             "\thttps://bitbucket.org/SMBYC/qgisplugin-acatama/issues"
                msg_error += "\n################## END REPORT"
                QgsMessageLog.logMessage(msg_error)
        return applicator
    return decorate


def wait_process():
    def decorate(f):
        def applicator(*args, **kwargs):
            # mouse wait
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            # do
            f(*args, **kwargs)
            # restore mouse
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
        return applicator
    return decorate


def get_layer_by_name(layer_name):
    for layer in iface.mapCanvas().layers():
        if layer.name() == layer_name:
            return layer


def get_current_file_path_in(combo_box):
    try:
        return unicode(get_layer_by_name(combo_box.currentText()).dataProvider().dataSourceUri().split('|layerid')[0])
    except:
        iface.messageBar().pushMessage("Error", "Please select a valid file", level=QgsMessageBar.WARNING)


def open_layer_in_qgis(file_path, layer_type):
    # Open in QGIS
    filename = os.path.splitext(os.path.basename(file_path))[0]
    if layer_type == "raster":
        layer = QgsRasterLayer(file_path, filename)
    if layer_type == "vector":
        layer = QgsVectorLayer(file_path, filename, "ogr")
    if layer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(layer)
    else:
        iface.messageBar().pushMessage("Error", "{} is not a valid {} file!"
                                       .format(os.path.basename(file_path), layer_type))
    return filename


def unload_layer_in_qgis(layer_path):
    layers_loaded = QgsMapLayerRegistry.instance().mapLayers().values()
    for layer_loaded in layers_loaded:
        if layer_path == layer_loaded.dataProvider().dataSourceUri().split('|layerid')[0]:
            QgsMapLayerRegistry.instance().removeMapLayer(layer_loaded)


def update_layers_list(combo_box, layer_type="any"):
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


def do_clipping_with_shape(target_file, shape, out_path):
    filename, ext = os.path.splitext(os.path.basename(target_file))
    out_file = os.path.join(out_path, filename + "_clip" + ext)

    return_code = call('gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline "{}" -dstnodata 0 "{}" "{}"'
                       .format(shape, target_file, out_file), shell=True)
    if return_code == 0:  # successfully
        return out_file
    else:
        iface.messageBar().pushMessage("Error", "While clipping the thematic raster.", level=QgsMessageBar.WARNING)


def get_extent(img_path):
    data = gdal.Open(img_path, gdal.GA_ReadOnly)
    geoTransform = data.GetGeoTransform()
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1] * data.RasterXSize
    miny = maxy + geoTransform[5] * data.RasterYSize
    del data

    return [round(minx), round(maxy), round(maxx), round(miny)]