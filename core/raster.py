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

from PyQt4.QtGui import QMessageBox
from osgeo import gdal
from subprocess import call
from numpy.core.umath import isnan
from osgeo import gdalnumeric
import xml.etree.ElementTree as ET

from qgis.core import QgsRaster, QgsPoint
from qgis.utils import iface
from qgis.gui import QgsMessageBar

from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import wait_process


@wait_process()
def do_clipping_with_shape(target_file, shape, out_path):
    if out_path.endswith((".tif", ".TIF", ".img", ".IMG")):
        out_file = out_path
    else:
        filename, ext = os.path.splitext(os.path.basename(target_file))
        out_file = os.path.join(out_path, filename + "_clip" + ext)

    return_code = call('gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline "{}" -dstnodata 0 "{}" "{}"'
                       .format(shape, target_file, out_file), shell=True)
    if return_code == 0:  # successfully
        return out_file
    else:
        iface.messageBar().pushMessage("AcATaMa", "Error while clipping the raster file with shape.",
                                       level=QgsMessageBar.WARNING)


def get_extent(img_path):
    data = gdal.Open(img_path, gdal.GA_ReadOnly)
    geoTransform = data.GetGeoTransform()
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1] * data.RasterXSize
    miny = maxy + geoTransform[5] * data.RasterYSize
    del data

    return [round(minx), round(maxy), round(maxx), round(miny)]


def get_nodata_value(layer_file):
    extent = layer_file.extent()
    rows = layer_file.rasterUnitsPerPixelY()
    cols = layer_file.rasterUnitsPerPixelX()
    nodata_value = layer_file.dataProvider().block(1, extent, rows, cols).noDataValue()
    if isnan(nodata_value):
        nodata_value = -1
    return nodata_value


def get_color_table(layer, band_number, nodata=None):
    try:
        ds = gdal.Open(get_file_path_of_layer(layer))
    except:
        return False
    # set all negative values as None to nodata
    if nodata is not None:
        nodata = nodata if nodata >= 0 else None

    gdalBand = ds.GetRasterBand(band_number)
    colorTable = gdalBand.GetColorTable()
    if colorTable is None:
        iface.messageBar().pushMessage("AcATaMa", "Error, the raster file selected has no color table",
                                       level=QgsMessageBar.WARNING)
        return False

    count = colorTable.GetCount()
    color_table = {"Pixel Value":[], "Red":[], "Green":[], "Blue":[], "Alpha":[]}
    for index in range(count):
        if nodata is not None and index == int(nodata):
            continue
        color_table["Pixel Value"].append(index)
        colorEntry = list(colorTable.GetColorEntry(index))
        color_table["Red"].append(colorEntry[0])
        color_table["Green"].append(colorEntry[1])
        color_table["Blue"].append(colorEntry[2])
        color_table["Alpha"].append(colorEntry[3])

    return color_table


def get_singleband_pseudocolor(layer, band_number, nodata=None):
    current_style = layer.styleManager().currentStyle()
    layer_style = layer.styleManager().style(current_style)

    xml_style_str = layer_style.xmlData()
    xml_style = ET.fromstring(xml_style_str)

    items = xml_style.findall('pipe/rasterrenderer[@band="{}"]/rastershader/colorrampshader/item'.format(band_number))
    # check if items is empty or any pixel value (in color table) not is integer
    if not items or False in [i.get("value").lstrip('+-').isdigit() for i in items]:
        msg = "The layer selected \"{}\" {}doesn't have an appropiate color style for AcATaMa, " \
              "it must be singleband pseudocolor with integer values. " \
              "<a href='https://smbyc.bitbucket.io/qgisplugins/acatama/how_to_use/#types-of-thematic-rasters-accepted-in-acatama'>" \
              "See more</a>.".format(layer.name(), "in the band {} ".format(band_number) if layer.bandCount() > 1 else "")
        QMessageBox.warning(None, 'Error reading the pixel color style...', msg)
        return False

    color_table = {"Pixel Value": [], "Red": [], "Green": [], "Blue": [], "Alpha": []}
    for item in items:
        if nodata is not None and int(item.get("value")) == int(nodata):
            continue

        color_table["Pixel Value"].append(int(item.get("value")))

        item_color = item.get("color").lstrip('#')
        item_color = tuple(int(item_color[i:i+2], 16) for i in (0, 2 ,4))

        color_table["Red"].append(item_color[0])
        color_table["Green"].append(item_color[1])
        color_table["Blue"].append(item_color[2])
        color_table["Alpha"].append(int(item.get("alpha")))

    return color_table


def get_current_colors_style(layer, band_number=1, nodata=None):
    # with color table
    if layer.dataProvider().colorTable(band_number):
        return get_color_table(layer, band_number, nodata)
    # without color table
    else:
        return get_singleband_pseudocolor(layer, band_number, nodata)


class Raster():
    def __init__(self, file_selected_combo_box, band=1, nodata=None):
        from AcATaMa.utils.qgis_utils import get_current_file_path_in, get_current_layer_in
        self.file_path = get_current_file_path_in(file_selected_combo_box)
        self.qgs_layer = get_current_layer_in(file_selected_combo_box)
        self.band = band
        self.nodata = nodata if nodata != -1 else None

    def extent(self):
        return get_extent(self.file_path)

    def get_pixel_value_from_xy(self, x, y):
        return self.qgs_layer.dataProvider().identify(QgsPoint(x, y), QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_pixel_value_from_pnt(self, point):
        return self.qgs_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[self.band]

    def get_total_pixels_by_value(self, pixel_value):
        raster_numpy = gdalnumeric.LoadFile(self.file_path)
        return (raster_numpy == int(pixel_value)).sum()
