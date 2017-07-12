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
from qgis.core import QgsGeometry, QgsPoint, QgsRaster
from processing.tools import vector


class Point():
    def __init__(self, rx, ry):
        self.QgsPnt = QgsPoint(rx, ry)
        self.QgsGeom = QgsGeometry.fromPoint(self.QgsPnt)

    def in_valid_data(self, ThematicR):
        """Check if the point is in valid data in thematic raster
        """
        try:
            point_value_in_thematic = \
                int(ThematicR.qgs_layer.dataProvider().identify(self.QgsPnt, QgsRaster.IdentifyFormatValue).results()[1])
        except:
            return False
        if point_value_in_thematic == ThematicR.nodata:
            return False
        return True

    def in_extent(self, boundaries):
        """Check if the point is inside boundaries
        """
        if self.QgsGeom.within(boundaries):
            return True
        return False

    def in_mim_distance(self, index, min_distance, points):
        """Check if the point have at least the mim distance with respect
        to all points created at the moment
        """
        if min_distance == 0:
            return True
        if vector.checkMinDistance(self.QgsPnt, index, min_distance, points):
            return True
        return False

    def in_categorical_raster(self, pixel_values, CategoricalR):
        """Check if point is at least in one pixel values set of the categorical raster
        """
        if pixel_values is not None:
            point_value_in_categ_raster = \
                int(CategoricalR.qgs_layer.dataProvider().identify(self.QgsPnt, QgsRaster.IdentifyFormatValue).results()[1])
            if point_value_in_categ_raster not in pixel_values:
                return False
        return True

    def in_stratified_raster(self, pixel_values, number_of_samples, CategoricalR, nPointsInCategories):
        """Check if point is at least in one pixel values set of the stratified
        categorical raster
        """
        pixel_value_in_categ_raster = \
            int(CategoricalR.qgs_layer.dataProvider().identify(self.QgsPnt, QgsRaster.IdentifyFormatValue).results()[1])
        self.index_pixel_value = pixel_values.index(pixel_value_in_categ_raster)
        if nPointsInCategories[self.index_pixel_value] >= number_of_samples[self.index_pixel_value]:
            return False
        return True

