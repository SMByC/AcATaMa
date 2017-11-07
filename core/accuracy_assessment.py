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
from AcATaMa.core.raster import Raster
from AcATaMa.core.utils import wait_process


class AccuracyAssessment:

    def __init__(self, classification):
        from AcATaMa.gui.acatama_dockwidget import AcATaMaDockWidget as AcATaMa

        self.classification = classification
        self.ThematicR = Raster(file_selected_combo_box=AcATaMa.dockwidget.QCBox_ThematicRaster,
                                nodata=int(AcATaMa.dockwidget.nodata_ThematicRaster.value()))

    @wait_process
    def compute(self):

        # get labels from classification buttons
        labels = {}
        for button_config in self.classification.buttons_config.values():
            labels[button_config["thematic_class"]] = button_config["name"]

        # get the classified and thematic map values
        thematic_map_values = []
        classified_values = []
        points_ordered = sorted(self.classification.points, key=lambda p: p.shape_id)
        for point in points_ordered:
            # classification from the pixel values in the thematic map
            thematic_map_value = self.ThematicR.get_pixel_value_from_pnt(point.QgsPnt)
            thematic_map_values.append(int(thematic_map_value))
            # classified value made/checked by user with classification buttons
            classified_value = self.classification.buttons_config[point.classif_id]["thematic_class"]
            classified_values.append(int(classified_value))

        # all unique and sorted values
        values = sorted(set(thematic_map_values + classified_values))
        # Construct a value->index dictionary
        indices = dict((val, i) for (i, val) in enumerate(values))

        # calculate the error/confusion matrix
        # https://github.com/nltk/nltk/blob/develop/nltk/metrics/confusionmatrix.py
        #
        #             classified
        #   t |    | L1 | L2 | L3 | L4 |
        #   h | L1 |    |    |    |    |
        #   e | L2 |    |    |    |    |
        #   m | L3 |    |    |    |    |
        #   a | L4 |    |    |    |    |
        #
        error_matrix = [[0 for column in values] for row in values]
        for thematic, classified in zip(thematic_map_values, classified_values):
            error_matrix[indices[thematic]][indices[classified]] += 1
