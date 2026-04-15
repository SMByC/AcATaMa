# -*- coding: utf-8 -*-
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
import os

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsRendererPropertiesDialog, QgsRendererRasterPropertiesWidget, QgsMapLayerComboBox
from qgis.core import QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsVectorLayer, Qgis, QgsStyle, QgsMapLayer
from qgis.utils import iface


def is_integer_data_type(layer, band=1):
    """Check if the raster layer data type for the given band is integer or byte.
    Uses the Qgis.DataType enum name to detect integer types generically,
    compatible across different QGIS/GDAL versions (including Int8, etc.).
    """
    data_type = layer.dataProvider().dataType(band)
    try:
        type_name = Qgis.DataType(data_type).name
    except ValueError:
        return False
    return "Int" in type_name or "Byte" in type_name


def get_source_from(item):
    """Get the source/path of a QgsMapLayer or the current layer in a QgsMapLayerComboBox."""
    layer = item.currentLayer() if isinstance(item, QgsMapLayerComboBox) else item
    if layer and layer.isValid():
        source = layer.source().split("|layername")[0]
        if os.path.isfile(source):
            return source
        # for remote/non-filesystem layers return the full source as identifier
        return layer.source()
    return ""


def valid_file_selected_in(combo_box, combobox_name=False):
    if combo_box.currentLayer() is None:
        return False
    if combo_box.currentLayer().isValid():
        return True
    else:
        if combobox_name:
            iface.messageBar().pushMessage("AcATaMa", "Error, please browse/select a valid file in "
                                           + combobox_name, level=Qgis.MessageLevel.Warning, duration=10)
        combo_box.setCurrentIndex(-1)
        return False


def get_loaded_layer(layer_path):
    # return the loaded layer in Qgis that matches the file path
    # whatever the name of the layer
    for layer in QgsProject.instance().mapLayers().values():
        if layer.source() == layer_path:
            return layer


def select_item_in(combo_box, item):
    selected_index = combo_box.findText(item, Qt.MatchFlag.MatchFixedString)
    combo_box.setCurrentIndex(selected_index)


def load_and_select_layer_in(source, combo_box, layer_name=None):
    if not source:
        combo_box.setCurrentIndex(-1)
        return True
    qgslayer = get_loaded_layer(source)
    # try to load the layer if not already in QGIS
    if qgslayer is None:
        qgslayer = load_layer(source, name=layer_name)
        if qgslayer is None or not qgslayer.isValid():
            return False
    # select the exact layer in combobox
    combo_box.setLayer(qgslayer)

    return qgslayer


RASTER_EXTENSIONS = (".tif", ".tiff", ".vrt", ".img", ".jp2", ".asc", ".nc", ".hdf", ".ecw", ".dt2")
VECTOR_EXTENSIONS = (".shp", ".gpkg", ".geojson", ".json", ".kml", ".gml", ".csv", ".xlsx", ".ods", ".dxf", ".tab")


