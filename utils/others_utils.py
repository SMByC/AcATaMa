# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2024 by Xavier C. Llano, SMByC
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
import re
import xml.etree.ElementTree as ET

from osgeo import gdal, gdal_array

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QProgressDialog, QApplication

from AcATaMa.utils.qgis_utils import get_file_path_of_layer
from AcATaMa.utils.system_utils import wait_process


def get_plugin_version(version_string):
    if isinstance(version_string, (int, float)):
        version_string = str(version_string)

    version = ''.join(['{:0>2}'.format(re.sub('\D', '', x)) for x in version_string.split('.')])

    if len(version) == 4:
        version += '00'

    return int(version)


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
# compute pixels count by pixel unique values

storage_pixel_count_by_pixel_values = {}  # storage the pixel/values computed by layer, band and nodata


def get_pixel_count_by_pixel_values(layer, band, pixel_values=None, nodata=None):
    """Meta function to choose the way to compute the pixel count by pixel values
    checking if dask library is available or not"""
    try:
        import dask
        return get_pixel_count_by_pixel_values_parallel(layer, band, pixel_values, nodata)
    except ImportError:
        return get_pixel_count_by_pixel_values_sequential(layer, band, pixel_values, nodata)


# --------------------------------------------------------------------------
# parallel processing

def chunks(l, n):
    """generate the sub-list of chunks of n-sizes from list l"""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def pixel_count_in_chunk(img_path, band, pixel_values, xoff, yoff, xsize, ysize):
    gdal_file = gdal.Open(img_path, gdal.GA_ReadOnly)
    chunk_narray = gdal_file.GetRasterBand(band).ReadAsArray(xoff, yoff, xsize, ysize)
    del gdal_file
    pixel_count = [0] * len(pixel_values)
    for idx, pixel_value in enumerate(pixel_values):
        pixel_count[idx] += (chunk_narray == int(pixel_value)).sum()
    return pixel_count


@wait_process
def get_pixel_count_by_pixel_values_parallel(layer, band, pixel_values=None, nodata=None):
    """Get the total pixel count for each pixel values"""
    import dask
    from AcATaMa.utils.progress_dialog import DaskQTProgressDialog

    if nodata in [None, "", "nan"] or np.isnan(nodata):
        nodata = "nan"
    elif float(nodata) == int(nodata):
        nodata = int(nodata)
    else:
        nodata = float(nodata)

    # check if it was already computed, then return it
    if (layer, band, set_nodata_format(nodata)) in storage_pixel_count_by_pixel_values:
        return storage_pixel_count_by_pixel_values[(layer, band, set_nodata_format(nodata))]

    # progress dialog
    progress = QProgressDialog('AcATaMa is counting the number of pixels for each thematic value.\n'
                               'Depending on the size of the image, it would take a few minutes.',
                               None, 0, 100)
    progress.setWindowTitle("AcATaMa - Counting unique values...")
    progress.setWindowModality(Qt.WindowModal)
    progress.setValue(0)
    progress.show()
    progress.update()
    QApplication.processEvents()

    if pixel_values is None:
        pixel_values = get_pixel_values(layer, band)

    # put nodata at the beginning, with the idea to include it for stopping
    # the counting when reaching the total pixels, delete it at the end
    if nodata != "nan":
        if nodata in pixel_values: pixel_values.remove(nodata)
        pixel_values.insert(0, nodata)

    # split the image in chunks, the 0,0 is left-upper corner
    layer_filepath = get_file_path_of_layer(layer)
    gdal_file = gdal.Open(layer_filepath, gdal.GA_ReadOnly)
    chunk_size_x, chunk_size_y = gdal_file.RasterXSize//10+1, gdal_file.RasterYSize//10+1
    data_in_chunks = []
    for y in chunks(range(gdal_file.RasterYSize), chunk_size_y):
        yoff = y[0]
        ysize = len(y)
        for x in chunks(range(gdal_file.RasterXSize), chunk_size_x):
            xoff = x[0]
            xsize = len(x)
            data_in_chunks.append((layer_filepath, band, pixel_values, xoff, yoff, xsize, ysize))
    del gdal_file

    # compute and merge all parallel process returns in one result
    with DaskQTProgressDialog(progress_dialog=progress):
        results = dask.compute(*[dask.delayed(pixel_count_in_chunk)(*chunk) for chunk in data_in_chunks])
    pixel_counts = np.sum(results, axis=0).tolist()

    if nodata != "nan":
        pixel_values.pop(0)
        pixel_counts.pop(0)

    progress.close()
    pairing_values_and_counts = dict(zip(pixel_values, pixel_counts))
    storage_pixel_count_by_pixel_values[(layer, band, set_nodata_format(nodata))] = pairing_values_and_counts
    return pairing_values_and_counts


# --------------------------------------------------------------------------
# sequential processing
total_count = 0


@wait_process
def get_pixel_count_by_pixel_values_sequential(layer, band, pixel_values=None, nodata=None):
    if nodata in [None, "", "nan"] or np.isnan(nodata):
        nodata = "nan"
    elif float(nodata) == int(nodata):
        nodata = int(nodata)
    else:
        nodata = float(nodata)

    # check if it was already computed, then return it
    if (layer, band, set_nodata_format(nodata)) in storage_pixel_count_by_pixel_values:
        return storage_pixel_count_by_pixel_values[(layer, band, set_nodata_format(nodata))]

    if pixel_values is None:
        pixel_values = get_pixel_values(layer, band)

    # put nodata at the beginning, with the idea to include it for stopping
    # the counting when reaching the total pixels, delete it at the end
    if nodata != "nan":
        if nodata in pixel_values: pixel_values.remove(nodata)
        pixel_values.insert(0, nodata)

    dataset = gdal_array.LoadFile(get_file_path_of_layer(layer))

    if len(dataset.shape) == 3:
        dataset = dataset[band - 1]

    max_pixels = dataset.shape[-1] * dataset.shape[-2]

    progress = QProgressDialog('AcATaMa is counting the number of pixels for each thematic value.\n'
                               'Depending on the size of the image, it would take a few minutes.',
                               None, 0, 100)
    progress.setWindowTitle("AcATaMa - Counting pixels by values...")
    progress.setWindowModality(Qt.WindowModal)
    progress.setValue(0)
    progress.show()
    QApplication.processEvents()

    global total_count
    total_count = 0

    def count_value(pixel_value):
        global total_count
        if total_count >= max_pixels:
            return 0
        count = np.count_nonzero(dataset == pixel_value)
        total_count += count
        progress.setValue(int(total_count * 100 / max_pixels))
        return count

    pixel_counts = [count_value(pixel_value) for pixel_value in pixel_values]

    if nodata != "nan":
        pixel_values.pop(0)
        pixel_counts.pop(0)

    progress.close()
    pairing_values_and_counts = dict(zip(pixel_values, pixel_counts))
    storage_pixel_count_by_pixel_values[(layer, band, set_nodata_format(nodata))] = pairing_values_and_counts
    return pairing_values_and_counts


# --------------------------------------------------------------------------
# set nodata format for the text line boxes

def set_nodata_format(value):
    if isinstance(value, str) and not value.strip():
        return ""
    value = float(value)
    if np.isnan(value):
        return str(value)
    if value <= -1000 or value >= 1000:
        return np.format_float_scientific(value)
    if value == int(value):
        return str(int(value))
    return str(value)
