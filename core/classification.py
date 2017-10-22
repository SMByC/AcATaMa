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
from random import shuffle

from AcATaMa.core.point import ClassificationPoint


class Classification:
    # save instances for each sampling layer
    instances = {}

    def __init__(self, sampling_layer):
        self.sampling_layer = sampling_layer
        # for store the classification buttons properties
        # {btn_id: {"name", "color", "thematic_class"}}
        self.btns_config = None
        # get all points from the layer
        self.points = self.getPoints()
        # save and init the current sample index
        self.current_sample_idx = 0
        # grid config
        self.grid_columns = 3
        self.grid_rows = 2
        # others config
        self.fit_to_sample = 120
        # when all points are classified
        self.is_completed = False

        # shuffle the list items
        shuffle(self.points)
        # save instance
        Classification.instances[sampling_layer] = self

    def getPoints(self):
        points = []
        for qgs_feature in self.sampling_layer.getFeatures():
            geom = qgs_feature.geometry()
            x, y = geom.asPoint()
            points.append(ClassificationPoint(x, y))
        return points