def detect_provider(source):
    """Detect the provider key and layer class from a file path or datasource URI."""
    s = source.lower().strip()

    # Local filesystem files (let QGIS auto-detect the best provider)
    ext = os.path.splitext(s)[1]
    if ext:
        if ext in RASTER_EXTENSIONS:
            return None, QgsRasterLayer
        if ext in VECTOR_EXTENSIONS:
            return None, QgsVectorLayer

    # Google Earth Engine
    if "type=xyz" in s and "url=https://earthengine.googleapis.com" in s:
        if "EE" in QgsProviderRegistry.instance().providerList():
            return "EE", QgsRasterLayer
        else:
            iface.messageBar().pushMessage("AcATaMa",
                "Google Earth Engine plugin is required to load this layer, install and configure it.",
                level=Qgis.MessageLevel.Warning, duration=20)
            return None, None

    # OGC services
    if "type=xyz" in s or "provider=xyz" in s:
        return "wms", QgsRasterLayer
    if "service=wms" in s or "request=getmap" in s or "contextualwmslegend" in s or "contextualwmslegen" in s:
        return "wms", QgsRasterLayer
    if "service=wmts" in s or "tilematrixset" in s:
        return "wms", QgsRasterLayer
    if "service=wfs" in s or "typename=" in s or "provider=wfs" in s:
        return "wfs", QgsVectorLayer
    if "service=wcs" in s or "coverage=" in s or "coverageid=" in s:
        return "wcs", QgsRasterLayer

    # Databases
    if s.startswith("postgresql://") or "provider=postgres" in s or (
            "dbname=" in s and ("table=" in s or "schema=" in s)):
        return "postgres", QgsVectorLayer
    if "spatialite" in s or "provider=spatialite" in s or (
            ".sqlite" in s and "table=" in s):
        return "spatialite", QgsVectorLayer

    # ArcGIS REST services
    if "mapserver" in s or "arcgismapserver" in s:
        return "arcgismapserver", QgsRasterLayer
    if "featureserver" in s or "arcgisfeatureserver" in s:
        return "arcgisfeatureserver", QgsVectorLayer

    # Vector tile datasource URIs
    if "provider=vectortile" in s or "type=vtpk" in s or "type=mbtiles" in s or "vectortile" in s:
        return "vectortile", QgsVectorLayer

    # Remote direct file URLs
    if s.startswith("http://") or s.startswith("https://") or "url=http" in s:
        if any(ext in s for ext in RASTER_EXTENSIONS):
            return "gdal", QgsRasterLayer
        if any(ext in s for ext in VECTOR_EXTENSIONS):
            return "ogr", QgsVectorLayer
        return "wms", QgsRasterLayer

    return None, None


def load_layer(source, name=None, add_to_legend=True):
    """Load a layer from a file path or remote datasource URI and add it to the project."""
    name = name or (os.path.splitext(os.path.basename(source))[0] if os.path.isfile(source) else "Remote Layer")

    provider_key, layer_class = detect_provider(source)
    layer = (layer_class(source, name, provider_key) if provider_key else layer_class(source, name)) if layer_class else None

    if layer and layer.isValid():
        QgsProject.instance().addMapLayer(layer, add_to_legend)
        return layer

    return None


def unload_layer(source):
    layers_loaded = QgsProject.instance().mapLayers().values()
    for layer_loaded in layers_loaded:
        if source == get_source_from(layer_loaded):
            QgsProject.instance().removeMapLayer(layer_loaded.id())


def get_symbology_table(raster_layer, band):
    """Get the symbology table with pixel value, label and Qcolor of raster layer
    """
    from AcATaMa.core.map import get_xml_style

    # check if the thematic map has a valid symbology else ask to apply an automatic classification
    get_xml_style(raster_layer, band)

    renderer = raster_layer.renderer()

    if renderer.type() == 'singlebandpseudocolor':
        color_ramp = renderer.shader().rasterShaderFunction()
        color_ramp_list = color_ramp.colorRampItemList()
        symbology_table = []
        for color_ramp_item in color_ramp_list:
            symbology_table.append([int(color_ramp_item.value), color_ramp_item.label, color_ramp_item.color])
        return symbology_table

    if renderer.type() == 'paletted':
        symbology_table = []
        for raster_class in renderer.classes():
            symbology_table.append([int(raster_class.value), raster_class.label, raster_class.color])
        return symbology_table


# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'response_design_style_editor.ui'))


class StyleEditorDialog(QDialog, FORM_CLASS):
    def __init__(self, layer, canvas, parent=None):
        QDialog.__init__(self)
        self.setupUi(self)
        self.layer = layer

        self.setWindowTitle("{} - style editor".format(self.layer.name()))

        if self.layer.type() == QgsMapLayer.LayerType.VectorLayer:
            self.StyleEditorWidget = QgsRendererPropertiesDialog(self.layer, QgsStyle(), True, parent)

        if self.layer.type() == QgsMapLayer.LayerType.RasterLayer:
            self.StyleEditorWidget = QgsRendererRasterPropertiesWidget(self.layer, canvas, parent)

        self.scrollArea.setWidget(self.StyleEditorWidget)

        self.DialogButtons.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        self.DialogButtons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)

    def apply(self):
        self.StyleEditorWidget.apply()
        self.layer.triggerRepaint()
