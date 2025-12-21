# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2025 by Xavier C. Llano, SMByC
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
import numpy as np
from random import randrange
import xml.etree.ElementTree as ET

from qgis.core import QgsRaster, QgsPointXY, QgsPalettedRasterRenderer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMessageBox

from AcATaMa.utils.others_utils import get_pixel_count_by_pixel_values, wait_process


@wait_process
def auto_symbology_classification_render(layer, band):
    # get the unique values in the band
    rows = layer.height()
    cols = layer.width()
    provider = layer.dataProvider()
    bl = provider.block(band, provider.extent(), cols, rows)
    unique_values = list(set([bl.value(r, c) for r in range(rows) for c in range(cols)]))

    # fill categories
    categories = []
    for unique_value in unique_values:
        categories.append(QgsPalettedRasterRenderer.Class(
            unique_value, QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256)), str(unique_value)))

    renderer = QgsPalettedRasterRenderer(layer.dataProvider(), band, categories)
    layer.setRenderer(renderer)
    layer.triggerRepaint()


def get_nodata_value(layer, band=1):
    if layer and layer.isValid():
        return layer.dataProvider().sourceNoDataValue(band)
    else:
        return np.nan


def get_xml_style(layer, band):
    current_style = layer.styleManager().currentStyle()
    layer_style = layer.styleManager().style(current_style)
    xml_style_str = layer_style.xmlData()
    xml_style = ET.fromstring(xml_style_str)

    # for singleband_pseudocolor
    xml_style_items = xml_style.findall(
        'pipe/rasterrenderer[@band="{}"]/rastershader/colorrampshader/item'.format(band))
    if not xml_style_items:
        # for unique values
        xml_style_items = xml_style.findall('pipe/rasterrenderer[@band="{}"]/colorPalette/paletteEntry'.format(band))

    check_int_values = [int(float(xml_item.get("value"))) == float(xml_item.get("value")) for xml_item in
                        xml_style_items]

    if not xml_style_items or False in check_int_values:
        msg = "The selected layer \"{layer}\"{band} doesn't have an appropriate symbology for AcATaMa, " \
              "it must be set with unique/exact colors-values. " \
              "<a href='https://smbyc.github.io/AcATaMa/#types-of-thematic-rasters-accepted-in-acatama'>" \
              "See more</a>.<br/><br/>" \
              "Allow AcATaMa apply an automatic classification symbology to this layer{band}?" \
            .format(layer=layer.name(), band=" in the band {}".format(band) if layer.bandCount() > 1 else "")
        reply = QMessageBox.question(None, 'Reading the symbology layer style...', msg, QMessageBox.Apply, QMessageBox.Cancel)
        if reply == QMessageBox.Apply:
            auto_symbology_classification_render(layer, band)
            return get_xml_style(layer, band)
        else:
            return
    xml_style_items = sorted(xml_style_items, key=lambda x: int(x.get("value")))
    return xml_style_items


def get_values_and_colors_table(layer, band=1, nodata=None):
    xml_style_items = get_xml_style(layer, band)
    if not xml_style_items:
        return

    values_and_colors_table = {"Pixel Value": [], "Red": [], "Green": [], "Blue": [], "Alpha": []}
    for item in xml_style_items:
        if nodata is not None and int(item.get("value")) == nodata:
            continue

        values_and_colors_table["Pixel Value"].append(int(item.get("value")))

        item_color = item.get("color").lstrip('#')
        item_color = tuple(int(item_color[i:i+2], 16) for i in (0, 2, 4))

        values_and_colors_table["Red"].append(item_color[0])
        values_and_colors_table["Green"].append(item_color[1])
        values_and_colors_table["Blue"].append(item_color[2])
        values_and_colors_table["Alpha"].append(int(item.get("alpha")))

    return values_and_colors_table


class Map(object):
    def __init__(self, file_selected_combo_box, band=1, nodata=None):
        from AcATaMa.utils.qgis_utils import get_current_file_path_in
        self.file_path = get_current_file_path_in(file_selected_combo_box)
        self.qgs_layer = file_selected_combo_box.currentLayer()
        self.band = band
        self.nodata = nodata

    def extent(self):
        return self.qgs_layer.extent()

    def get_pixel_value_from_xy(self, x, y):
        return self.qgs_layer.dataProvider().identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_pixel_value_from_pnt(self, point):
        return self.qgs_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_total_pixels_by_value(self, pixel_value):
        pixel_counts_by_value = get_pixel_count_by_pixel_values(self.qgs_layer, self.band, None, self.nodata)
        if pixel_value in pixel_counts_by_value:
            return pixel_counts_by_value[pixel_value]

    def get_pixel_centroid(self, x, y):
        if x < self.extent().xMinimum() or x > self.extent().xMaximum() or y < self.extent().yMinimum() or y > self.extent().yMaximum():
            return None, None

        pixel_width = self.qgs_layer.rasterUnitsPerPixelX()
        pixel_height = self.qgs_layer.rasterUnitsPerPixelY()
        x_min = self.extent().xMinimum()
        y_max = self.extent().yMaximum()
        col = int((x - x_min) / pixel_width)
        row = int((y_max - y) / pixel_height)

        x_centroid = x_min + (col + 0.5) * pixel_width
        y_centroid = y_max - (row + 0.5) * pixel_height
        return x_centroid, y_centroid