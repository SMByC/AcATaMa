# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2019 by Xavier Corredor Llano, SMByC
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

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import pyqtSlot

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'generate_sampling_widget.ui'))


class GenerateSamplingWidget(QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        ######
        self.widget_neighbour_aggregation.setHidden(True)
        # fill QCBox_SameClassOfNeighbors
        self.fill_same_class_of_neighbors()
        self.QCBox_NumberOfNeighbors.currentIndexChanged.connect(self.fill_same_class_of_neighbors)

    @pyqtSlot()
    def fill_same_class_of_neighbors(self):
        self.QCBox_SameClassOfNeighbors.clear()
        number_of_neighbor = int(self.QCBox_NumberOfNeighbors.currentText())
        self.QCBox_SameClassOfNeighbors.addItems([str(x) for x in range(1, number_of_neighbor+1)])

