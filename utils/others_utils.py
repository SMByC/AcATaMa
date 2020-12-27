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
import numpy as np
import multiprocessing
import xml.etree.ElementTree as ET
from osgeo import gdal, gdalnumeric

from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import wait_process


def mask(input_list, boolean_mask):
    """Apply boolean mask to input list

    Args:
        input_list (list): Input list for apply mask
        boolean_mask (list): The boolean mask list

    Examples:
        >>> mask(['A','B','C','D'], [1,0,1,0])
        ['A', 'C']
    """
    return [i for i, b in zip(input_list, boolean_mask) if b]

# --------------------------------------------------------------------------


def get_pixel_values(layer, band):
    current_style = layer.styleManager().currentStyle()
    layer_style = layer.styleManager().style(current_style)
    xml_style_str = layer_style.xmlData()
    xml_style = ET.fromstring(xml_style_str)

    # for singleband_pseudocolor
    items = xml_style.findall('pipe/rasterrenderer[@band="{}"]/rastershader/colorrampshader/item'.format(band))
    if not items:
        # for unique values
        items = xml_style.findall('pipe/rasterrenderer[@band="{}"]/colorPalette/paletteEntry'.format(band))

    pixel_values = []
    for item in items:
        pixel_values.append(int(item.get("value")))
    return pixel_values

# --------------------------------------------------------------------------


def chunks(l, n):
    """generate the sub-list of chunks of n-sizes from list l"""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def pixel_count_in_chunk(args):
    img_path, band, pixel_values, xoff, yoff, xsize, ysize = args
    pixel_count = [0] * len(pixel_values)
    gdal_file = gdal.Open(img_path, gdal.GA_ReadOnly)

    chunk_narray = gdal_file.GetRasterBand(band).ReadAsArray(xoff, yoff, xsize, ysize).astype(np.int)

    for idx, pixel_value in enumerate(pixel_values):
        pixel_count[idx] += (chunk_narray == int(pixel_value)).sum()
    return pixel_count


@wait_process
def get_pixel_count_by_pixel_values_parallel(layer, band, pixel_values=None):
    """Get the total pixel count for each pixel values"""

    if pixel_values is None:
        pixel_values = get_pixel_values(layer, band)

    # split the image in chunks, the 0,0 is left-upper corner
    gdal_file = gdal.Open(get_file_path_of_layer(layer), gdal.GA_ReadOnly)
    chunk_size = 1000
    input_data = []
    for y in chunks(range(gdal_file.RasterYSize), chunk_size):
        yoff = y[0]
        ysize = len(y)
        for x in chunks(range(gdal_file.RasterXSize), chunk_size):
            xoff = x[0]
            xsize = len(x)

            input_data.append((get_file_path_of_layer(layer), band, pixel_values, xoff, yoff, xsize, ysize))

    # compute and merge all parallel process returns in one result
    with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
        imap_it = pool.imap(pixel_count_in_chunk, input_data)
        pixel_counts = np.sum([proc for proc in imap_it], axis=0).tolist()
        return dict(zip(pixel_values, pixel_counts))

# --------------------------------------------------------------------------


def calc_pixel_count_by_value_lineal(layer, band, pixel_values):
    raster_numpy = gdalnumeric.LoadFile(get_file_path_of_layer(layer))
    if len(raster_numpy.shape) == 3:
        raster_numpy = raster_numpy[band-1]

    pixel_counts = [np.count_nonzero(raster_numpy == pixel_value)
                    for pixel_value in pixel_values]

    return pixel_counts


@wait_process
def get_pixel_count_by_pixel_values(layer, band, pixel_values=None):
    if pixel_values is None:
        pixel_values = get_pixel_values(layer, band)

    pixel_counts = calc_pixel_count_by_value_lineal(layer, band, pixel_values)

    return dict(zip(pixel_values, pixel_counts))
