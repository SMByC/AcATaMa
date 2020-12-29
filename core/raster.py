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
from math import isnan
import xml.etree.ElementTree as ET

from qgis.core import QgsRaster, QgsPointXY
from qgis.PyQt.QtWidgets import QMessageBox

from AcATaMa.utils.others_utils import get_pixel_count_by_pixel_values


def get_nodata_value(layer, band=1):
    nodata_value = -1  # nan in the spinbox
    if layer is not None:
        nodata = layer.dataProvider().sourceNoDataValue(band)
        if not isnan(nodata) and (-1 <= nodata <= 999999):
            nodata_value = nodata

    return nodata_value


def get_color_table(layer, band=1, nodata=None):
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
        msg = "The selected layer \"{}\" {}doesn't have an appropriate colors/values style for AcATaMa, " \
              "it must be unique values or singleband pseudocolor with integer values. " \
              "<a href='https://smbyc.github.io/AcATaMa/#types-of-thematic-rasters-accepted-in-acatama'>" \
              "See more</a>.".format(layer.name(), "in the band {} ".format(band) if layer.bandCount() > 1 else "")
        QMessageBox.warning(None, 'Reading the symbology layer style...', msg)
        return

    color_table = {"Pixel Value": [], "Red": [], "Green": [], "Blue": [], "Alpha": []}
    for item in xml_style_items:
        if nodata is not None and int(item.get("value")) == int(nodata):
            continue

        color_table["Pixel Value"].append(int(item.get("value")))

        item_color = item.get("color").lstrip('#')
        item_color = tuple(int(item_color[i:i+2], 16) for i in (0, 2, 4))

        color_table["Red"].append(item_color[0])
        color_table["Green"].append(item_color[1])
        color_table["Blue"].append(item_color[2])
        color_table["Alpha"].append(int(item.get("alpha")))

    return color_table


class Raster(object):
    def __init__(self, file_selected_combo_box, band=1, nodata=None):
        from AcATaMa.utils.qgis_utils import get_current_file_path_in
        self.file_path = get_current_file_path_in(file_selected_combo_box)
        self.qgs_layer = file_selected_combo_box.currentLayer()
        self.band = band
        self.nodata = nodata if nodata != -1 else None
        self.pixel_counts_by_value = None

    def extent(self):
        return self.qgs_layer.extent()

    def get_pixel_value_from_xy(self, x, y):
        return self.qgs_layer.dataProvider().identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_pixel_value_from_pnt(self, point):
        return self.qgs_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_total_pixels_by_value(self, pixel_value):
        if self.pixel_counts_by_value is None:
            self.pixel_counts_by_value = get_pixel_count_by_pixel_values(self.qgs_layer, self.band, self.nodata)

        if pixel_value in self.pixel_counts_by_value:
            return self.pixel_counts_by_value[pixel_value]
