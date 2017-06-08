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
import traceback

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QCursor, QTableWidgetItem, QColor
from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QgsRasterLayer, QgsVectorLayer, QgsMapLayer
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from AcATaMa.core.raster import get_color_table


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
                iface.messageBar().pushMessage("AcATaMa", msg_error,
                                                level=QgsMessageBar.CRITICAL, duration=10)
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


def valid_file_selected_in(combo_box, combobox_name):
    try:
        get_layer_by_name(combo_box.currentText()).dataProvider().dataSourceUri()
        return True
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, please browse/select a valid file in "+combobox_name,
                                       level=QgsMessageBar.WARNING, duration=10)
        return False


def get_layer_by_name(layer_name):
    for layer in QgsMapLayerRegistry.instance().mapLayers().values():
        if layer.name() == layer_name:
            return layer


def get_current_file_path_in(combo_box):
    try:
        return unicode(get_layer_by_name(combo_box.currentText()).dataProvider().dataSourceUri().split('|layerid')[0])
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid file",
                                       level=QgsMessageBar.WARNING, duration=10)


def get_current_layer_in(combo_box):
    try:
        return get_layer_by_name(combo_box.currentText())
    except:
        iface.messageBar().pushMessage("AcATaMa", "Error, please select a valid file",
                                       level=QgsMessageBar.WARNING, duration=10)


def load_layer_in_qgis(file_path, layer_type):
    # Open in QGIS
    filename = os.path.splitext(os.path.basename(file_path))[0]
    if layer_type == "raster":
        layer = QgsRasterLayer(file_path, filename)
    if layer_type == "vector":
        layer = QgsVectorLayer(file_path, filename, "ogr")
    if layer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(layer)
    else:
        iface.messageBar().pushMessage("AcATaMa", "Error, {} is not a valid {} file!"
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


def fill_stratified_sampling_table(dockwidget):
    try:
        # check a valid current selected file
        get_layer_by_name(dockwidget.selectCategRaster_SRS.currentText()).dataProvider()
    except:
        # clear table
        dockwidget.table_pixel_colors_SRS.setRowCount(0)
        dockwidget.table_pixel_colors_SRS.setColumnCount(0)
        return

    color_table = get_color_table(get_current_file_path_in(dockwidget.selectCategRaster_SRS))
    if not color_table:
        # clear table
        dockwidget.table_pixel_colors_SRS.setRowCount(0)
        dockwidget.table_pixel_colors_SRS.setColumnCount(0)
        return

    column_count = len(color_table)
    row_count = len(color_table.values()[0])
    headers = ["Pixel Value", "Color", "No. samples"]

    # restore values saved for number of samples configured for selected categorical file
    if dockwidget.selectCategRaster_SRS.currentText() in dockwidget.srs_categorical_table.keys():
        samples_values = dockwidget.srs_categorical_table[dockwidget.selectCategRaster_SRS.currentText()]
    else:
        samples_values = [str(0)]*row_count

    dockwidget.table_pixel_colors_SRS.setRowCount(row_count)
    dockwidget.table_pixel_colors_SRS.setColumnCount(len(headers))

    # enter data onto Table
    for n, key in enumerate(headers):
        if key == "Pixel Value":
            for m, item in enumerate(color_table[key]):
                newitem = QTableWidgetItem(str(item))
                newitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                newitem.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                dockwidget.table_pixel_colors_SRS.setItem(m, n, newitem)
        if key == "Color":
            for m in range(row_count):
                newitem = QTableWidgetItem()
                newitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                newitem.setBackground(QColor(color_table["Red"][m],
                                             color_table["Green"][m],
                                             color_table["Blue"][m],
                                             color_table["Alpha"][m]))
                dockwidget.table_pixel_colors_SRS.setItem(m, n, newitem)
        if key == "No. samples":
            for m in range(row_count):
                newitem = QTableWidgetItem(samples_values[m])
                newitem.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                dockwidget.table_pixel_colors_SRS.setItem(m, n, newitem)

    # hidden row labels
    dockwidget.table_pixel_colors_SRS.verticalHeader().setVisible(False)
    # add Header
    dockwidget.table_pixel_colors_SRS.setHorizontalHeaderLabels(headers)
    # adjust size of Table
    dockwidget.table_pixel_colors_SRS.resizeColumnsToContents()
    dockwidget.table_pixel_colors_SRS.resizeRowsToContents()


def update_and_save_srs_data_table(dockwidget):
    number_of_samples = []
    try:
        for row in range(dockwidget.table_pixel_colors_SRS.rowCount()):
            number_of_samples.append(dockwidget.table_pixel_colors_SRS.item(row, 2).text())
    except:
        return
    dockwidget.srs_categorical_table[dockwidget.selectCategRaster_SRS.currentText()] = number_of_samples
