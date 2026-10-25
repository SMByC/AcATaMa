"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2026 by Xavier C. Llano, SMByC
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

import hashlib
import xml.etree.ElementTree as ET  # nosec B405 - parses only QGIS-generated style XML, not untrusted input
from random import randrange

import numpy as np
from osgeo import gdal
from qgis.core import Qgis, QgsPalettedRasterRenderer, QgsPointXY, QgsRasterRange
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMessageBox

from AcATaMa.utils.others_utils import (
    get_layer_data,
    get_pixel_count_by_pixel_values,
    get_unique_values,
    wait_process,
)


@wait_process
def auto_symbology_classification_render(layer, band):
    # get the unique values in the band
    unique_values = get_unique_values(layer, band)

    # fill categories
    categories = []
    for unique_value in unique_values:
        color = QColor(randrange(0, 256), randrange(0, 256), randrange(0, 256))  # nosec B311 - display colors
        categories.append(QgsPalettedRasterRenderer.Class(unique_value, color, str(unique_value)))

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
    xml_style = ET.fromstring(xml_style_str)  # nosec B314 - XML serialized in-process by QGIS, not external input

    # for singleband_pseudocolor
    xml_style_items = xml_style.findall(f'pipe/rasterrenderer[@band="{band}"]/rastershader/colorrampshader/item')
    if not xml_style_items:
        # for unique values
        xml_style_items = xml_style.findall(f'pipe/rasterrenderer[@band="{band}"]/colorPalette/paletteEntry')

    check_int_values = [
        int(float(xml_item.get("value"))) == float(xml_item.get("value")) for xml_item in xml_style_items
    ]

    if not xml_style_items or False in check_int_values:
        msg = (
            'The selected layer "{layer}"{band} doesn\'t have an appropriate symbology for AcATaMa, '
            "it must be set with unique/exact colors-values. "
            "<a href='https://smbyc.github.io/AcATaMa/#types-of-thematic-rasters-accepted-in-acatama'>"
            "See more</a>.<br/><br/>"
            "Allow AcATaMa apply an automatic classification symbology to this layer{band}?".format(
                layer=layer.name(), band=f" in the band {band}" if layer.bandCount() > 1 else ""
            )
        )
        reply = QMessageBox.question(
            None,
            "Reading the symbology layer style...",
            msg,
            QMessageBox.StandardButton.Apply,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Apply:
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

        item_color = item.get("color").lstrip("#")
        item_color = tuple(int(item_color[i : i + 2], 16) for i in (0, 2, 4))

        values_and_colors_table["Red"].append(item_color[0])
        values_and_colors_table["Green"].append(item_color[1])
        values_and_colors_table["Blue"].append(item_color[2])
        values_and_colors_table["Alpha"].append(int(item.get("alpha")))

    return values_and_colors_table


# version of the fingerprints, those of other versions are not comparable
MAP_FINGERPRINT_VERSION = "v1"
# storage the fingerprint of the data of a band of a layer (size, geotransform and pixel values) with the data
# of the layer (source and file modification) when it was computed
storage_map_fingerprints = {}


@wait_process
def get_map_fingerprint(layer, band):
    """Identification of a band of a raster by its pixel values and georeferencing, not by its file (that can be
    moved or renamed): size, geotransform, CRS and a hash of the pixel values of the band, as little endian 64-bit
    integers (or floats) so they don't depend on the data type (the GDAL checksum is not used, for values smaller
    than 7 it only depends on the pixel counts by value). None if it can't be read"""
    from AcATaMa.utils.qgis_utils import get_source_from

    layer_data = get_layer_data(layer, band)
    stored = storage_map_fingerprints.get((layer, band))
    if stored is None or stored[0] is None or stored[0] != layer_data:
        try:
            dataset = gdal.Open(get_source_from(layer), gdal.GA_ReadOnly)
            raster_band = dataset.GetRasterBand(band)
            width, height = dataset.RasterXSize, dataset.RasterYSize
            pixel_values_hash = hashlib.blake2b(digest_size=16)
            rows_by_block = max(1, 2**22 // width)
            for y in range(0, height, rows_by_block):
                block = raster_band.ReadAsArray(0, y, width, min(rows_by_block, height - y))
                canonical_type = "<i8" if np.issubdtype(block.dtype, np.integer) else "<f8"
                pixel_values_hash.update(block.astype(canonical_type).tobytes())
            geotransform = ",".join(f"{value:.12g}" for value in dataset.GetGeoTransform())
            dataset = None
        except Exception:
            return None
        storage_map_fingerprints[(layer, band)] = (
            layer_data,
            f"{width}x{height} {geotransform} {pixel_values_hash.hexdigest()}",
        )
    # the CRS of the layer can be changed in QGIS without changing its file, it is identified by its definition
    # when it has no authority identifier or a user one (whose definition can be changed)
    crs = layer.crs()
    crs_id = crs.authid()
    if not crs_id or crs_id.upper().startswith("USER:"):
        crs_id = hashlib.blake2b(crs.toWkt().encode(), digest_size=8).hexdigest()
    return f"{MAP_FINGERPRINT_VERSION} {storage_map_fingerprints[(layer, band)][1]} {crs_id}"


def get_source_nodata(layer, band):
    """No data value of the layer used by the provider (its pixels can't be sampled), None if there is not"""
    provider = layer.dataProvider()
    if provider.sourceHasNoDataValue(band) and provider.useSourceNoDataValue(band):
        return provider.sourceNoDataValue(band)
    return None


def get_user_nodata_ranges(layer, band):
    """No data ranges set by the user in the layer, as (min, max, bounds), the bounds as in QgsRasterRange:
    0 includes min and max, 1 includes max, 2 includes min, 3 excludes both; a NaN min or max is unbounded"""
    return [
        (
            no_data_range.min(),
            no_data_range.max(),
            int(getattr(no_data_range.bounds(), "value", no_data_range.bounds())),
        )
        for no_data_range in layer.dataProvider().userNoDataValues(band)
    ]


def in_nodata_ranges(value, nodata_ranges):
    """If the value is in any of the no data ranges (min, max, bounds), with the semantics of the provider"""
    return any(
        QgsRasterRange(minimum, maximum, QgsRasterRange.BoundsType(bounds)).contains(value)
        for minimum, maximum, bounds in nodata_ranges
    )


def get_valid_pixel_counts(layer, band, nodata=None):
    """Number of pixels of each class value with pixels in the map, counting all the values in the image
    (not only the ones of the symbology), without the no data of AcATaMa and of the layer, also the no data
    ranges set by the user in the layer (its pixels can't be sampled)"""
    pixel_counts_by_value = get_pixel_count_by_pixel_values(layer, band, None, nodata, complete=True)
    if pixel_counts_by_value is None:
        raise RuntimeError(f'Failed to count the pixels of the map "{layer.name()}"')
    source_nodata = get_source_nodata(layer, band)
    user_nodata_ranges = get_user_nodata_ranges(layer, band)
    return {
        int(value): count
        for value, count in pixel_counts_by_value.items()
        if count > 0
        and not np.isnan(value)
        and value != nodata
        and value != source_nodata
        and not in_nodata_ranges(value, user_nodata_ranges)
    }


class Map:
    def __init__(self, file_selected_combo_box, band=1, nodata=None):
        from AcATaMa.utils.qgis_utils import get_source_from

        self.file_path = get_source_from(file_selected_combo_box)
        self.qgs_layer = file_selected_combo_box.currentLayer()
        self.band = band
        self.nodata = nodata

    def extent(self):
        return self.qgs_layer.extent()

    def get_pixel_value_from_xy(self, x, y):
        return (
            self.qgs_layer.dataProvider()
            .identify(QgsPointXY(x, y), Qgis.RasterIdentifyFormat.Value)
            .results()[self.band]
        )

    def get_pixel_value_from_pnt(self, point):
        return self.qgs_layer.dataProvider().identify(point, Qgis.RasterIdentifyFormat.Value).results()[self.band]

    def get_total_pixels_by_value(self, pixel_value):
        pixel_counts_by_value = get_pixel_count_by_pixel_values(self.qgs_layer, self.band, None, self.nodata)
        if pixel_value in pixel_counts_by_value:
            return pixel_counts_by_value[pixel_value]

    def get_pixel_counts(self):
        """Number of pixels of each class value with pixels in the map, see get_valid_pixel_counts"""
        return get_valid_pixel_counts(self.qgs_layer, self.band, self.nodata)

    def get_pixel_centroid(self, x, y):
        if (
            x < self.extent().xMinimum()
            or x > self.extent().xMaximum()
            or y < self.extent().yMinimum()
            or y > self.extent().yMaximum()
        ):
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
