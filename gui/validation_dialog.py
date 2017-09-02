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
from PyQt4 import QtGui, uic

# plugin path
plugin_folder = os.path.dirname(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    plugin_folder, 'ui', 'validation_dialog.ui'))


class ValidationDialog(QtGui.QDialog, FORM_CLASS):
    sampling_layer = None
    view_widgets = []

    def __init__(self, sampling_layer):
        QtGui.QDialog.__init__(self)
        ValidationDialog.sampling_layer = sampling_layer

        self.setupUi(self)

        # save the six view render widgets
        ValidationDialog.view_widgets = \
            [self.render_window_1, self.render_window_2, self.render_window_3,
             self.render_window_4, self.render_window_5, self.render_window_6]

        # set the master view and label names for each view
        for num_view, view_widget in zip(range(1, 7), ValidationDialog.view_widgets):
            view_widget.master_view = ValidationDialog.view_widgets[0]
            view_widget.view_label_name.setText("View {}:".format(num_view))
