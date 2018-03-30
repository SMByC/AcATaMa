# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2018 by Xavier Corredor Llano, SMBYC
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
import random
from qgis.core import QgsGeometry, QgsPoint, QgsRectangle
from processing.tools import vector

from AcATaMa.utils.system_utils import block_signals_to


class Point(object):

    def __init__(self, x, y):
        self.set_qgis_pnt(x, y)

    def set_qgis_pnt(self, x, y):
        self.QgsPnt = QgsPoint(x, y)
        self.QgsGeom = QgsGeometry.fromPoint(self.QgsPnt)


class RandomPoint(Point):
    # init random
    random.seed()

    def __init__(self, xMin, yMax, xMax, yMin):
        # generate the random x and y between boundaries
        rx = xMin + (xMax - xMin) * random.random()
        ry = yMin + (yMax - yMin) * random.random()
        self.set_qgis_pnt(rx, ry)

    def in_valid_data(self, ThematicR):
        """Check if the point is in valid data in thematic raster
        """
        try:
            point_value_in_thematic = int(ThematicR.get_pixel_value_from_pnt(self.QgsPnt))
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

    def in_categorical_raster_SimpRS(self, pixel_values, CategoricalR):
        """Check if point is at least in one pixel values set in the categorical raster
        """
        if pixel_values is not None:
            point_value_in_categ_raster = int(CategoricalR.get_pixel_value_from_pnt(self.QgsPnt))
            if point_value_in_categ_raster not in pixel_values:
                return False
        return True

    def in_categorical_raster_StraRS(self, pixel_values, number_of_samples, CategoricalR, nPointsInCategories):
        """Check if point pass the number of samples in the category or is nodata
        """
        pixel_value_in_categ_raster = int(CategoricalR.get_pixel_value_from_pnt(self.QgsPnt))
        if pixel_value_in_categ_raster == CategoricalR.nodata or pixel_value_in_categ_raster not in pixel_values:
            return False
        self.index_pixel_value = pixel_values.index(pixel_value_in_categ_raster)
        if nPointsInCategories[self.index_pixel_value] >= number_of_samples[self.index_pixel_value]:
            return False
        return True

    def check_neighbors_aggregation(self, ThematicR, num_neighbors, min_with_same_class):
        """Check if the pixel have at least the minimum the neighbors with the
        same class of the pixel
        """
        pixel_class_value = int(ThematicR.get_pixel_value_from_pnt(self.QgsPnt))

        pixel_size_x = ThematicR.qgs_layer.rasterUnitsPerPixelX()
        pixel_size_y = ThematicR.qgs_layer.rasterUnitsPerPixelY()

        if num_neighbors == 8:
            x_list = [pixel_size_x*mul+self.QgsPnt.x() for mul in range(-1, 2)]
            y_list = [pixel_size_y*mul+self.QgsPnt.y() for mul in range(-1, 2)]
        if num_neighbors == 24:
            x_list = [pixel_size_x*mul+self.QgsPnt.x() for mul in range(-2, 3)]
            y_list = [pixel_size_y*mul+self.QgsPnt.y() for mul in range(-2, 3)]
        if num_neighbors == 48:
            x_list = [pixel_size_x*mul+self.QgsPnt.x() for mul in range(-3, 4)]
            y_list = [pixel_size_y*mul+self.QgsPnt.y() for mul in range(-3, 4)]

        neighbors = []
        for x, y in ((_x, _y) for _x in x_list for _y in y_list):
            try:
                neighbors.append(int(ThematicR.get_pixel_value_from_xy(x, y)))
            except:
                continue

        if neighbors.count(pixel_class_value) > min_with_same_class:
            return True

        return False


class ClassificationPoint(Point):

    def __init__(self, x, y, shape_id=None):
        super(ClassificationPoint, self).__init__(x, y)
        # shape id is the order of the points inside the shapefile
        self.shape_id = shape_id
        # classification button id
        self.classif_id = None
        # status for this point
        self.is_classified = False

    def fit_to(self, view_widget, radius):
        # fit to current sample with min radius of extent
        fit_extent = QgsRectangle(self.QgsPnt.x()-radius, self.QgsPnt.y()-radius,
                                  self.QgsPnt.x()+radius, self.QgsPnt.y()+radius)
        with block_signals_to(view_widget.render_widget.canvas):
            view_widget.render_widget.set_extents_and_scalefactor(fit_extent)
