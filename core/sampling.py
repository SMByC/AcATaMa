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
import random
from datetime import datetime

from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsGeometry, QgsField, QgsFields, QgsRectangle, QgsSpatialIndex, \
    QgsPoint, QgsFeature, QGis, QgsDistanceArea, QgsRaster
from processing.tools import vector

from AcATaMa.core.raster import get_extent
from AcATaMa.core.dockwidget import error_handler, wait_process, load_layer_in_qgis, get_current_file_path_in, \
    get_current_layer_in


@error_handler()
@wait_process()
def do_random_sampling(dockwidget):
    number_of_samples = int(dockwidget.numberOfSamples_RS.value())
    min_distance = int(dockwidget.minDistance_RS.value())
    thematic_raster = get_current_file_path_in(dockwidget.selectThematicRaster)
    extent = get_extent(thematic_raster)
    thematic_layer = get_current_layer_in(dockwidget.selectThematicRaster)
    nodata_thematic = int(dockwidget.nodata_ThematicRaster.value())

    # random sampling in categorical raster
    if dockwidget.groupBox_RSwithCR.isChecked():
        categorical_layer = get_current_layer_in(dockwidget.selectCategRaster_RS)
        try:
            pixel_values = [int(p) for p in dockwidget.pixelsValuesCategRaster.text().split(",")]
        except:
            iface.messageBar().pushMessage("AcATaMa", "Error, wrong pixel values, set only integers and separated by commas",
                                           level=QgsMessageBar.WARNING, duration=20)
            return
    else:
        categorical_layer = get_current_layer_in(dockwidget.selectThematicRaster)
        pixel_values = None

    output_file = os.path.join(dockwidget.tmp_dir, "random_sampling_t{}".format(datetime.now().strftime('%H%M%S')))
    # process
    nPoints = random_points_in_thematic(number_of_samples, min_distance, extent, output_file, thematic_layer,
                                        nodata_thematic, categorical_layer, pixel_values)

    # success
    if nPoints == number_of_samples:
        load_layer_in_qgis(output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generate the random sampling, completed",
                                       level=QgsMessageBar.SUCCESS)
    # success but not completed
    if nPoints < number_of_samples and nPoints > 0:
        load_layer_in_qgis(output_file + ".shp", "vector")
        iface.messageBar().pushMessage("AcATaMa", "Generated the random sampling, but can not generate requested number of "
                                                  "random points {}/{}, attempts exceeded".format(nPoints, number_of_samples),
                                       level=QgsMessageBar.INFO, duration=20)
    # zero points
    if nPoints < number_of_samples and nPoints == 0:
        iface.messageBar().pushMessage("AcATaMa", "Error, could not generate any random points with this settings, "
                                                  "attempts exceeded", level=QgsMessageBar.WARNING, duration=20)


@error_handler()
@wait_process()
def do_stratified_random_sampling(dockwidget):
    pass


def random_points_in_thematic(point_number, min_distance, extent, output_file, thematic_layer, nodata_thematic,
                              categorical_layer=None, pixel_values=None):
    """Code base from (by Alexander Bruy):
    https://github.com/qgis/QGIS/blob/release-2_18/python/plugins/processing/algs/qgis/RandomPointsExtent.py
    """

    xMin = float(extent[0])
    xMax = float(extent[2])
    yMin = float(extent[3])
    yMax = float(extent[1])
    extent = QgsGeometry().fromRect(QgsRectangle(xMin, yMin, xMax, yMax))

    fields = QgsFields()
    fields.append(QgsField('id', QVariant.Int, '', 10, 0))
    mapCRS = iface.mapCanvas().mapSettings().destinationCrs()
    writer = vector.VectorWriter(output_file, None, fields, QGis.WKBPoint, mapCRS)

    nPoints = 0
    nIterations = 0
    maxIterations = point_number * 200
    total = 100.0 / point_number

    index = QgsSpatialIndex()
    points = dict()

    random.seed()

    while nIterations < maxIterations and nPoints < point_number:
        rx = xMin + (xMax - xMin) * random.random()
        ry = yMin + (yMax - yMin) * random.random()

        pnt = QgsPoint(rx, ry)
        geom = QgsGeometry.fromPoint(pnt)

        # check if point is not a nodata value in thematic raster
        point_value_in_thematic = \
            int(thematic_layer.dataProvider().identify(pnt, QgsRaster.IdentifyFormatValue).results()[1])
        if point_value_in_thematic == nodata_thematic:
            nIterations += 1
            continue
        # check if point in categ raster is in pixel values
        if pixel_values is not None:
            point_value_in_categ_raster = \
                int(categorical_layer.dataProvider().identify(pnt, QgsRaster.IdentifyFormatValue).results()[1])
            if point_value_in_categ_raster not in pixel_values:
                nIterations += 1
                continue

        if geom.within(extent) and \
                vector.checkMinDistance(pnt, index, min_distance, points):
            f = QgsFeature(nPoints)
            f.initAttributes(1)
            f.setFields(fields)
            f.setAttribute('id', nPoints)
            f.setGeometry(geom)
            writer.addFeature(f)
            index.insertFeature(f)
            points[nPoints] = pnt
            nPoints += 1
            # feedback.setProgress(int(nPoints * total))
        nIterations += 1

    del writer

    return nPoints

