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
import numpy as np
from subprocess import call

from qgis.utils import iface
from qgis.gui import QgsMessageBar


def do_clipping_with_shape(target_file, shape, out_path):
    filename, ext = os.path.splitext(os.path.basename(target_file))
    out_file = os.path.join(out_path, filename + "_clip" + ext)

    return_code = call('gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline "{}" -dstnodata 0 "{}" "{}"'
                       .format(shape, target_file, out_file), shell=True)
    if return_code == 0:  # successfully
        return out_file
    else:
        iface.messageBar().pushMessage("AcATaMa", "Error while clipping the raster file with shape.",
                                       level=QgsMessageBar.WARNING, duration=20)


def get_extent(img_path):
    data = gdal.Open(img_path, gdal.GA_ReadOnly)
    geoTransform = data.GetGeoTransform()
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1] * data.RasterXSize
    miny = maxy + geoTransform[5] * data.RasterYSize
    del data

    return [round(minx), round(maxy), round(maxx), round(miny)]


def get_color_table(raster_path, band_number=1):
    ds = gdal.Open(str(raster_path))

    gdalBand = ds.GetRasterBand(band_number)
    colorTable = gdalBand.GetColorTable()
    if colorTable is None:
        print "Image has no color table"
        return

    count = colorTable.GetCount()
    color_table = {"Pixel Value":[], "Red":[], "Green":[], "Blue":[], "Alpha":[]}
    for index in range(count):
        color_table["Pixel Value"].append(index)
        colorEntry = list(colorTable.GetColorEntry(index))
        color_table["Red"].append(colorEntry[0])
        color_table["Green"].append(colorEntry[1])
        color_table["Blue"].append(colorEntry[2])
        color_table["Alpha"].append(colorEntry[3])

    return color_table