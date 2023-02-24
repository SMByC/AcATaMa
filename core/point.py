# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2023 by Xavier C. Llano, SMByC
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
import random
from math import floor

from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle

from AcATaMa.utils.qgis_utils import valid_file_selected_in
from AcATaMa.utils.sampling_utils import check_min_distance
from AcATaMa.utils.system_utils import block_signals_to


class Point(object):
    def __init__(self, x, y):
        self.QgsPnt = QgsPointXY(x, y)
        self.QgsGeom = QgsGeometry.fromPointXY(self.QgsPnt)


class RandomPoint(Point):
    """Class for generate, check and validate the random points
    """

    def __init__(self, x, y):
        """Init Qgis point
        """
        super().__init__(x, y)

    @classmethod
    def fromExtent(cls, extent):
        """Generate the random x and y between boundaries

        Args:
            extent (QgsRectangle): extent boundaries for generate random points inside it
        """
        rx = extent.xMinimum() + (extent.xMaximum() - extent.xMinimum()) * random.random()
        ry = extent.yMinimum() + (extent.yMaximum() - extent.yMinimum()) * random.random()
        return cls(rx, ry)

    def in_valid_data(self, thematic_map):
        """Check if the point is in valid data in thematic map
        """
        try:
            point_value_in_thematic = int(thematic_map.get_pixel_value_from_pnt(self.QgsPnt))
        except:
            return False
        if point_value_in_thematic == thematic_map.nodata:
            return False
        return True

    def in_extent(self, boundaries):
        """Check if the point is inside boundaries

        Args:
            boundaries (QgsGeometry)
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
        if check_min_distance(self.QgsPnt, index, min_distance, points):
            return True
        return False

    def in_categorical_map_post_stratify(self, classes_for_sampling, categorical_map):
        """Check if point is at least in one pixel values set in the categorical map
        """
        if classes_for_sampling is not None:
            point_value_in_categ_map = int(categorical_map.get_pixel_value_from_pnt(self.QgsPnt))
            if point_value_in_categ_map not in classes_for_sampling:
                return False
        return True

    def in_categorical_map_StraRS(self, classes_for_sampling, total_of_samples, categorical_map, nPointsInCategories):
        """Check if point pass the number of samples in the category or is nodata
        """
        pixel_value_in_categ_map = int(categorical_map.get_pixel_value_from_pnt(self.QgsPnt))
        if pixel_value_in_categ_map == categorical_map.nodata or pixel_value_in_categ_map not in classes_for_sampling:
            return False
        self.index_pixel_value = classes_for_sampling.index(pixel_value_in_categ_map)
        if nPointsInCategories[self.index_pixel_value] >= total_of_samples[self.index_pixel_value]:
            return False
        return True

    def check_neighbors_aggregation(self, thematic_map, num_neighbors, min_with_same_class):
        """Check if the pixel have at least the minimum the neighbors with the
        same class of the pixel
        """
        pixel_class_value = int(thematic_map.get_pixel_value_from_pnt(self.QgsPnt))

        pixel_size_x = thematic_map.qgs_layer.rasterUnitsPerPixelX()
        pixel_size_y = thematic_map.qgs_layer.rasterUnitsPerPixelY()

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
                neighbors.append(int(thematic_map.get_pixel_value_from_xy(x, y)))
            except:
                continue

        if neighbors.count(pixel_class_value) > min_with_same_class:
            return True

        return False


class LabelingPoint(Point):

    def __init__(self, x, y, sample_id=None):
        super().__init__(x, y)
        # shape id is the order of the points inside the shapefile
        self.sample_id = sample_id
        # label button id
        self.label_id = None
        # status for this point
        self.is_labeled = False

    def fit_to(self, view_widget, radius):
        # fit to current sample with min radius of extent
        fit_extent = QgsRectangle(self.QgsPnt.x()-radius, self.QgsPnt.y()-radius,
                                  self.QgsPnt.x()+radius, self.QgsPnt.y()+radius)
        with block_signals_to(view_widget.render_widget.canvas):
            view_widget.render_widget.set_extents_and_scalefactor(fit_extent)

    def get_thematic_pixel(self, with_buffer=0):
        """Get the edges of the thematic pixel respectively of the current labeling point"""
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa
        if not valid_file_selected_in(AcATaMa.dockwidget.QCBox_ThematicMap):
            return
        thematic_layer = AcATaMa.dockwidget.QCBox_ThematicMap.currentLayer()
        data_provider = thematic_layer.dataProvider()
        if not data_provider.capabilities() or not data_provider.Size:
            return
        extent = data_provider.extent()
        width = data_provider.xSize()
        height = data_provider.ySize()
        xres = extent.width() / width
        yres = extent.height() / height

        if extent.xMinimum() <= self.QgsPnt.x() <= extent.xMaximum() and \
                extent.yMinimum() <= self.QgsPnt.y() <= extent.yMaximum():
            col = int(floor((self.QgsPnt.x() - extent.xMinimum()) / xres))
            row = int(floor((extent.yMaximum() - self.QgsPnt.y()) / yres))
            xmin = extent.xMinimum() + col * xres - with_buffer * xres
            xmax = xmin + xres + 2*(with_buffer * xres)
            ymax = extent.yMaximum() - row * yres + with_buffer * yres
            ymin = ymax - yres - 2*(with_buffer * yres)

            return xmin, xmax, ymin, ymax
