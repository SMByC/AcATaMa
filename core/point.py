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
import random
from PyQt4.QtCore import QTimer
from qgis.PyQt import QtGui
from qgis.core import QgsGeometry, QgsPoint, QgsRectangle, QGis
from qgis.gui import QgsVertexMarker, QgsRubberBand
from processing.tools import vector

from AcATaMa.core.utils import block_signals_to


class Point(object):

    def __init__(self, x, y):
        self.setQgsPnt(x, y)

    def setQgsPnt(self, x, y):
        self.QgsPnt = QgsPoint(x, y)
        self.QgsGeom = QgsGeometry.fromPoint(self.QgsPnt)


class RandomPoint(Point):
    # init random
    random.seed()

    def __init__(self, xMin, yMax, xMax, yMin):
        # generate the random x and y between boundaries
        rx = xMin + (xMax - xMin) * random.random()
        ry = yMin + (yMax - yMin) * random.random()
        self.setQgsPnt(rx, ry)

    def in_valid_data(self, ThematicR):
        """Check if the point is in valid data in thematic raster
        """
        try:
            point_value_in_thematic = int(ThematicR.get_pixel_value_from_pnt(self.QgsPnt, band=1))
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
            point_value_in_categ_raster = int(CategoricalR.get_pixel_value_from_pnt(self.QgsPnt, band=1))
            if point_value_in_categ_raster not in pixel_values:
                return False
        return True

    def in_stratified_raster(self, pixel_values, number_of_samples, CategoricalR, nPointsInCategories):
        """Check if point is at least in one pixel values set of the stratified
        categorical raster
        """
        pixel_value_in_categ_raster = int(CategoricalR.get_pixel_value_from_pnt(self.QgsPnt, band=1))
        self.index_pixel_value = pixel_values.index(pixel_value_in_categ_raster)
        if nPointsInCategories[self.index_pixel_value] >= number_of_samples[self.index_pixel_value]:
            return False
        return True

    def check_neighbors_aggregation(self, ThematicR, num_neighbors, min_with_same_class):
        """Check if the pixel have at least the minimum the neighbors with the
        same class of the pixel
        """
        pixel_class_value = int(ThematicR.get_pixel_value_from_pnt(self.QgsPnt, band=1))

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
                neighbors.append(int(ThematicR.get_pixel_value_from_xy(x, y, band=1)))
            except:
                continue

        if neighbors.count(pixel_class_value) > min_with_same_class:
            return True

        return False


class ClassificationPoint(Point):

    def __init__(self, x, y):
        super(ClassificationPoint, self).__init__(x, y)
        # init param
        self.is_classified = False
        self.class_id = None
        self.markers = [None]*6

    def show_marker(self, view_widget):
        """Show marker for the respective view widget"""
        if self.markers[view_widget.id] is None:
            self.markers[view_widget.id] = QgsVertexMarker(view_widget.render_widget.canvas)
        self.markers[view_widget.id].setCenter(self.QgsPnt)
        self.markers[view_widget.id].setIconSize(18)
        self.markers[view_widget.id].setPenWidth(2)
        self.markers[view_widget.id].setIconType(QgsVertexMarker.ICON_CROSS)

    def remove_marker(self, view_widget):
        """Remove marker for the respective view widget"""
        view_widget.render_widget.canvas.scene().removeItem(self.markers[view_widget.id])
        self.markers[view_widget.id] = None

    def highlight(self, view_widget):
        curr_ext = view_widget.render_widget.canvas.extent()

        left_point = QgsPoint(curr_ext.xMinimum(), self.QgsPnt.y())
        right_point = QgsPoint(curr_ext.xMaximum(), self.QgsPnt.y())

        top_point = QgsPoint(self.QgsPnt.x(), curr_ext.yMaximum())
        bottom_point = QgsPoint(self.QgsPnt.x(), curr_ext.yMinimum())

        horiz_line = QgsGeometry.fromPolyline([left_point, right_point])
        vert_line = QgsGeometry.fromPolyline([top_point, bottom_point])

        cross_rb = QgsRubberBand(view_widget.render_widget.canvas, QGis.Line)
        cross_rb.setColor(QtGui.QColor(255, 0, 0))
        cross_rb.reset(QGis.Line)
        cross_rb.addGeometry(horiz_line, None)
        cross_rb.addGeometry(vert_line, None)

        QTimer.singleShot(600, cross_rb.reset)
        view_widget.render_widget.canvas.refresh()

    def fit_to(self, view_widget, radius):
        # fit to current sample with min radius of extent
        fit_extent = QgsRectangle(self.QgsPnt.x()-radius, self.QgsPnt.y()-radius,
                                  self.QgsPnt.x()+radius, self.QgsPnt.y()+radius)
        with block_signals_to(view_widget.render_widget.canvas):
            view_widget.render_widget.set_extents_and_scalefactor(fit_extent)
